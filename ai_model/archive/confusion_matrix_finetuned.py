import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

TEST_PATH = "dataset/archive/chest_xray/test"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

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

model = tf.keras.models.load_model(
    "saved_models/fine_tuned_model.h5"
)

print()
print("Fine-tuned model loaded.")

y_true = []
y_pred = []

for images, labels in test_dataset:

    predictions = model.predict(
        images,
        verbose=0
    ).ravel()

    predicted_classes = (
        predictions >= 0.5
    ).astype(int)

    y_true.extend(labels.numpy())
    y_pred.extend(predicted_classes)

y_true = np.array(y_true)
y_pred = np.array(y_pred)

cm = confusion_matrix(
    y_true,
    y_pred
)

print()
print("===== FINE-TUNED CONFUSION MATRIX =====")
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