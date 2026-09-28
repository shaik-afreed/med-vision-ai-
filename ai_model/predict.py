import os
import numpy as np
import tensorflow as tf
from PIL import Image


# ==============================
# SETTINGS
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "saved_models", "fine_tuned_model.h5")
IMAGE_SIZE = (224, 224)

# Operating threshold selected by evaluate_model.py; keep in sync with
# backend/services/prediction.py. See evaluation_report.json for details.
THRESHOLD = 0.82


# ==============================
# LOAD MODEL
# ==============================

print("Loading MediVision AI model...")

model = tf.keras.models.load_model(MODEL_PATH)

print("Model loaded successfully.")


# ==============================
# PREDICT X-RAY
# ==============================

def predict_xray(image_path):
    # Check file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Open image
    image = Image.open(image_path)

    # Convert to RGB
    image = image.convert("RGB")

    # Resize
    image = image.resize(IMAGE_SIZE)

    # Convert to NumPy
    image_array = np.array(image, dtype=np.float32)

    # Add batch dimension
    image_array = np.expand_dims(image_array, axis=0)

    # Prediction
    probability = model.predict(image_array, verbose=0)[0][0]

    # Classification
    if probability >= THRESHOLD:
        prediction = "PNEUMONIA"
        confidence = probability
    else:
        prediction = "NORMAL"
        confidence = 1 - probability

    return {
        "prediction": prediction,
        "confidence": float(confidence),
        "pneumonia_probability": float(probability)
    }


# ==============================
# TEST
# ==============================

if __name__ == "__main__":
    test_image = os.path.join(
        BASE_DIR,
        "dataset",
        "archive",
        "chest_xray",
        "test",
        "PNEUMONIA",
        "person1_virus_11.jpeg"
    )

    result = predict_xray(test_image)

    print()
    print("===== X-RAY PREDICTION =====")
    print("Prediction:", result["prediction"])
    print("Confidence:", f"{result['confidence'] * 100:.2f}%")
    print("Pneumonia probability:",
          f"{result['pneumonia_probability'] * 100:.2f}%")
