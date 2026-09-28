import os
import numpy as np
import tensorflow as tf
from PIL import Image


# ============================================================
# MEDIVISION AI - PREDICTION SERVICE
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODEL_PATH = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "ai_model",
        "saved_models",
        "fine_tuned_model.h5"
    )
)

IMAGE_SIZE = (224, 224)

# Final validated operating threshold
THRESHOLD = 0.66


# ============================================================
# LOAD MODEL ONCE
# ============================================================

print("Loading MediVision AI model...")
print("Model path:", MODEL_PATH)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

model = tf.keras.models.load_model(
    MODEL_PATH
)

print("MediVision AI model loaded successfully.")


# ============================================================
# PREDICT X-RAY
# ============================================================

def predict_disease(file_path: str):

    # --------------------------------------------------------
    # CHECK FILE
    # --------------------------------------------------------

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"X-ray file not found: {file_path}"
        )

    # --------------------------------------------------------
    # LOAD IMAGE
    # --------------------------------------------------------

    image = Image.open(file_path)

    image = image.convert("RGB")

    image = image.resize(
        IMAGE_SIZE
    )

    # --------------------------------------------------------
    # CONVERT TO NUMPY
    # --------------------------------------------------------

    image_array = np.array(
        image
    ).astype(
        np.float32
    )

  

    # --------------------------------------------------------
    # ADD BATCH DIMENSION
    # --------------------------------------------------------

    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    # --------------------------------------------------------
    # MODEL PREDICTION
    # --------------------------------------------------------

    probability = float(
        model.predict(
            image_array,
            verbose=0
        )[0][0]
    )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if probability >= THRESHOLD:

        disease = "Pneumonia"

        confidence = probability

    else:

        disease = "Normal"

        confidence = 1.0 - probability

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "disease": disease,
        "confidence": round(
            confidence * 100,
            2
        ),
        "pneumonia_probability": round(
            probability * 100,
            2
        ),
        "threshold": THRESHOLD
    }