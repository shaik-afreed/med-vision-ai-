"""Same footing as V1: V1's 0.82 cutoff was tuned on 249 test images and
reported on the other 375. Tune A and B the same way (Youden's J on the 249)
and compare all three on the untouched 375."""
import json, os, sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from evaluate_improved import youden_threshold, metrics, SEED

d = pd.read_csv(f"{HERE}/test_predictions.csv")
y = d.label.values.astype(int)
assert (y == np.load(f"{HERE}/cache/test_y.npy").astype(int)).all()
tune_idx, hold_idx = train_test_split(np.arange(len(y)), test_size=0.6, stratify=y, random_state=SEED)
print(f"tuning {len(tune_idx)}  holdout {len(hold_idx)}")

v1 = d["V1 (deployed)"].values
v1_ok = (v1[hold_idx] >= 0.82).astype(int) == y[hold_idx]
print("V1 youden on tuning part (for reference):", youden_threshold(y[tune_idx], v1[tune_idx]))
mv = metrics(y[hold_idx], v1[hold_idx], 0.82)
print(f"V1 cutoff 0.82    holdout acc {mv['accuracy']} sens {mv['sensitivity']} spec {mv['specificity']} missed {mv['fn']} false-alarms {mv['fp']} auc {mv['auc']}")

rng = np.random.default_rng(SEED)
out = {"V1": mv}
for col in ("Candidate A", "Candidate B"):
    p = d[col].values
    t = youden_threshold(y[tune_idx], p[tune_idx])
    m = metrics(y[hold_idx], p[hold_idx], t)
    ok = (p[hold_idx] >= t).astype(int) == y[hold_idx]
    diffs = []
    for _ in range(4000):
        i = rng.integers(0, len(hold_idx), len(hold_idx))
        diffs.append(ok[i].mean() - v1_ok[i].mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    m["acc_gain_vs_v1"] = round(float(ok.mean() - v1_ok.mean()), 4)
    m["ci95"] = [round(float(lo), 4), round(float(hi), 4)]
    out[col] = m
    print(f"{col} cutoff {t:.4f} holdout acc {m['accuracy']} sens {m['sensitivity']} spec {m['specificity']} "
          f"missed {m['fn']} false-alarms {m['fp']} auc {m['auc']} | gain {m['acc_gain_vs_v1']:+.4f} CI [{lo:+.4f}, {hi:+.4f}]")

json.dump(out, open(os.path.join(HERE, "same_footing.json"), "w"), indent=1)
