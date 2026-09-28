import os
import numpy as np
import tensorflow as tf
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)

# ============================================
# SETTINGS
# ============================================

TEST_PATH = "dataset/archive/chest_xray/test"

MODEL_PATH = "saved_models/fine_tuned_model.h5"

IMAGE_SIZE = (224, 224)

THRESHOLD = 0.50


# ============================================
# LOAD MODEL
# ============================================

print("Loading fine-tuned model...")

model = tf.keras.models.load_model(
    MODEL_PATH
)

print("Fine-tuned model loaded successfully.")


# ============================================
# CLASS MAPPING
# ============================================

class_names = [
    "NORMAL",
    "PNEUMONIA"
]

print()
print("Classes:", class_names)


# ============================================
# GET IMAGE FILES
# ============================================

normal_path = os.path.join(
    TEST_PATH,
    "NORMAL"
)

pneumonia_path = os.path.join(
    TEST_PATH,
    "PNEUMONIA"
)

normal_files = [
    os.path.join(normal_path, f)
    for f in os.listdir(normal_path)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

pneumonia_files = [
    os.path.join(pneumonia_path, f)
    for f in os.listdir(pneumonia_path)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]


# ============================================
# SORT FOR REPRODUCIBILITY
# ============================================

normal_files.sort()
pneumonia_files.sort()


all_files = normal_files + pneumonia_files

y_true = (
    [0] * len(normal_files)
    +
    [1] * len(pneumonia_files)
)


print()
print("NORMAL images:", len(normal_files))
print("PNEUMONIA images:", len(pneumonia_files))
print("TOTAL images:", len(all_files))


# ============================================
# PREDICT USING SAME PREPROCESSING AS predict.py
# ============================================

y_probability = []


print()
print("Running predictions...")


for index, image_path in enumerate(all_files):

    image = Image.open(image_path)
    image = image.convert("RGB")
    image = image.resize(IMAGE_SIZE)

    image_array = np.array(image).astype(np.float32)

    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    probability = model.predict(
        image_array,
        verbose=0
    )[0][0]

    y_probability.append(
        float(probability)
    )

    if (index + 1) % 50 == 0:

        print(
            f"Processed {index + 1}/{len(all_files)}"
        )


y_true = np.array(y_true)

y_probability = np.array(
    y_probability
)


# ============================================
# APPLY THRESHOLD
# ============================================

y_pred = (
    y_probability >= THRESHOLD
).astype(int)


# ============================================
# METRICS
# ============================================

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

auc = roc_auc_score(
    y_true,
    y_probability
)


# ============================================
# CONFUSION MATRIX
# ============================================

cm = confusion_matrix(
    y_true,
    y_pred
)

tn, fp, fn, tp = cm.ravel()

specificity = tn / (
    tn + fp
)


# ============================================
# RESULTS
# ============================================

print()
print("========================================")
print("   CORRECT PIPELINE TEST RESULTS")
print("========================================")

print(
    f"Threshold:   {THRESHOLD:.2f}"
)

print(
    f"Accuracy:    {accuracy:.4f}"
)

print(
    f"Precision:   {precision:.4f}"
)

print(
    f"Recall:      {recall:.4f}"
)

print(
    f"Specificity: {specificity:.4f}"
)

print(
    f"AUC:         {auc:.4f}"
)


# ============================================
# CONFUSION MATRIX
# ============================================

print()
print("===== CONFUSION MATRIX =====")

print(cm)


# ============================================
# CLASSIFICATION REPORT
# ============================================

print()
print("===== CLASSIFICATION REPORT =====")

print(
    classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=4
    )
)


# ============================================
# PROBABILITY SUMMARY
# ============================================

normal_probabilities = y_probability[
    y_true == 0
]

pneumonia_probabilities = y_probability[
    y_true == 1
]


print()
print("===== PROBABILITY SUMMARY =====")

print(
    "NORMAL mean pneumonia probability:",
    f"{normal_probabilities.mean():.4f}"
)

print(
    "NORMAL minimum:",
    f"{normal_probabilities.min():.4f}"
)

print(
    "NORMAL maximum:",
    f"{normal_probabilities.max():.4f}"
)

print()

print(
    "PNEUMONIA mean pneumonia probability:",
    f"{pneumonia_probabilities.mean():.4f}"
)

print(
    "PNEUMONIA minimum:",
    f"{pneumonia_probabilities.min():.4f}"
)

print(
    "PNEUMONIA maximum:",
    f"{pneumonia_probabilities.max():.4f}"
)
