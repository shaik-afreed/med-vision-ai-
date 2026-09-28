import os
import json
import numpy as np
import tensorflow as tf
from PIL import Image

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)

# ============================================================
# MEDIVISION AI - FINAL EVALUATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ai_model",
    "saved_models",
    "fine_tuned_model.h5"
)

TRAIN_PATH = os.path.join(
    BASE_DIR,
    "ai_model",
    "dataset",
    "archive",
    "chest_xray",
    "train"
)

TEST_PATH = os.path.join(
    BASE_DIR,
    "ai_model",
    "dataset",
    "archive",
    "chest_xray",
    "test"
)

EXTERNAL_PATH = os.path.join(
    BASE_DIR,
    "real_test"
)

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 42

# Threshold candidates
THRESHOLDS = np.arange(
    0.10,
    0.91,
    0.01
)

# ============================================================
# IMPORTANT PREPROCESSING
# ============================================================
#
# The saved model contains:
#
#     mobilenet_v2.preprocess_input()
#
# Therefore images MUST enter the model as normal
# 0-255 RGB pixel values.
#
# DO NOT call preprocess_input() outside the model.
#
# ============================================================


def load_image(path):

    image = Image.open(path).convert("RGB")
    image = image.resize(IMAGE_SIZE)

    array = np.asarray(
        image,
        dtype=np.float32
    )

    return np.expand_dims(
        array,
        axis=0
    )


def predict_probability(model, path):

    image = load_image(path)

    probability = model.predict(
        image,
        verbose=0
    )[0][0]

    return float(probability)


# ============================================================
# GET FILES
# ============================================================

def get_class_files(base_path):

    normal_dir = os.path.join(
        base_path,
        "NORMAL"
    )

    pneumonia_dir = os.path.join(
        base_path,
        "PNEUMONIA"
    )

    normal_files = sorted([
        os.path.join(normal_dir, f)
        for f in os.listdir(normal_dir)
        if f.lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp")
        )
    ])

    pneumonia_files = sorted([
        os.path.join(pneumonia_dir, f)
        for f in os.listdir(pneumonia_dir)
        if f.lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp")
        )
    ])

    return normal_files, pneumonia_files


# ============================================================
# PREDICT FILE LIST
# ============================================================

def predict_files(model, files):

    probabilities = []

    for start in range(
        0,
        len(files),
        BATCH_SIZE
    ):

        batch_files = files[
            start:start + BATCH_SIZE
        ]

        images = []

        for path in batch_files:

            image = Image.open(
                path
            ).convert("RGB")

            image = image.resize(
                IMAGE_SIZE
            )

            array = np.asarray(
                image,
                dtype=np.float32
            )

            images.append(array)

        batch = np.asarray(
            images,
            dtype=np.float32
        )

        # IMPORTANT:
        # No external MobileNet preprocessing.

        predictions = model.predict(
            batch,
            verbose=0
        ).ravel()

        probabilities.extend(
            predictions.tolist()
        )

    return np.asarray(
        probabilities,
        dtype=np.float32
    )


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    y_true,
    probabilities,
    threshold
):

    y_pred = (
        probabilities >= threshold
    ).astype(int)

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1]
    )

    tn, fp, fn, tp = cm.ravel()

    specificity = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else 0.0
    )

    sensitivity = (
        tp / (tp + fn)
        if (tp + fn) > 0
        else 0.0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )

    return {
        "threshold": float(threshold),
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred
            )
        ),
        "precision": float(
            precision_score(
                y_true,
                y_pred,
                zero_division=0
            )
        ),
        "recall": float(sensitivity),
        "specificity": float(specificity),
        "f1": float(f1),
        "auc": float(
            roc_auc_score(
                y_true,
                probabilities
            )
        ),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp)
    }


# ============================================================
# START
# ============================================================

print()
print("=" * 65)
print("          MEDIVISION AI - FINAL EVALUATION")
print("=" * 65)

print()
print("Loading model...")

model = tf.keras.models.load_model(
    MODEL_PATH
)

print("Model loaded successfully.")

print()
print("Model input :", model.input_shape)
print("Model output:", model.output_shape)

# ============================================================
# VERIFY MODEL
# ============================================================

print()
print("=" * 65)
print("STEP 1 - MODEL VERIFICATION")
print("=" * 65)

print()
print("Model:", MODEL_PATH)

