import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

# ==============================
# SETTINGS
# ==============================

TEST_PATH = "dataset/archive/chest_xray/test"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32


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

print()
print("Model loaded successfully.")


# ==============================
# GET PREDICTIONS
# ==============================

y_true = []
y_pred = []

for images, labels in test_dataset:

    predictions = model.predict(
        images,
        verbose=0
    )

    predictions = predictions.ravel()

    predicted_classes = (predictions >= 0.5).astype(int)

    y_true.extend(labels.numpy())
    y_pred.extend(predicted_classes)


y_true = np.array(y_true)
y_pred = np.array(y_pred)


# ==============================
# CONFUSION MATRIX
# ==============================

cm = confusion_matrix(
    y_true,
    y_pred
)

print()
print("===== CONFUSION MATRIX =====")
print(cm)


# ==============================
# CLASSIFICATION REPORT
# ==============================

print()
print("===== CLASSIFICATION REPORT =====")

print(
    classification_report(
        y_true,
        y_pred,
        target_names=class_names
    )
)
