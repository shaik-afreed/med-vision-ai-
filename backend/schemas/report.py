from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Assessment(BaseModel):
    category: str
    label: str
    advice: str
    historical_pneumonia_share: float | None = None
    historical_images: int | None = None
    evaluated_on: str | None = None
    # The score's own band, even when `category` overrides it (e.g. adult patient).
    score_category: str | None = None


class ReportResponse(BaseModel):
    id: int
    patient_id: int
    owner_id: int

    report_name: str
    report_type: str

    prediction: str | None = None
    confidence: float | None = None
    pneumonia_probability: float | None = None
    threshold_used: float | None = None
    model_version: str | None = None
    has_gradcam: bool = False
    assessment: Assessment | None = None
    ai_explanation: str | None = None

    status: str
    notes: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    total: int
    reports: list[ReportResponse]


class ReportUploadResponse(BaseModel):
    message: str
    report: ReportResponse


class ReportUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
