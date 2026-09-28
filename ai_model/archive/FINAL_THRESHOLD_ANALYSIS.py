import os
import numpy as np
import tensorflow as tf
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score
)

# ============================================================
# SETTINGS
# ============================================================

MODEL_PATH = "saved_models/fine_tuned_model.h5"
TEST_PATH = "dataset/archive/chest_xray/test"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

# ============================================================
# LOAD MODEL
# ============================================================

print("=" * 60)
print("MEDIVISION AI - FINAL THRESHOLD ANALYSIS")
print("=" * 60)

print("\nLoading model...")

model = tf.keras.models.load_model(MODEL_PATH)

print("Model loaded successfully.")

# ============================================================
# LOAD TEST IMAGES
# ============================================================

normal_dir = os.path.join(TEST_PATH, "NORMAL")
pneumonia_dir = os.path.join(TEST_PATH, "PNEUMONIA")

normal_files = sorted([
    os.path.join(normal_dir, f)
    for f in os.listdir(normal_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
])

pneumonia_files = sorted([
    os.path.join(pneumonia_dir, f)
    for f in os.listdir(pneumonia_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
])

all_files = normal_files + pneumonia_files

y_true = np.array(
    [0] * len(normal_files) +
    [1] * len(pneumonia_files)
)

print("\nNORMAL:", len(normal_files))
print("PNEUMONIA:", len(pneumonia_files))
print("TOTAL:", len(all_files))

# ============================================================
# LOAD + PREDICT ONCE
# ============================================================

print("\nRunning predictions ONCE...")

images = []

for path in all_files:

    image = Image.open(path).convert("RGB")
    image = image.resize(IMAGE_SIZE)

    image = np.array(image).astype(np.float32)

    # IMPORTANT:
    # Model contains its own preprocessing.
    images.append(image)

images = np.array(images)

print("Image array:", images.shape)

probabilities = model.predict(
    images,
    batch_size=BATCH_SIZE,
    verbose=1
).ravel()

print("\nPredictions completed.")

# ============================================================
# AUC
# ============================================================

auc = roc_auc_score(
    y_true,
    probabilities
)

print("\nAUC:", f"{auc:.4f}")

# ============================================================
# THRESHOLD ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("THRESHOLD ANALYSIS")
print("=" * 60)

results = []

thresholds = np.arange(
    0.10,
    0.91,
    0.01
)

for threshold in thresholds:

    y_pred = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1]
    ).ravel()

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0
    )

    specificity = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else 0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )

    results.append({
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp
    })

# ============================================================
# BEST BALANCED THRESHOLD
# ============================================================

# Require pneumonia recall >= 0.95
eligible = [
    r for r in results
    if r["recall"] >= 0.95
]

best = max(
    eligible,
    key=lambda r: (
        r["specificity"] +
        r["recall"]
    ) / 2
)

print("\n" + "=" * 60)
print("BEST BALANCED THRESHOLD")
print("=" * 60)

print(
    "Threshold:   ",
    f"{best['threshold']:.2f}"
)

print(
    "Accuracy:    ",
    f"{best['accuracy']:.4f}"
)

print(
    "Precision:   ",
    f"{best['precision']:.4f}"
)

print(
    "Recall:      ",
    f"{best['recall']:.4f}"
)

print(
    "Specificity: ",
    f"{best['specificity']:.4f}"
)

print(
    "F1:          ",
    f"{best['f1']:.4f}"
)

print(
    "Confusion:   ",
    [[best["tn"], best["fp"]],
     [best["fn"], best["tp"]]]
)

# ============================================================
# SHOW IMPORTANT THRESHOLDS
# ============================================================

print("\n" + "=" * 60)
print("IMPORTANT THRESHOLDS")
print("=" * 60)

print(
    "\nThreshold | Accuracy | Precision | Recall | Specificity | F1"
)

print("-" * 65)

for target in [0.20, 0.25, 0.30, 0.31, 0.35,
               0.40, 0.45, 0.50, 0.55, 0.60,
               0.65, 0.70, 0.75, 0.80]:

    closest = min(
        results,
        key=lambda r: abs(
            r["threshold"] - target
        )
    )

    print(
        f"{closest['threshold']:.2f}      | "
        f"{closest['accuracy']:.4f}   | "
        f"{closest['precision']:.4f}    | "
        f"{closest['recall']:.4f} | "
        f"{closest['specificity']:.4f}      | "
        f"{closest['f1']:.4f}"
    )

# ============================================================
# FINAL RECOMMENDATION
# ============================================================

print("\n" + "=" * 60)
print("RECOMMENDATION")
print("=" * 60)

print(
    f"\nRecommended threshold: {best['threshold']:.2f}"
)

print(
    "\nThis threshold keeps pneumonia recall at or above 95%"
    " while improving the NORMAL/PNEUMONIA balance."
)

print(
    "\nDo NOT change the model weights based only on this test."
)

print(
    "\nThreshold analysis completed."
)