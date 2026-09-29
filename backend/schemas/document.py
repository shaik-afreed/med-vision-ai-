from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentFinding(BaseModel):
    test: str
    value: float
    unit: str | None = None
    reference_range: str | None = None
    reference_source: str
    status: str


class DocumentResponse(BaseModel):
    id: int
    patient_id: int
    owner_id: int

    file_name: str
    content_type: str

    summary: str | None = None
    findings: list[DocumentFinding] = []
    raw_text: str | None = None

    status: str
    notes: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse


class DocumentUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
