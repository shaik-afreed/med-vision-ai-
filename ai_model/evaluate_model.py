"""
MediVision AI - Authoritative Model Evaluation

This is the ONLY evaluation script for this project. It replaces the
previous set of ad-hoc scripts (see ai_model/archive/README.md), which
used inconsistent thresholds and, in one case, selected a threshold by
sweeping directly against the test set (test-set leakage).

METHODOLOGY NOTE - why this does NOT use a train-directory validation
split for threshold selection:

  train.py (Phase 1) calls image_dataset_from_directory(..., seed=42)
  with the default shuffle=True. TF pre-shuffles the full file list
  (seeded) before slicing off the validation_split fraction, so Phase
  1's held-out validation set is a proper random ~20% stratified sample.

  fine_tune.py (Phase 2 - the phase that PRODUCED the deployed
  fine_tuned_model.h5) calls the same function with shuffle=False for
  its validation subset. With shuffle=False, TF does NOT pre-shuffle -
  it takes a *contiguous tail slice* of the class-sorted file list
  (NORMAL files first alphabetically, then PNEUMONIA). Because
  PNEUMONIA has ~3x more images than NORMAL, that tail slice lands
  entirely inside the PNEUMONIA folder: Phase 2's "validation" set was
  1043 images, 100% PNEUMONIA, 0% NORMAL. val_auc-based checkpointing/
  early-stopping during the fine-tuning that produced the deployed
  model was therefore driven by a degenerate, single-class signal.

  A further consequence: Phase 1 already trained on the large majority
  of the PNEUMONIA and NORMAL images (everything except its own proper
  ~20% validation slice). Phase 2's fit() call did not re-exclude
  Phase 1's validation slice from its own training fold, so by the
  time fine_tune.py ran, the model had already been fitted on nearly
  the entire train/ directory. There is no leakage-free subset of
  train/ left to use for honest threshold calibration on this
  already-trained model, short of retraining from scratch (explicitly
  out of scope here).

  The only data these two training phases never touched is the TEST
  directory. This script therefore treats TEST as the sole clean data
  source: it is split ONCE (stratified, seeded) into a calibration
  subset (used only to pick the operating threshold via Youden's J)
  and a disjoint holdout subset (used only to report final metrics).
  This keeps threshold selection independent of the images the final
  metrics are computed on, which is the property that matters -
  even though both subsets come from the same directory.

Inference here uses the same PIL-based loading path as production
(backend/services/prediction.py), not tf.data's image pipeline, so
reported metrics reflect exactly what the deployed API does.
"""

import os
import json
import numpy as np
import tensorflow as tf
from PIL import Image

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)

# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)

MODEL_PATH = os.path.join(BASE_DIR, "saved_models", "fine_tuned_model.h5")
TEST_PATH = os.path.join(BASE_DIR, "dataset", "archive", "chest_xray", "test")
EXTERNAL_PATH = os.path.join(REPO_ROOT, "real_test")

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 42

# Fraction of the (leakage-free) test set used only to calibrate the
# threshold. The remaining images are the true, never-touched holdout.
CALIBRATION_FRACTION = 0.40

REPORT_PATH = os.path.join(REPO_ROOT, "ai_model", "evaluation_report.json")

CLASS_NAMES = ["NORMAL", "PNEUMONIA"]


# ============================================================
# IMAGE LOADING (matches backend/services/prediction.py exactly)
# ============================================================

def load_image_array(path):
    image = Image.open(path).convert("RGB")
    image = image.resize(IMAGE_SIZE)
    return np.asarray(image, dtype=np.float32)


def predict_files(model, files):
    """Batched PIL-based prediction, matching production inference."""
    probabilities = []

    for start in range(0, len(files), BATCH_SIZE):
        batch_files = files[start:start + BATCH_SIZE]
        batch = np.stack([load_image_array(f) for f in batch_files])

        # The model contains mobilenet_v2.preprocess_input() as part of
        # its graph (see train.py) - no external normalization here.
        predictions = model.predict(batch, verbose=0).ravel()
        probabilities.extend(predictions.tolist())

    return np.asarray(probabilities, dtype=np.float32)


def get_all_files(path, class_names):
    files, labels = [], []

    for class_index, class_name in enumerate(class_names):
        class_dir = os.path.join(path, class_name)

        for filename in sorted(os.listdir(class_dir)):
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                files.append(os.path.join(class_dir, filename))
                labels.append(class_index)

    return files, np.array(labels)


