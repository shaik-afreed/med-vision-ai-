"""
Honest V1-vs-candidate comparison.

Rules fixed BEFORE looking at any test result:
  * A candidate's decision threshold is chosen with Youden's J on the
    CALIBRATION split (patients never used for training or validation).
  * The best candidate is chosen by calibration-set AUC, never by test results.
  * V1 is evaluated exactly as deployed (threshold 0.82).
  * Metrics are reported on (a) all 624 Kermany test images and (b) V1's own
    375-image holdout subset (same split code as ai_model/evaluate_model.py).
  * Paired bootstrap tells whether an accuracy gain over V1 is distinguishable
    from sampling noise.
"""
import csv
import json
import os
import sys

import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
MODELS = os.path.join(HERE, "models")
V1_PATH = os.path.join(os.path.dirname(HERE), "saved_models", "fine_tuned_model.h5")
V1_THRESHOLD = 0.82
SEED = 42


def predict(model, x, tta):
    out = []
    for start in range(0, len(x), 64):
        batch = x[start:start + 64].astype(np.float32)
        p = model.predict(batch, verbose=0).ravel()
        if tta:
            p = (p + model.predict(batch[:, :, ::-1, :], verbose=0).ravel()) / 2.0
        out.append(p)
    return np.concatenate(out)


def youden_threshold(y, p):
    best_t, best_j = 0.5, -1.0
    for t in np.unique(np.round(p, 4)):
        pred = p >= t
        tp, fn = int(((y == 1) & pred).sum()), int(((y == 1) & ~pred).sum())
        tn, fp = int(((y == 0) & ~pred).sum()), int(((y == 0) & pred).sum())
        j = tp / max(tp + fn, 1) + tn / max(tn + fp, 1) - 1
        if j > best_j:
            best_t, best_j = float(t), j
    return best_t


def metrics(y, p, t):
    pred = (p >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "threshold": round(float(t), 4),
        "accuracy": round((tp + tn) / len(y), 4),
        "sensitivity": round(recall, 4),
        "specificity": round(tn / max(tn + fp, 1), 4),
        "precision": round(precision, 4),
        "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def paired_bootstrap(y, p_new, t_new, p_old, t_old, rounds=2000):
    rng = np.random.default_rng(SEED)
    correct_new = ((p_new >= t_new).astype(int) == y).astype(float)
    correct_old = ((p_old >= t_old).astype(int) == y).astype(float)
    diffs = []
    for _ in range(rounds):
        idx = rng.integers(0, len(y), len(y))
        diffs.append(correct_new[idx].mean() - correct_old[idx].mean())
    low, high = np.percentile(diffs, [2.5, 97.5])
    return {"accuracy_gain": round(float(correct_new.mean() - correct_old.mean()), 4),
            "ci95": [round(float(low), 4), round(float(high), 4)],
            "gain_is_significant": bool(low > 0)}


def main():
    names = sys.argv[1:] or ["A", "B"]

    x = {s: np.load(f"{CACHE}/{s}_x.npy") for s in ("validation", "calibration", "test")}
    y = {s: np.load(f"{CACHE}/{s}_y.npy").astype(int) for s in ("validation", "calibration", "test")}

    # V1's own holdout subset (identical to ai_model/evaluate_model.py).
    _, holdout_idx = train_test_split(
        np.arange(len(y["test"])), test_size=0.6, stratify=y["test"], random_state=SEED
    )

    models = {"V1 (deployed)": tf.keras.models.load_model(V1_PATH)}
    for name in names:
        models[f"Candidate {name}"] = tf.keras.models.load_model(os.path.join(MODELS, f"{name}.h5"))

    probs = {}
    for label, model in models.items():
        tta = label != "V1 (deployed)"
        probs[label] = {s: predict(model, x[s], tta) for s in x}
        print(f"predicted with {label} (flip-TTA: {tta})")

    report = {"models": {}, "v1_holdout_images": len(holdout_idx)}
    for label in models:
        p = probs[label]
        entry = {
            "auc_validation": round(float(roc_auc_score(y["validation"], p["validation"])), 4),
            "auc_calibration": round(float(roc_auc_score(y["calibration"], p["calibration"])), 4),
        }
        if label == "V1 (deployed)":
            threshold = V1_THRESHOLD
            entry["threshold_source"] = "deployed value 0.82 (calibrated on part of the test set)"
        else:
            threshold = youden_threshold(y["calibration"], p["calibration"])
            entry["threshold_source"] = "Youden's J on the patient-grouped calibration split"
        entry["full_test_624"] = metrics(y["test"], p["test"], threshold)
        entry["v1_holdout_375"] = metrics(y["test"][holdout_idx], p["test"][holdout_idx], threshold)
        report["models"][label] = entry

    candidates = [l for l in models if l != "V1 (deployed)"]
    chosen = max(candidates, key=lambda l: (report["models"][l]["auc_calibration"], report["models"][l]["auc_validation"]))
    report["selected_by_calibration_auc"] = chosen

    v1 = probs["V1 (deployed)"]
    for label in candidates:
        t_new = report["models"][label]["full_test_624"]["threshold"]
        report["models"][label]["vs_v1_paired_bootstrap"] = {
            "full_test_624": paired_bootstrap(y["test"], probs[label]["test"], t_new, v1["test"], V1_THRESHOLD),
            "v1_holdout_375": paired_bootstrap(
                y["test"][holdout_idx], probs[label]["test"][holdout_idx], t_new,
                v1["test"][holdout_idx], V1_THRESHOLD),
        }

    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    manifest = json.load(open(os.path.join(HERE, "splits.json")))["splits"]["test"]
    with open(os.path.join(HERE, "test_predictions.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "label"] + list(models))
        for i, name in enumerate(manifest):
            writer.writerow([name, int(y["test"][i])] + [f"{probs[l]['test'][i]:.6f}" for l in models])

    print("\n" + "=" * 78)
    for label, entry in report["models"].items():
        for scope in ("full_test_624", "v1_holdout_375"):
            m = entry[scope]
            print(f"{label:16} {scope:15} acc {m['accuracy']:.4f}  sens {m['sensitivity']:.4f}  spec {m['specificity']:.4f}  "
                  f"auc {m['auc']:.4f}  thr {m['threshold']}  missed-pneumonia {m['fn']}  false-alarms {m['fp']}")
        if "vs_v1_paired_bootstrap" in entry:
            for scope, b in entry["vs_v1_paired_bootstrap"].items():
                print(f"{'':16} vs V1 on {scope}: accuracy gain {b['accuracy_gain']:+.4f}, 95% CI {b['ci95']}, significant: {b['gain_is_significant']}")
    print("=" * 78)
    print("Selected by calibration AUC (pre-registered rule):", chosen)


if __name__ == "__main__":
    main()
