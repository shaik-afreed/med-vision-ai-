import json
import os
from functools import lru_cache

# Turns a raw pneumonia probability into a plain-language category plus a
# MEASURED reliability figure from ai_model/probability_bands.json (produced
# by ai_model/probability_bands.py on the 624-image test set). The labels are
# display wording, not a clinical grading system.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BANDS_PATH = os.path.join(REPO_ROOT, "ai_model", "probability_bands.json")

# The deployed model was trained only on chest X-rays of children aged 1-5
# (one pediatric hospital). On adult X-rays it is often confidently wrong, so
# above this age the score is not given a likelihood label at all.
TRAINING_AGE_MAX = 10

OUTSIDE_AGES = "outside_training_ages"
UNLIKE_TRAINING = "unlike_training_images"

# The image-domain check (services/prediction.py) flags an image when its
# P(unlike the training X-rays) is at or above this.
DOMAIN_FLAG_AT = 0.5

LABELS = {
    UNLIKE_TRAINING: "Unreliable - this image does not look like the children's X-rays the AI was trained on",
    OUTSIDE_AGES: "Unreliable for this patient's age - the AI was trained only on X-rays of young children",
    "very_high": "Very high likelihood of pneumonia",
    "high": "High likelihood of pneumonia",
    "inconclusive": "Inconclusive (borderline) - cannot be reliably called normal or pneumonia",
    "probably_normal": "Probably normal - pneumonia not excluded",
    "low": "Low likelihood of pneumonia",
    "very_low": "Very low likelihood of pneumonia",
}

ADVICE = {
    UNLIKE_TRAINING: (
        "The AI learned only from children's chest X-rays. This image looks different (for example an adult "
        "X-ray, another kind of image, or a very different scanner), and on such images it often gives "
        "confident but wrong scores, so this score should not be used. A qualified clinician must read the "
        "X-ray itself."
    ),
    OUTSIDE_AGES: (
        "This AI model learned from X-rays of children aged 1-5 and often gives confident but wrong "
        "scores on adult or older-child X-rays, so this score should not be used. A qualified "
        "clinician must read the X-ray itself."
    ),
    "very_high": "Recommend prompt review of the X-ray by a qualified clinician.",
    "high": "Recommend review of the X-ray by a qualified clinician.",
    "inconclusive": (
        "Scores in this range were wrong about as often as right on the test set. "
        "Do not treat this as reassuring: clinician review of the image is strongly advised."
    ),
    "probably_normal": "Pneumonia is not excluded. Correlate with symptoms and clinical findings.",
    "low": "A low score does not exclude pneumonia or other chest conditions.",
    "very_low": "A low score does not exclude pneumonia or other chest conditions.",
}


@lru_cache
def _load_bands() -> dict | None:
    if not os.path.exists(BANDS_PATH):
        return None
    with open(BANDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def assess(
    pneumonia_probability_percent: float | None,
    model_version: str | None,
    patient_age: int | None = None,
    domain_score: float | None = None,
) -> dict | None:
    """Returns {"category", "label", "advice", "historical_pneumonia_share",
    "historical_images", "evaluated_on", "score_category"} or None if no
    probability. The historical figures are included only when the saved
    table describes the same model version that produced this probability.
    For a patient older than TRAINING_AGE_MAX the category is
    "outside_training_ages"; if the image itself is flagged as unlike the
    training X-rays (domain_score >= DOMAIN_FLAG_AT) it is
    "unlike_training_images". score_category keeps the score's own band."""
    if pneumonia_probability_percent is None:
        return None

    data = _load_bands()
    bands = (data or {}).get("bands", [])

    for band in bands:
        if band["min_percent"] <= pneumonia_probability_percent < band["max_percent"] or (
            band["max_percent"] >= 100 and pneumonia_probability_percent >= band["min_percent"]
        ):
            if patient_age is not None and patient_age > TRAINING_AGE_MAX:
                return {
                    "category": OUTSIDE_AGES,
                    "label": LABELS[OUTSIDE_AGES],
                    "advice": ADVICE[OUTSIDE_AGES],
                    "historical_pneumonia_share": None,
                    "historical_images": None,
                    "evaluated_on": None,
                    "score_category": band["category"],
                }

            if domain_score is not None and domain_score >= DOMAIN_FLAG_AT:
                return {
                    "category": UNLIKE_TRAINING,
                    "label": LABELS[UNLIKE_TRAINING],
                    "advice": ADVICE[UNLIKE_TRAINING],
                    "historical_pneumonia_share": None,
                    "historical_images": None,
                    "evaluated_on": None,
                    "score_category": band["category"],
                }

            same_model = data.get("model_version") == model_version
            return {
                "category": band["category"],
                "label": LABELS[band["category"]],
                "advice": ADVICE[band["category"]],
                "historical_pneumonia_share": band["pneumonia_share"] if same_model else None,
                "historical_images": band["images"] if same_model else None,
                "evaluated_on": data["evaluated_on"] if same_model else None,
                "score_category": band["category"],
            }

    return None