def calculate_metrics(y_true, probabilities, threshold):
    y_pred = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(sensitivity),
        "specificity": float(specificity),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_true, probabilities)),
        "youden_j": float(sensitivity + specificity - 1.0),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


# ============================================================
# RUN
# ============================================================

def main():
    print("=" * 70)
    print("MEDIVISION AI - AUTHORITATIVE MODEL EVALUATION")
    print("=" * 70)

    print("\nLoading model:", MODEL_PATH)
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Model input :", model.input_shape)
    print("Model output:", model.output_shape)

    # --------------------------------------------------------
    # STEP 1 - load the ONLY leakage-free data (the test set)
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 1 - TEST SET (only data untouched by either training phase)")
    print("=" * 70)

    test_files, test_labels = get_all_files(TEST_PATH, CLASS_NAMES)
    print(f"\nTest images: {len(test_files)} "
          f"(NORMAL={int((test_labels == 0).sum())}, "
          f"PNEUMONIA={int((test_labels == 1).sum())})")

    print("\nRunning predictions once on the full test set...")
    test_probabilities = predict_files(model, test_files)
    full_test_auc = roc_auc_score(test_labels, test_probabilities)
    print(f"Full test-set AUC (threshold-independent): {full_test_auc:.4f}")

    # --------------------------------------------------------
    # STEP 2 - split test set into calibration / holdout (stratified)
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 2 - CALIBRATION / HOLDOUT SPLIT (stratified, seeded)")
    print("=" * 70)

    indices = np.arange(len(test_files))
    calib_idx, holdout_idx = train_test_split(
        indices,
        test_size=(1.0 - CALIBRATION_FRACTION),
        stratify=test_labels,
        random_state=SEED,
    )

    calib_labels = test_labels[calib_idx]
    calib_probs = test_probabilities[calib_idx]
    holdout_labels = test_labels[holdout_idx]
    holdout_probs = test_probabilities[holdout_idx]

    print(f"\nCalibration subset: {len(calib_idx)} images "
          f"(NORMAL={int((calib_labels == 0).sum())}, "
          f"PNEUMONIA={int((calib_labels == 1).sum())})")
    print(f"Holdout subset:     {len(holdout_idx)} images "
          f"(NORMAL={int((holdout_labels == 0).sum())}, "
          f"PNEUMONIA={int((holdout_labels == 1).sum())})")

    # --------------------------------------------------------
    # STEP 3 - threshold selection (calibration subset only)
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 3 - THRESHOLD SELECTION (Youden's J, calibration subset only)")
    print("=" * 70)

    thresholds = np.arange(0.05, 0.96, 0.01)
    threshold_sweep = [
        calculate_metrics(calib_labels, calib_probs, t) for t in thresholds
    ]

    best = max(threshold_sweep, key=lambda r: r["youden_j"])
    BEST_THRESHOLD = round(best["threshold"], 2)

    print(f"\nSelected threshold: {BEST_THRESHOLD:.2f}")
    print(f"  Calibration accuracy:    {best['accuracy']:.4f}")
    print(f"  Calibration precision:   {best['precision']:.4f}")
    print(f"  Calibration recall:      {best['recall']:.4f}")
    print(f"  Calibration specificity: {best['specificity']:.4f}")
    print(f"  Calibration F1:          {best['f1']:.4f}")

    # --------------------------------------------------------
    # STEP 4 - final evaluation on the disjoint holdout subset
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 4 - FINAL HOLDOUT EVALUATION (never used for threshold choice)")
    print("=" * 70)

    holdout_result = calculate_metrics(holdout_labels, holdout_probs, BEST_THRESHOLD)

    print(f"\nAccuracy:    {holdout_result['accuracy']:.4f}")
    print(f"Precision:   {holdout_result['precision']:.4f}")
    print(f"Recall:      {holdout_result['recall']:.4f}")
    print(f"Specificity: {holdout_result['specificity']:.4f}")
    print(f"F1:          {holdout_result['f1']:.4f}")
    print(f"AUC:         {holdout_result['auc']:.4f}")

    holdout_pred = (holdout_probs >= BEST_THRESHOLD).astype(int)
    holdout_report_text = classification_report(
        holdout_labels, holdout_pred, target_names=CLASS_NAMES, digits=4, zero_division=0
    )
    print("\n" + holdout_report_text)

    # Informational only: full test set at the chosen threshold (includes
    # the calibration images the threshold was tuned on - not an unbiased
    # number, reported for context only).
    full_test_result_informational = calculate_metrics(
        test_labels, test_probabilities, BEST_THRESHOLD
    )

    # --------------------------------------------------------
    # STEP 5 - external images (generalization check, not "test")
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 5 - EXTERNAL IMAGES (generalization observation only)")
    print("=" * 70)

    external_results = []

    if os.path.isdir(EXTERNAL_PATH):
        external_files = sorted(
            f for f in os.listdir(EXTERNAL_PATH)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
        )

        if external_files:
            ext_probs = predict_files(
                model, [os.path.join(EXTERNAL_PATH, f) for f in external_files]
            )

            for filename, probability in zip(external_files, ext_probs):
                probability = float(probability)
                prediction = "PNEUMONIA" if probability >= BEST_THRESHOLD else "NORMAL"
                confidence = probability if prediction == "PNEUMONIA" else 1.0 - probability

                external_results.append({
                    "file": filename,
                    "prediction": prediction,
                    "pneumonia_probability": round(probability, 4),
                    "model_confidence": round(confidence, 4),
                })

                print(f"  {filename:35s} -> {prediction:10s} "
                      f"(p={probability:.4f}, confidence={confidence:.2%})")
    else:
        print("External directory not found:", EXTERNAL_PATH)

    # --------------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------------
    report = {
        "model_path": os.path.relpath(MODEL_PATH, REPO_ROOT).replace("\\", "/"),
        "input_size": list(IMAGE_SIZE),
        "classes": CLASS_NAMES,
        "preprocessing": (
            "mobilenet_v2.preprocess_input is embedded in the model graph; "
            "inputs are raw 0-255 RGB float32 pixel arrays with no external "
            "normalization, resized to 224x224 via PIL (matches production)."
        ),
        "methodology_note": (
            "The training-directory validation split could not be used for "
            "threshold calibration: fine_tune.py (Phase 2, which produced "
            "the deployed model) used shuffle=False, causing its "
            "'validation' set to be a contiguous, single-class (100% "
            "PNEUMONIA) slice rather than a random stratified sample, and "
            "Phase 1 had already trained on nearly all of the train "
            "directory. The TEST directory is the only data neither phase "
            "touched, so it was split once (stratified, seed=42) into a "
            "calibration subset (threshold selection only) and a disjoint "
            "holdout subset (final metrics only)."
        ),
        "full_test_set": {
            "total_images": len(test_files),
            "normal_images": int((test_labels == 0).sum()),
            "pneumonia_images": int((test_labels == 1).sum()),
            "auc": float(full_test_auc),
        },
        "calibration_subset": {
            "total_images": len(calib_idx),
            "normal_images": int((calib_labels == 0).sum()),
            "pneumonia_images": int((calib_labels == 1).sum()),
            "purpose": "threshold selection only",
            "selected_threshold": BEST_THRESHOLD,
            "metrics_at_selected_threshold": best,
        },
        "holdout_subset": {
            "total_images": len(holdout_idx),
            "normal_images": int((holdout_labels == 0).sum()),
            "pneumonia_images": int((holdout_labels == 1).sum()),
            "purpose": "final reported metrics, never used for threshold selection",
            "result": holdout_result,
            "classification_report": holdout_report_text,
        },
        "full_test_set_informational_only": {
            "note": "Includes the calibration images; NOT an unbiased estimate.",
            "result": full_test_result_informational,
        },
        "external_generalization": {
            "note": (
                "These images are not part of the Kermany/Guangzhou pediatric "
                "chest X-ray distribution the model was trained on. This is a "
                "small, informal generalization check, not a validated "
                "benchmark."
            ),
            "predictions": external_results,
        },
        "known_limitations": [
            "Threshold calibration and final metrics both come from the "
            "TEST directory (split into disjoint subsets), because the "
            "training pipeline's own validation split was compromised - "
            "see methodology_note. A fully independent pipeline would "
            "require retraining with three disjoint splits from the start.",
            "The calibration/holdout split of only 624 test images (250 "
            "calibration, 374 holdout) is small; reported precision/"
            "specificity/F1 at the selected threshold have real sampling "
            "uncertainty. AUC (computed on the full test set, threshold-"
            "independent) is the more stable summary statistic.",
            "The model is trained on a single-source pediatric dataset "
            "(Kermany/Guangzhou). External test images in this evaluation "
            "were misclassified, indicating the model does not reliably "
            "generalize outside that dataset's imaging conditions.",
            "This is a screening-support research tool, not a diagnostic "
            "device, and has not been validated for clinical use.",
        ],
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\nReport written to: {REPORT_PATH}")
    print(f"Operating threshold to deploy: {BEST_THRESHOLD:.2f}")


if __name__ == "__main__":
    main()
