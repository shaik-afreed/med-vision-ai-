import json
import os

from fastapi import APIRouter

from core.config import settings

router = APIRouter(prefix="/model", tags=["AI Model"])

# backend/routers/model_info.py -> backend/routers -> backend -> repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVALUATION_REPORT_PATH = os.path.join(REPO_ROOT, "ai_model", "evaluation_report.json")


@router.get("/info")
def model_info():
    """
    Serves real numbers from ai_model/evaluation_report.json (produced by
    ai_model/evaluate_model.py), not hardcoded metrics. If the report
    hasn't been generated yet, says so explicitly rather than making
    numbers up.
    """

    if not os.path.exists(EVALUATION_REPORT_PATH):
        return {
            "evaluation_available": False,
            "model_version": settings.MODEL_VERSION,
        }

    with open(EVALUATION_REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    holdout = report["holdout_subset"]["result"]

    return {
        "evaluation_available": True,
        "model_version": settings.MODEL_VERSION,
        "threshold": holdout["threshold"],
        "auc": holdout["auc"],
        "accuracy": holdout["accuracy"],
        "precision": holdout["precision"],
        "recall": holdout["recall"],
        "specificity": holdout["specificity"],
        "f1": holdout["f1"],
        "evaluated_on_images": report["holdout_subset"]["total_images"],
        "known_limitations": report.get("known_limitations", []),
    }
