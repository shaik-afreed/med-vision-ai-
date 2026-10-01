import json
import os
from functools import lru_cache

# Turns a raw pneumonia probability into a plain-language category plus a
# MEASURED reliability figure from ai_model/probability_bands.json (produced
# by ai_model/probability_bands.py on the 624-image test set). The labels are
# display wording, not a clinical grading system.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BANDS_PATH = os.path.join(REPO_ROOT, "ai_model", "probability_bands.json")

LABELS = {
    "very_high": "Very high likelihood of pneumonia",
    "high": "High likelihood of pneumonia",
    "inconclusive": "Inconclusive (borderline) - cannot be reliably called normal or pneumonia",
    "probably_normal": "Probably normal - pneumonia not excluded",
    "low": "Low likelihood of pneumonia",
    "very_low": "Very low likelihood of pneumonia",
}

ADVICE = {
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


def assess(pneumonia_probability_percent: float | None, model_version: str | None) -> dict | None:
    """Returns {"category", "label", "advice", "historical_pneumonia_share",
    "historical_images", "evaluated_on"} or None if no probability.
    The historical figures are included only when the saved table describes
    the same model version that produced this probability."""
    if pneumonia_probability_percent is None:
        return None

    data = _load_bands()
    bands = (data or {}).get("bands", [])

    for band in bands:
        if band["min_percent"] <= pneumonia_probability_percent < band["max_percent"] or (
            band["max_percent"] >= 100 and pneumonia_probability_percent >= band["min_percent"]
        ):
            same_model = data.get("model_version") == model_version
            return {
                "category": band["category"],
                "label": LABELS[band["category"]],
                "advice": ADVICE[band["category"]],
                "historical_pneumonia_share": band["pneumonia_share"] if same_model else None,
                "historical_images": band["images"] if same_model else None,
                "evaluated_on": data["evaluated_on"] if same_model else None,
            }

    return None
