"""Independent external test: deployed V1 vs candidate B on adult chest X-rays
from the NIH ChestX-ray14 dataset (a different hospital system and age group
than the pediatric training data).

Data: Hugging Face dataset timm/nih-chest-xray-14, official TEST split,
parquet shards test-00000..00003 (downloaded separately, see README.md).
Positives: images whose labels include "Pneumonia". Negatives: images with no
finding (empty label list). From each shard every positive is kept and up to
NEG_PER_POS x as many negatives are sampled at random (fixed seed).

Known limits of this data, stated before seeing any result:
- NIH labels were text-mined from radiology reports (NIH estimates >90%
  accuracy); pneumonia is hard to call on a single X-ray, and published
  models reach only about 0.77 AUC for pneumonia on this dataset.
- "No Finding" is not the same as "normal".

PRE-REGISTERED ANALYSIS (written before any model was run on this data):
1. Primary: AUC of V1 and B on the TEST half. B is "demonstrably better"
   only if the 95% paired-bootstrap CI of (AUC_B - AUC_V1) is above zero.
2. Operating point: each model's cutoff is chosen by Youden's J on the
   CALIBRATION half; sensitivity, specificity and accuracy are then reported
   on the TEST half, with a paired bootstrap CI for the accuracy difference.
3. Descriptive only: both models at their current cutoffs (V1 0.82, B 0.842).
The calibration and test halves are split by patient (no patient in both).

Usage (from ai_model/):  python external/nih_eval.py extract <shard.parquet>...
                         python external/nih_eval.py evaluate
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
AI_MODEL = os.path.dirname(HERE)
V1_PATH = os.path.join(AI_MODEL, "saved_models", "fine_tuned_model.h5")
B_PATH = os.path.join(AI_MODEL, "improve", "models", "B.h5")
V1_CUTOFF, B_CUTOFF = 0.82, 0.842
IMAGE_SIZE = (224, 224)  # same as backend/services/prediction.py
NEG_PER_POS = 4
SEED = 42


def extract(shards):
    import pyarrow.parquet as pq
    from PIL import Image

    rng = np.random.default_rng(SEED)
    os.makedirs(CACHE, exist_ok=True)
    images, meta = [], []

    for shard in shards:
        table = pq.read_table(shard, columns=["image", "label_names", "image_id", "patient_id",
                                              "patient_age", "patient_sex", "view_position"])
        rows = table.to_pylist()
        positives = [r for r in rows if "Pneumonia" in r["label_names"]]
        negatives = [r for r in rows if not r["label_names"]]
        pick = rng.choice(len(negatives), size=min(len(negatives), NEG_PER_POS * len(positives)), replace=False)
        chosen = [(r, 1) for r in positives] + [(negatives[i], 0) for i in sorted(pick)]

        for row, label in chosen:
            # Exactly the production preprocessing: RGB, plain PIL resize.
            image = Image.open(io.BytesIO(row["image"]["bytes"])).convert("RGB").resize(IMAGE_SIZE)
            images.append(np.asarray(image, dtype=np.uint8))
            meta.append({
                "image_id": row["image_id"], "label": label, "patient_id": int(row["patient_id"]),
                "age": int(row["patient_age"]), "sex": row["patient_sex"], "view": row["view_position"],
                "findings": list(row["label_names"]),
            })
        print(f"{os.path.basename(shard)}: {len(positives)} pneumonia, {len(pick)} no-finding kept")

    np.save(os.path.join(CACHE, "nih_x.npy"), np.stack(images))
    with open(os.path.join(CACHE, "nih_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    print(f"saved {len(meta)} images ({sum(m['label'] for m in meta)} pneumonia)")


def _predict(model, x, tta):
    out = []
    for start in range(0, len(x), 64):
        batch = x[start:start + 64].astype(np.float32)
        p = model.predict(batch, verbose=0).ravel()
        if tta:
            p = (p + model.predict(batch[:, :, ::-1, :], verbose=0).ravel()) / 2.0
        out.append(p)
    return np.concatenate(out)


def _youden(y, p):
    best_t, best_j = 0.5, -1.0
    for t in np.unique(np.round(p, 4)):
        pred = p >= t
        j = pred[y == 1].mean() + (~pred[y == 0]).mean() - 1
        if j > best_j:
            best_t, best_j = float(t), float(j)
    return best_t


def _point(y, p, t):
    pred = p >= t
    tp, fn = int((pred & (y == 1)).sum()), int((~pred & (y == 1)).sum())
    tn, fp = int((~pred & (y == 0)).sum()), int((pred & (y == 0)).sum())
    return {"cutoff": round(t, 4), "sensitivity": round(tp / max(tp + fn, 1), 4),
            "specificity": round(tn / max(tn + fp, 1), 4), "accuracy": round((tp + tn) / len(y), 4),
            "missed_pneumonia": fn, "false_alarms": fp}


def evaluate():
    import tensorflow as tf
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupShuffleSplit

    x = np.load(os.path.join(CACHE, "nih_x.npy"))
    meta = json.load(open(os.path.join(CACHE, "nih_meta.json"), encoding="utf-8"))
    y = np.array([m["label"] for m in meta])
    groups = np.array([m["patient_id"] for m in meta])

    cal_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=SEED).split(x, y, groups))
    assert not set(groups[cal_idx]) & set(groups[test_idx])

    probs = {
        "V1": _predict(tf.keras.models.load_model(V1_PATH), x, tta=False),
        "B": _predict(tf.keras.models.load_model(B_PATH, compile=False), x, tta=True),
    }

    yt = y[test_idx]
    report = {
        "images": len(y), "pneumonia": int(y.sum()),
        "calibration_images": len(cal_idx), "test_images": len(test_idx),
        "test_pneumonia": int(yt.sum()),
        "median_age": float(np.median([m["age"] for m in meta])),
        "models": {},
    }
    for name, p in probs.items():
        cutoff = _youden(y[cal_idx], p[cal_idx])
        report["models"][name] = {
            "auc_test": round(float(roc_auc_score(yt, p[test_idx])), 4),
            "at_calibrated_cutoff": _point(yt, p[test_idx], cutoff),
            "at_current_cutoff": _point(yt, p[test_idx], V1_CUTOFF if name == "V1" else B_CUTOFF),
        }

    # Paired bootstrap on the test half.
    rng = np.random.default_rng(SEED)
    pv, pb = probs["V1"][test_idx], probs["B"][test_idx]
    tv = report["models"]["V1"]["at_calibrated_cutoff"]["cutoff"]
    tb = report["models"]["B"]["at_calibrated_cutoff"]["cutoff"]
    auc_d, acc_d = [], []
    for _ in range(2000):
        i = rng.integers(0, len(yt), len(yt))
        if yt[i].min() == yt[i].max():
            continue
        auc_d.append(roc_auc_score(yt[i], pb[i]) - roc_auc_score(yt[i], pv[i]))
        acc_d.append(((pb[i] >= tb) == yt[i]).mean() - ((pv[i] >= tv) == yt[i]).mean())
    report["auc_gain_B_minus_V1"] = {
        "estimate": round(report["models"]["B"]["auc_test"] - report["models"]["V1"]["auc_test"], 4),
        "ci95": [round(float(v), 4) for v in np.percentile(auc_d, [2.5, 97.5])],
    }
    report["accuracy_gain_B_minus_V1_at_calibrated_cutoffs"] = {
        "ci95": [round(float(v), 4) for v in np.percentile(acc_d, [2.5, 97.5])],
    }
    report["B_demonstrably_better"] = bool(report["auc_gain_B_minus_V1"]["ci95"][0] > 0)

    with open(os.path.join(HERE, "nih_results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["extract"]:
        extract(sys.argv[2:])
    elif sys.argv[1:2] == ["evaluate"]:
        evaluate()
    else:
        print(__doc__)
