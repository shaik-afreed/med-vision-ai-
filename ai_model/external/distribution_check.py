"""Can the app tell that an X-ray does not look like the model's training data?

Problem: the deployed model (V1) learned from children's chest X-rays only and
gives confident wrong answers on other images (adult normals scored "pneumonia
99%"; the age typed by the user is not always right, and a non-X-ray photo gets
a score too). This builds an image-based "does this look like the training
data" check and measures whether it works.

Method: take the model's own 1280-number image summary (the global-average-
pool layer before its final decision), fit PCA (N_COMPONENTS) and a Gaussian
on the TRAINING images only, and score any image by its Mahalanobis distance
in that space. The flag threshold is the 99th percentile of the distances of
held-out children's images (validation + calibration split, never used for
fitting). No adult image is used to fit or to choose the threshold.

PRE-REGISTERED SUCCESS CRITERIA (written before the first run):
  1. The check flags at least 90% of the 1,145 NIH adult X-rays
     (ai_model/external/cache/nih_x.npy), AND
  2. flags at most 3% of the 624 children's TEST images, AND
  3. N_COMPONENTS and the 99th-percentile rule are fixed here and not changed
     after seeing results. If any criterion fails, the check is not shipped.

Also reported (descriptive): flag rates on solid-color and random-noise images
as stand-ins for "not an X-ray at all".

Usage (from ai_model/):  python external/distribution_check.py
Writes external/distribution_check.json (the fitted check + the measurements).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AI_MODEL = os.path.dirname(HERE)
CACHE_CHILD = os.path.join(AI_MODEL, "improve", "cache")
CACHE_NIH = os.path.join(HERE, "cache")
V1_PATH = os.path.join(AI_MODEL, "saved_models", "fine_tuned_model.h5")

N_COMPONENTS = 64
PERCENTILE = 99.0
OUT_JSON = os.path.join(HERE, "distribution_check.json")


def features(model_path, x):
    import tensorflow as tf

    model = tf.keras.models.load_model(model_path)
    extractor = tf.keras.Model(model.input, model.get_layer("global_average_pooling2d").output)
    out = []
    for start in range(0, len(x), 64):
        out.append(extractor.predict(x[start:start + 64].astype(np.float32), verbose=0))
    return np.concatenate(out)


def fit(train_features):
    mean = train_features.mean(axis=0)
    centered = train_features - mean
    # PCA by SVD; keep the top components.
    _, singular, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:N_COMPONENTS]
    variances = (singular[:N_COMPONENTS] ** 2) / (len(train_features) - 1)
    return mean, components, variances


def distance(feats, mean, components, variances):
    projected = (feats - mean) @ components.T
    return np.sqrt(((projected ** 2) / variances).sum(axis=1))


def main():
    child = {s: np.load(f"{CACHE_CHILD}/{s}_x.npy") for s in ("train", "validation", "calibration", "test")}
    adults = np.load(f"{CACHE_NIH}/nih_x.npy")
    meta = json.load(open(f"{CACHE_NIH}/nih_meta.json", encoding="utf-8"))

    rng = np.random.default_rng(0)
    synthetic = np.concatenate([
        np.stack([np.full((224, 224, 3), v, dtype=np.uint8) for v in (0, 64, 128, 192, 255)]),
        rng.integers(0, 256, size=(20, 224, 224, 3), dtype=np.uint8),
    ])

    feats = {name: features(V1_PATH, x) for name, x in {**child, "adults": adults, "synthetic": synthetic}.items()}
    mean, components, variances = fit(feats["train"])
    dist = {name: distance(f, mean, components, variances) for name, f in feats.items()}

    held_out = np.concatenate([dist["validation"], dist["calibration"]])
    threshold = float(np.percentile(held_out, PERCENTILE))

    flagged = {name: float((d > threshold).mean()) for name, d in dist.items()}
    adult_ages = np.array([m["age"] for m in meta])
    adult_pneu = np.array([m["label"] for m in meta]).astype(bool)

    report = {
        "n_components": N_COMPONENTS,
        "percentile": PERCENTILE,
        "threshold": round(threshold, 4),
        "images": {name: int(len(d)) for name, d in dist.items()},
        "median_distance": {name: round(float(np.median(d)), 2) for name, d in dist.items()},
        "flagged_fraction": {name: round(v, 4) for name, v in flagged.items()},
        "adults_flagged_by_group": {
            "pneumonia": round(float((dist["adults"][adult_pneu] > threshold).mean()), 4),
            "no_finding": round(float((dist["adults"][~adult_pneu] > threshold).mean()), 4),
            "age_under_30": round(float((dist["adults"][adult_ages < 30] > threshold).mean()), 4),
            "age_30_plus": round(float((dist["adults"][adult_ages >= 30] > threshold).mean()), 4),
        },
        "criteria": {
            "adults_flagged_at_least_90pct": bool(flagged["adults"] >= 0.90),
            "children_test_flagged_at_most_3pct": bool(flagged["test"] <= 0.03),
        },
    }
    report["passes"] = all(report["criteria"].values())

    print(json.dumps(report, indent=1))

    if report["passes"]:
        # The fitted check, small enough to ship with the backend.
        report["fit"] = {
            "mean": mean.round(6).tolist(),
            "components": components.round(6).tolist(),
            "variances": variances.round(6).tolist(),
        }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f)


if __name__ == "__main__":
    main()
