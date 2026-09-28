import tensorflow as tf
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix

# ==============================
# SETTINGS
# ==============================

DATASET_PATH = "dataset/archive/chest_xray/train"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 42


# ==============================
# LOAD VALIDATION DATA
# ==============================

validation_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.20,
    subset="validation",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb",
    shuffle=True
)

print()
print("Classes:", validation_dataset.class_names)


# ==============================
# LOAD MODEL
# ==============================

model = tf.keras.models.load_model(
    "saved_models/fine_tuned_model.h5"
)

print("Model loaded successfully.")


# ==============================
# GET VALIDATION PREDICTIONS
# ==============================

y_true = []
y_probability = []

for images, labels in validation_dataset:

    predictions = model.predict(
        images,
        verbose=0
    )

    y_true.extend(labels.numpy())
    y_probability.extend(predictions.ravel())


y_true = np.array(y_true)
y_probability = np.array(y_probability)


# ==============================
# TEST DIFFERENT THRESHOLDS
# ==============================

thresholds = [
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70
]

print()
print("===== THRESHOLD ANALYSIS =====")

for threshold in thresholds:

    y_pred = (
        y_probability >= threshold
    ).astype(int)

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

    cm = confusion_matrix(
        y_true,
        y_pred
    )

    tn, fp, fn, tp = cm.ravel()

    specificity = tn / (tn + fp)

    print()
    print(f"Threshold: {threshold:.2f}")
    print(f"Accuracy:    {accuracy:.4f}")
    print(f"Precision:   {precision:.4f}")
    print(f"Recall:      {recall:.4f}")
    print(f"Specificity: {specificity:.4f}")
    print(f"TN: {tn} | FP: {fp} | FN: {fn} | TP: {tp}")
