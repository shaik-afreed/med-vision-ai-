"""
Prepare patient-grouped splits and cached image arrays for retraining.

Why this exists (see ai_model/evaluation_report.json "methodology_note"):
V1's validation data was compromised, so its threshold had to be calibrated
on part of the TEST set. Here the training directory is split BY PATIENT
into train / validation / calibration, so:
  - validation  -> early stopping and checkpoint choice
  - calibration -> choosing the decision threshold (Youden's J)
  - test        -> the untouched Kermany test directory, used only for the
                   final comparison against V1.

Images are resized with PIL's default resize, exactly like production
(backend/services/prediction.py). V1 was trained with TensorFlow's bilinear
resize but is served with PIL's, a small train/serve mismatch this removes.
"""
import json
import os
import re

import numpy as np
from PIL import Image
from sklearn.model_selection import StratifiedGroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(os.path.dirname(HERE), "dataset", "archive", "chest_xray")
CACHE = os.path.join(HERE, "cache")
SPLITS_JSON = os.path.join(HERE, "splits.json")

IMAGE_SIZE = (224, 224)
SEED = 42
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

_PNEUMONIA = re.compile(r"^person(\d+)_(bacteria|virus)_(\d+)", re.I)
_NORMAL = re.compile(r"^(NORMAL2-IM|IM)-(\d+)", re.I)


def patient_key(class_name: str, filename: str) -> str:
    """Identifies the patient. The numeric ID alone is NOT unique: the
    bacteria/virus and IM/NORMAL2-IM series are numbered independently,
    so the series name is part of the key."""
    if class_name == "NORMAL":
        match = _NORMAL.match(filename)
        return f"N-{match.group(1).upper()}-{match.group(2)}"
    match = _PNEUMONIA.match(filename)
    return f"P-{match.group(2).lower()}-{match.group(1)}"


def list_split_dir(split: str):
    files, labels, groups = [], [], []
    for label, class_name in enumerate(CLASS_NAMES):
        class_dir = os.path.join(DATASET, split, class_name)
        for filename in sorted(os.listdir(class_dir)):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                files.append(os.path.join(split, class_name, filename))
                labels.append(label)
                groups.append(patient_key(class_name, filename) if split == "train" else filename)
    return files, np.array(labels), np.array(groups)


def load_array(relative_path: str) -> np.ndarray:
    image = Image.open(os.path.join(DATASET, relative_path)).convert("RGB")
    image = image.resize(IMAGE_SIZE)
    return np.asarray(image, dtype=np.uint8)


def cache_split(name: str, files, labels):
    x = np.stack([load_array(f) for f in files])
    np.save(os.path.join(CACHE, f"{name}_x.npy"), x)
    np.save(os.path.join(CACHE, f"{name}_y.npy"), labels.astype(np.int8))
    print(f"  cached {name}: {x.shape} (NORMAL={int((labels == 0).sum())}, PNEUMONIA={int((labels == 1).sum())})")


def main():
    os.makedirs(CACHE, exist_ok=True)

    files, labels, groups = list_split_dir("train")
    print(f"train directory: {len(files)} images, {len(set(groups))} patients")

    # 10 patient-grouped, class-stratified folds: fold 0 -> calibration (10%),
    # fold 1 -> validation (10%), folds 2-9 -> training (80%).
    folds = StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=SEED)
    assignment = np.zeros(len(files), dtype=int)
    for fold_index, (_, held_out) in enumerate(folds.split(files, labels, groups)):
        assignment[held_out] = fold_index

    split_of = np.where(assignment == 0, "calibration", np.where(assignment == 1, "validation", "train"))

    # Hard guarantee: no patient appears in more than one split.
    patient_splits = {}
    for group, split in zip(groups, split_of):
        patient_splits.setdefault(group, set()).add(split)
    leaked = [g for g, s in patient_splits.items() if len(s) > 1]
    assert not leaked, f"patient(s) split across sets: {leaked[:5]}"
    print("patient leakage check: PASSED (0 patients in more than one split)")

    manifest = {"seed": SEED, "image_size": list(IMAGE_SIZE), "splits": {}}

    for name in ("train", "validation", "calibration"):
        mask = split_of == name
        manifest["splits"][name] = [f for f, keep in zip(files, mask) if keep]
        cache_split(name, [f for f, keep in zip(files, mask) if keep], labels[mask])

    test_files, test_labels, _ = list_split_dir("test")
    manifest["splits"]["test"] = test_files
    cache_split("test", test_files, test_labels)

    with open(SPLITS_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print("wrote", SPLITS_JSON)


if __name__ == "__main__":
    main()
