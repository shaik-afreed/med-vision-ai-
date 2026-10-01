from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from database.database import get_db
from dependencies.auth import get_current_user
from models.report import Report
from models.user import User
from schemas.chat import ChatRequest, ChatResponse, ChatStatusResponse
from services import chatbot


router = APIRouter(
    prefix="/chat",
    tags=["Chatbot"]
)


@router.get("/status", response_model=ChatStatusResponse)
def chat_status(current_user: User = Depends(get_current_user)):
    # No network call for the hosted model: it is "available" if a key is
    # configured; a failure on an actual question falls back automatically.
    if chatbot.nvidia_configured():
        return {"llm_available": True, "provider": "nvidia", "model": settings.NVIDIA_MODEL}

    if chatbot.local_llm_status()["model_ready"]:
        return {"llm_available": True, "provider": "local_llm", "model": settings.LOCAL_LLM_MODEL}

    return {"llm_available": False, "provider": "none", "model": None}


# Plain `def` (not async): FastAPI runs it in a worker thread, so the
# blocking call to the local LLM doesn't stall other requests.
@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    report_context = None

    if payload.report_id is not None:
        report = db.query(Report).filter(
            Report.id == payload.report_id,
            Report.owner_id == current_user.id,
        ).first()

        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        # Only the fields the assistant needs - never the patient's name,
        # phone, or address.
        report_context = {
            "prediction": report.prediction,
            "pneumonia_probability": report.pneumonia_probability,
            "confidence": report.confidence,
            "threshold": report.threshold_used,
            "model_version": report.model_version,
            "ai_explanation": report.ai_explanation,
            "patient_age": report.patient.age,
            "patient_gender": report.patient.gender,
        }

    messages = [message.model_dump() for message in payload.messages]

    return chatbot.ask(messages, report_context)