print(
    "Final activation:",
    model.layers[-1].activation
)

print(
    "Input size:",
    model.input_shape
)

# ============================================================
# STRATIFIED VALIDATION SET
# ============================================================

print()
print("=" * 65)
print("STEP 2 - STRATIFIED VALIDATION")
print("=" * 65)

normal_files, pneumonia_files = get_class_files(
    TRAIN_PATH
)

print()
print("Training NORMAL images:", len(normal_files))
print("Training PNEUMONIA images:", len(pneumonia_files))

rng = np.random.default_rng(SEED)

normal_indices = np.arange(
    len(normal_files)
)

pneumonia_indices = np.arange(
    len(pneumonia_files)
)

rng.shuffle(normal_indices)
rng.shuffle(pneumonia_indices)

# 20% validation from EACH class

normal_val_count = int(
    len(normal_files) * 0.20
)

pneumonia_val_count = int(
    len(pneumonia_files) * 0.20
)

normal_val_files = [
    normal_files[i]
    for i in normal_indices[
        :normal_val_count
    ]
]

pneumonia_val_files = [
    pneumonia_files[i]
    for i in pneumonia_indices[
        :pneumonia_val_count
    ]
]

validation_files = (
    normal_val_files
    +
    pneumonia_val_files
)

validation_labels = np.array(
    [0] * len(normal_val_files)
    +
    [1] * len(pneumonia_val_files)
)

print()
print(
    "Validation NORMAL:",
    len(normal_val_files)
)

print(
    "Validation PNEUMONIA:",
    len(pneumonia_val_files)
)

print(
    "Validation TOTAL:",
    len(validation_files)
)

# ============================================================
# VALIDATION PREDICTIONS
# ============================================================

print()
print("Running validation predictions...")

validation_probabilities = predict_files(
    model,
    validation_files
)

print(
    "Validation predictions completed."
)

print()
print(
    "Validation AUC:",
    f"{roc_auc_score(validation_labels, validation_probabilities):.4f}"
)

# ============================================================
# THRESHOLD SELECTION
# ============================================================

print()
print("=" * 65)
print("STEP 3 - THRESHOLD SELECTION")
print("=" * 65)

threshold_results = []

for threshold in THRESHOLDS:

    result = calculate_metrics(
        validation_labels,
        validation_probabilities,
        threshold
    )

    # Youden's J
    result["youden_j"] = (
        result["recall"]
        +
        result["specificity"]
        -
        1.0
    )

    threshold_results.append(
        result
    )

# Select threshold with maximum Youden J

best_threshold_result = max(
    threshold_results,
    key=lambda x: x["youden_j"]
)

BEST_THRESHOLD = (
    best_threshold_result["threshold"]
)

print()

print(
    "BEST THRESHOLD:",
    f"{BEST_THRESHOLD:.2f}"
)

print(
    "Validation Accuracy:",
    f"{best_threshold_result['accuracy']:.4f}"
)

print(
    "Validation Precision:",
    f"{best_threshold_result['precision']:.4f}"
)

print(
    "Validation Recall:",
    f"{best_threshold_result['recall']:.4f}"
)

print(
    "Validation Specificity:",
    f"{best_threshold_result['specificity']:.4f}"
)

print(
    "Validation F1:",
    f"{best_threshold_result['f1']:.4f}"
)

# ============================================================
# FINAL INDEPENDENT TEST
# ============================================================

print()
print("=" * 65)
print("STEP 4 - INDEPENDENT TEST SET")
print("=" * 65)

test_normal_files, test_pneumonia_files = (
    get_class_files(TEST_PATH)
)

test_files = (
    test_normal_files
    +
    test_pneumonia_files
)

test_labels = np.array(
    [0] * len(test_normal_files)
    +
    [1] * len(test_pneumonia_files)
)

print()
print(
    "TEST NORMAL:",
    len(test_normal_files)
)

print(
    "TEST PNEUMONIA:",
    len(test_pneumonia_files)
)

print(
    "TEST TOTAL:",
    len(test_files)
)

print()
print("Running test predictions ONCE...")

test_probabilities = predict_files(
    model,
    test_files
)

print(
    "Test predictions completed."
)

test_result = calculate_metrics(
    test_labels,
    test_probabilities,
    BEST_THRESHOLD
)

# ============================================================
# FINAL RESULTS
# ============================================================

