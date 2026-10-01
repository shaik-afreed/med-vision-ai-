"""
Measures how trustworthy each pneumonia-probability range is for the deployed
model, on the 624-image Kermany test set, and writes probability_bands.json.

The backend (services/assessment.py) uses this to turn a raw probability into
a plain-language category with a measured, honest reliability figure - e.g.
"scores of 67-82% were truly pneumonia 53% of the time on the test set".

Re-run this whenever the deployed model changes; the JSON records which model
version it describes, and the backend ignores it for any other version.

Requires ai_model/improve/prepare_data.py to have been run (cached test arrays).
"""
import json
import os
from datetime import date

import numpy as np
import tensorflow as tf

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "saved_models", "fine_tuned_model.h5")
CACHE = os.path.join(HERE, "improve", "cache")
OUT = os.path.join(HERE, "probability_bands.json")

MODEL_VERSION = "mobilenetv2-finetuned-v1"
# Band edges (percent). 67 = 82 (decision threshold) - 15: below ~67% the share
# of true pneumonia drops under a third; between 67 and 82 it is a coin flip.
EDGES = [0, 20, 50, 67, 82, 95, 100.0001]
CATEGORIES = ["very_low", "low", "probably_normal", "inconclusive", "high", "very_high"]


def main():
    x = np.load(os.path.join(CACHE, "test_x.npy"))
    y = np.load(os.path.join(CACHE, "test_y.npy")).astype(int)
    model = tf.keras.models.load_model(MODEL_PATH)
    p = np.concatenate([
        model.predict(x[i:i + 64].astype(np.float32), verbose=0).ravel() for i in range(0, len(x), 64)
    ]) * 100

    bands = []
    for category, low, high in zip(CATEGORIES, EDGES[:-1], EDGES[1:]):
        mask = (p >= low) & (p < high)
        n = int(mask.sum())
        bands.append({
            "category": category,
            "min_percent": low,
            "max_percent": min(high, 100),
            "images": n,
            "truly_pneumonia": int(y[mask].sum()),
            "pneumonia_share": round(float(y[mask].mean()), 4) if n else None,
        })

    result = {
        "model_version": MODEL_VERSION,
        "evaluated_on": f"Kermany test set, {len(y)} images ({int((y == 0).sum())} normal, {int((y == 1).sum())} pneumonia)",
        "decision_threshold_percent": 82,
        "generated": date.today().isoformat(),
        "caveat": "Measured on one pediatric dataset; may not hold for other populations or X-ray equipment.",
        "bands": bands,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    for b in bands:
        print(f"{b['min_percent']:>5}-{b['max_percent']:<5} {b['category']:16} {b['images']:4} images, "
              f"{b['truly_pneumonia']:4} truly pneumonia ({100 * (b['pneumonia_share'] or 0):.0f}%)")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
