import tensorflow as tf
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)

# ==============================
# SETTINGS
# ==============================

TEST_PATH = "dataset/archive/chest_xray/test"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

THRESHOLD = 0.40


# ==============================
# LOAD TEST DATA
# ==============================

test_dataset = tf.keras.utils.image_dataset_from_directory(
    TEST_PATH,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb",
    shuffle=False
)

class_names = test_dataset.class_names

print()
print("Classes:", class_names)


# ==============================
# LOAD MODEL
# ==============================

model = tf.keras.models.load_model(
    "saved_models/best_model.h5"
)

print("Model loaded successfully.")


# ==============================
# GET PREDICTIONS
# ==============================

y_true = []
y_probability = []

for images, labels in test_dataset:

    predictions = model.predict(
        images,
        verbose=0
    )

    y_true.extend(labels.numpy())
    y_probability.extend(predictions.ravel())


y_true = np.array(y_true)
y_probability = np.array(y_probability)


# ==============================
# APPLY THRESHOLD
# ==============================

y_pred = (
    y_probability >= THRESHOLD
).astype(int)


# ==============================
# METRICS
# ==============================

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


# ==============================
# CONFUSION MATRIX
# ==============================

cm = confusion_matrix(
    y_true,
    y_pred
)

tn, fp, fn, tp = cm.ravel()

specificity = tn / (tn + fp)


# ==============================
# RESULTS
# ==============================

print()
print("========================================")
print("       FINAL TEST RESULTS")
print("========================================")

print(f"Threshold:   {THRESHOLD:.2f}")
print(f"Accuracy:    {accuracy:.4f}")
print(f"Precision:   {precision:.4f}")
print(f"Recall:      {recall:.4f}")
print(f"Specificity: {specificity:.4f}")
print(f"AUC:         {auc:.4f}")

print()
print("===== CONFUSION MATRIX =====")
print(cm)

print()
print("===== CLASSIFICATION REPORT =====")

print(
    classification_report(
        y_true,
        y_pred,
        target_names=class_names
    )
)