print()
print("=" * 65)
print("              FINAL TEST RESULTS")
print("=" * 65)

print()
print(
    "Threshold:   ",
    f"{BEST_THRESHOLD:.2f}"
)

print(
    "Accuracy:    ",
    f"{test_result['accuracy']:.4f}"
)

print(
    "Precision:   ",
    f"{test_result['precision']:.4f}"
)

print(
    "Recall:      ",
    f"{test_result['recall']:.4f}"
)

print(
    "Specificity: ",
    f"{test_result['specificity']:.4f}"
)

print(
    "F1 Score:    ",
    f"{test_result['f1']:.4f}"
)

print(
    "AUC:         ",
    f"{test_result['auc']:.4f}"
)

print()
print("Confusion Matrix:")
print(
    np.array([
        [
            test_result["tn"],
            test_result["fp"]
        ],
        [
            test_result["fn"],
            test_result["tp"]
        ]
    ])
)

print()
print("Classification Report:")

test_predictions = (
    test_probabilities >= BEST_THRESHOLD
).astype(int)

print(
    classification_report(
        test_labels,
        test_predictions,
        target_names=[
            "NORMAL",
            "PNEUMONIA"
        ],
        digits=4,
        zero_division=0
    )
)

# ============================================================
# EXTERNAL X-RAYS
# ============================================================

print()
print("=" * 65)
print("STEP 5 - EXTERNAL X-RAYS")
print("=" * 65)

external_results = []

if os.path.isdir(EXTERNAL_PATH):

    external_files = sorted([
        f
        for f in os.listdir(EXTERNAL_PATH)
        if f.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp"
            )
        )
    ])

    print()
    print(
        "External images:",
        len(external_files)
    )

    for filename in external_files:

        path = os.path.join(
            EXTERNAL_PATH,
            filename
        )

        probability = predict_probability(
            model,
            path
        )

        prediction = (
            "PNEUMONIA"
            if probability >= BEST_THRESHOLD
            else "NORMAL"
        )

        confidence = (
            probability
            if prediction == "PNEUMONIA"
            else 1.0 - probability
        )

        result = {
            "file": filename,
            "prediction": prediction,
            "pneumonia_probability": probability,
            "model_confidence": confidence
        }

        external_results.append(
            result
        )

        print()
        print(
            "File:",
            filename
        )

        print(
            "Prediction:",
            prediction
        )

        print(
            "Pneumonia probability:",
            f"{probability:.4f}"
        )

        print(
            "Model confidence:",
            f"{confidence:.4f}"
        )

else:

    print(
        "External directory not found:",
        EXTERNAL_PATH
    )

# ============================================================
# SAVE REPORT
# ============================================================

report = {

    "model": MODEL_PATH,

    "input_size": IMAGE_SIZE,

    "classes": [
        "NORMAL",
        "PNEUMONIA"
    ],

    "preprocessing": (
        "Model-internal MobileNetV2 preprocessing; "
        "no external preprocessing"
    ),

    "validation": {
        "normal_images": len(normal_val_files),
        "pneumonia_images": len(pneumonia_val_files),
        "total_images": len(validation_labels),
        "threshold_results": threshold_results,
        "selected_threshold": BEST_THRESHOLD
    },

    "final_test": test_result,

    "test_images": len(test_labels),

    "external_predictions": external_results
}

REPORT_PATH = os.path.join(
    BASE_DIR,
    "FINAL_EVALUATION_REPORT.json"
)

with open(
    REPORT_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        report,
        file,
        indent=4
    )

# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 65)
print("           FINAL EVALUATION COMPLETED")
print("=" * 65)

print()
print(
    "Report:",
    REPORT_PATH
)

print()
print("FINAL SUMMARY")
print("-" * 40)

print(
    "Threshold:",
    f"{BEST_THRESHOLD:.2f}"
)

print(
    "Accuracy:",
    f"{test_result['accuracy']:.4f}"
)

print(
    "Precision:",
    f"{test_result['precision']:.4f}"
)

print(
    "Recall:",
    f"{test_result['recall']:.4f}"
)

print(
    "Specificity:",
    f"{test_result['specificity']:.4f}"
)

print(
    "F1:",
    f"{test_result['f1']:.4f}"
)

print(
    "AUC:",
    f"{test_result['auc']:.4f}"
)

print()
print("No additional evaluation is required.")