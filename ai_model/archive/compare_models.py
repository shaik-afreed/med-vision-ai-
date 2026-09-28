import tensorflow as tf
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
    roc_auc_score
)

# ==============================
# SETTINGS
# ==============================

TEST_PATH = "dataset/archive/chest_xray/test"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

THRESHOLD = 0.50


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

print()
print("Classes:", test_dataset.class_names)


# ==============================
# EVALUATION FUNCTION
# ==============================

def evaluate_model(model_path, model_name):

    print()
    print("========================================")
    print(model_name)
    print("========================================")

    model = tf.keras.models.load_model(model_path)

    print("Model loaded.")

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

    y_pred = (
        y_probability >= THRESHOLD
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

    auc = roc_auc_score(
        y_true,
        y_probability
    )

    cm = confusion_matrix(
        y_true,
        y_pred
    )

    tn, fp, fn, tp = cm.ravel()

    specificity = tn / (tn + fp)

    print()
    print(f"Accuracy:    {accuracy:.4f}")
    print(f"Precision:   {precision:.4f}")
    print(f"Recall:      {recall:.4f}")
    print(f"Specificity: {specificity:.4f}")
    print(f"AUC:         {auc:.4f}")

    print()
    print("Confusion Matrix:")
    print(cm)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "auc": auc
    }


# ==============================
# PHASE 1
# ==============================

phase1 = evaluate_model(
    "saved_models/best_model.h5",
    "PHASE 1 - MOBILENETV2"
)


# ==============================
# PHASE 2
# ==============================

phase2 = evaluate_model(
    "saved_models/fine_tuned_model.h5",
    "PHASE 2 - FINE-TUNED"
)


# ==============================
# COMPARISON
# ==============================

print()
print("========================================")
print("           MODEL COMPARISON")
print("========================================")

print()
print("Metric          Phase 1       Phase 2")

print(
    f"Accuracy        "
    f"{phase1['accuracy']:.4f}        "
    f"{phase2['accuracy']:.4f}"
)

print(
    f"Precision       "
    f"{phase1['precision']:.4f}        "
    f"{phase2['precision']:.4f}"
)

print(
    f"Recall          "
    f"{phase1['recall']:.4f}        "
    f"{phase2['recall']:.4f}"
)

print(
    f"Specificity     "
    f"{phase1['specificity']:.4f}        "
    f"{phase2['specificity']:.4f}"
)

print(
    f"AUC             "
    f"{phase1['auc']:.4f}        "
    f"{phase2['auc']:.4f}"
)
