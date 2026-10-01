import json
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


# ============================================================
# "DOES THIS LOOK LIKE THE TRAINING DATA?" CHECK
# ============================================================
#
# The model learned from children's chest X-rays only and is confidently wrong
# on other images (adult X-rays scored "pneumonia 99%"). ai_model/external/
# domain_check.py fitted a small logistic regression on the model's own pooled
# image features (children's training images vs NIH adult X-rays) and passed
# its pre-registered test (flagged 99.3% of held-out adults, 0.16% of children's
# test images). domain_probability() returns P(image is unlike the training
# data) from those saved numbers; None if the file is missing.

DOMAIN_CHECK_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "ai_model", "external", "domain_check.json")
)
DOMAIN_FLAG_AT = 0.5

_domain = None
_domain_loaded = False
_feature_model = None


def _load_domain_check():
    global _domain, _domain_loaded

    if not _domain_loaded:
        _domain_loaded = True
        try:
            with open(DOMAIN_CHECK_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("passes") and "model" in saved:
                m = saved["model"]
                _domain = {
                    "mean": np.asarray(m["mean"], dtype=np.float32),
                    "scale": np.asarray(m["scale"], dtype=np.float32),
                    "coef": np.asarray(m["coef"], dtype=np.float32),
                    "intercept": float(m["intercept"]),
                }
        except (OSError, ValueError, KeyError):
            logger.warning("Image-domain check unavailable (%s)", DOMAIN_CHECK_PATH)

    return _domain


def domain_probability(features) -> float | None:
    """P(this image is unlike the children's training X-rays), 0-1."""
    domain = _load_domain_check()
    if domain is None:
        return None

    z = (np.asarray(features, dtype=np.float32) - domain["mean"]) / domain["scale"]
    logit = float(z @ domain["coef"]) + domain["intercept"]
    return float(1.0 / (1.0 + np.exp(-logit)))


def _get_feature_model():
    """The same network, also returning the pooled features the check uses, so
    one forward pass yields both the prediction and the check."""
    global _feature_model

    if _feature_model is None:
        import tensorflow as tf

        model = get_model()
        _feature_model = tf.keras.Model(
            model.input,
            [model.output, model.get_layer("global_average_pooling2d").output],
        )

    return _feature_model


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

    domain_score = None

    if _load_domain_check() is not None:
        outputs, pooled = _get_feature_model().predict(image_array, verbose=0)
        probability = float(outputs[0][0])
        domain_score = domain_probability(pooled[0])
    else:
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
        "domain_score": None if domain_score is None else round(domain_score, 6),
        "threshold": THRESHOLD
    }