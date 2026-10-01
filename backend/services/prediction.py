import logging
import os
import threading

import numpy as np
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

# Operating threshold selected by ai_model/evaluate_model.py via Youden's J
# on a calibration subset of the test set, disjoint from the holdout subset
# metrics are reported on. See ai_model/evaluation_report.json for the full
# methodology and numbers, and ai_model/archive/README.md for why the
# previous 0.66 value (from a test-set-leaked analysis) was replaced.
THRESHOLD = 0.82


# ============================================================
# LOAD MODEL LAZILY, ONCE
# ============================================================
#
# Importing TensorFlow and loading the model costs about a minute of CPU on
# a small host and ~350 MB of RAM, and most requests (sign-in, patients,
# reports, chat) never need it. Loading it at import time made every server
# start - including waking from sleep on a free tier - slow for everyone.
# It now loads on first use, or earlier via warm_up_in_background().

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def get_model():
    """The loaded Keras model. The first call loads it (thread-safe: other
    callers wait on the same load instead of starting a second one)."""
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                if not os.path.exists(MODEL_PATH):
                    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

                logger.info("Loading MediVision AI model from %s", MODEL_PATH)
                import tensorflow as tf

                _model = tf.keras.models.load_model(MODEL_PATH)
                logger.info("MediVision AI model loaded successfully.")

    return _model


def is_model_loaded() -> bool:
    return _model is not None


def warm_up_in_background() -> bool:
    """Starts loading the model on a background thread so the next analysis
    doesn't pay for it. Returns False if it is already loaded."""
    if _model is not None:
        return False

    threading.Thread(target=get_model, name="model-warmup", daemon=True).start()
    return True


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
        get_model().predict(
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

    # Round to 6 decimal places, not 2: rounding to 2dp here (before the
    # value is ever returned/stored) was collapsing any probability
    # >= 0.99995 to a misleading "100.0" before the frontend ever saw it.
    # 6dp preserves the model's real precision (float32 has ~7 significant
    # digits) while still trimming binary-float noise; display-level
    # rounding belongs in the frontend, not here.
    return {
        "disease": disease,
        "confidence": round(
            confidence * 100,
            6
        ),
        "pneumonia_probability": round(
            probability * 100,
            6
        ),
        "threshold": THRESHOLD
    }