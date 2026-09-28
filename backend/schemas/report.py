from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: int
    patient_id: int
    report_name: str
    report_type: str
    file_path: str

    class Config:
        from_attributes = True
