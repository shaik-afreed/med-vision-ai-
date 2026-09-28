from pydantic import BaseModel


# ==========================
# Create Patient Schema
# ==========================
class PatientCreate(BaseModel):
    full_name: str
    age: int
    gender: str
    phone: str
    address: str
    disease: str  | None = None


# ==========================
# Update Patient Schema
# ==========================
class PatientUpdate(BaseModel):
    full_name: str
    age: int
    gender: str
    phone: str
    address: str
    disease: str   | None = None


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
    disease: str  | None = None

    class Config:
        from_attributes = True
