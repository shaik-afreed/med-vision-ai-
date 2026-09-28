from datetime import datetime
from pydantic import BaseModel


# ==========================
# Create / Update Patient Schema
# ==========================
class PatientCreate(BaseModel):
    full_name: str
    age: int
    gender: str
    phone: str
    address: str
    disease: str | None = None


class PatientUpdate(BaseModel):
    full_name: str
    age: int
    gender: str
    phone: str
    address: str
    disease: str | None = None


# ==========================
# Response Schema
# ==========================
class PatientResponse(BaseModel):
    id: int
    full_name: str
    age: int
    gender: str
    phone: str
    address: str
    disease: str | None = None
    created_at: datetime | None = None
    owner_id: int

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    total: int
    patients: list[PatientResponse]


class PatientMutationResponse(BaseModel):
    message: str
    patient: PatientResponse
