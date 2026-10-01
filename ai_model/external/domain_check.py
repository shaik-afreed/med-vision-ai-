"""Second attempt at "does this X-ray look like the model's training data?"

distribution_check.py (unsupervised distance, pre-registered) FAILED: it flagged
only 38.5% of adult X-rays (needed 90%), so it is not used.

This version is supervised: a logistic regression on V1's own 1280-number
image summary that learns "children's training-set X-ray" vs "adult NIH
X-ray". Data and split (fixed here, before the first run):
  - children  : the 4,123 training images (ai_model/improve/cache/train_x.npy)
  - adults    : the NIH images in ai_model/external/cache, split BY PATIENT 50/50
                with the same GroupShuffleSplit(seed 42) used in nih_eval.py.
                Only the CALIBRATION half is used to fit; the TEST half
                (569 images, different patients) is never seen in fitting.
  - model     : StandardScaler + LogisticRegression(C=1.0, class_weight=
                "balanced"); an image is flagged when P(adult-like) >= 0.5.
                No hyperparameter is tuned.

PRE-REGISTERED SUCCESS CRITERIA:
  1. flags >= 95% of the held-out NIH adult TEST-half images, AND
  2. flags <= 3% of the children's TEST images (624) and of the children's
     VALIDATION images (555).
If either fails, the check is not shipped.

Limits, stated in advance: adults come from ONE source (NIH), so the classifier
may partly learn NIH-specific image traits rather than "adult"; flagging images
from other sources is acceptable here (the model does not generalize to them
either), but a different adult dataset would be needed to measure it.
Descriptive extras: solid-color / random-noise images, and how many of V1's
adult false alarms the check catches.

Usage (from ai_model/): python external/domain_check.py
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AI_MODEL = os.path.dirname(HERE)
CACHE_CHILD = os.path.join(AI_MODEL, "improve", "cache")
CACHE_NIH = os.path.join(HERE, "cache")
V1_PATH = os.path.join(AI_MODEL, "saved_models", "fine_tuned_model.h5")
OUT_JSON = os.path.join(HERE, "domain_check.json")
SEED = 42


def extract(x):
    import tensorflow as tf

    model = tf.keras.models.load_model(V1_PATH)
    extractor = tf.keras.Model(model.input, [model.output, model.get_layer("global_average_pooling2d").output])
    probs, feats = [], []
    for start in range(0, len(x), 64):
        p, f = extractor.predict(x[start:start + 64].astype(np.float32), verbose=0)
        probs.append(p.ravel()); feats.append(f)
    return np.concatenate(probs), np.concatenate(feats)


def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.preprocessing import StandardScaler

    child = {s: np.load(f"{CACHE_CHILD}/{s}_x.npy") for s in ("train", "validation", "test")}
    adults = np.load(f"{CACHE_NIH}/nih_x.npy")
    meta = json.load(open(f"{CACHE_NIH}/nih_meta.json", encoding="utf-8"))
    y_adult = np.array([m["label"] for m in meta])
    groups = np.array([m["patient_id"] for m in meta])

    # Same patient-grouped split as nih_eval.py.
    cal_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=SEED).split(adults, y_adult, groups))
    assert not set(groups[cal_idx]) & set(groups[test_idx])

    rng = np.random.default_rng(0)
    synthetic = np.concatenate([
        np.stack([np.full((224, 224, 3), v, dtype=np.uint8) for v in (0, 64, 128, 192, 255)]),
        rng.integers(0, 256, size=(20, 224, 224, 3), dtype=np.uint8),
    ])

    data = {**child, "adults": adults, "synthetic": synthetic}
    probs, feats = {}, {}
    for name, x in data.items():
        probs[name], feats[name] = extract(x)

    x_fit = np.concatenate([feats["train"], feats["adults"][cal_idx]])
    y_fit = np.concatenate([np.zeros(len(feats["train"])), np.ones(len(cal_idx))])
    scaler = StandardScaler().fit(x_fit)
    clf = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000).fit(scaler.transform(x_fit), y_fit)

    def p_adult(f):
        return clf.predict_proba(scaler.transform(f))[:, 1]

    flagged = {
        "children_test": float((p_adult(feats["test"]) >= 0.5).mean()),
        "children_validation": float((p_adult(feats["validation"]) >= 0.5).mean()),
        "adults_test_half_heldout": float((p_adult(feats["adults"][test_idx]) >= 0.5).mean()),
        "adults_calibration_half_fitted_on": float((p_adult(feats["adults"][cal_idx]) >= 0.5).mean()),
        "synthetic_non_xray": float((p_adult(feats["synthetic"]) >= 0.5).mean()),
    }

    # How many of V1's adult false alarms (no-finding images V1 calls pneumonia at 0.82) does it catch?
    held_flag = p_adult(feats["adults"][test_idx]) >= 0.5
    held_probs = probs["adults"][test_idx]
    held_neg = y_adult[test_idx] == 0
    false_alarm = held_neg & (held_probs >= 0.82)
    held_pos = y_adult[test_idx] == 1
    child_flag = p_adult(feats["test"]) >= 0.5

    report = {
        "fit": {"children_train": int(len(feats["train"])), "adults_calibration_half": int(len(cal_idx))},
        "held_out": {"adults_test_half": int(len(test_idx)), "children_test": int(len(feats["test"])),
                     "children_validation": int(len(feats["validation"]))},
        "flagged_fraction": {k: round(v, 4) for k, v in flagged.items()},
        "v1_false_alarms_on_held_out_adults": {
            "count": int(false_alarm.sum()),
            "caught_by_check": int((false_alarm & held_flag).sum()),
        },
        "adult_pneumonia_flagged_fraction": round(float(held_flag[held_pos].mean()), 4),
        "criteria": {
            "heldout_adults_flagged_at_least_95pct": bool(flagged["adults_test_half_heldout"] >= 0.95),
            "children_test_flagged_at_most_3pct": bool(flagged["children_test"] <= 0.03),
            "children_validation_flagged_at_most_3pct": bool(flagged["children_validation"] <= 0.03),
        },
    }
    report["passes"] = all(report["criteria"].values())
    print(json.dumps(report, indent=1))

    if report["passes"]:
        report["model"] = {
            "mean": scaler.mean_.round(6).tolist(),
            "scale": scaler.scale_.round(6).tolist(),
            "coef": clf.coef_[0].round(6).tolist(),
            "intercept": round(float(clf.intercept_[0]), 6),
        }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f)


if __name__ == "__main__":
    main()
