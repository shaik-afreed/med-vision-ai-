import json

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database.database import Base


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)

    # Extracted text and analysis results from services/document_analysis.py.
    # findings_json is a JSON-encoded list of {test, value, unit,
    # reference_range, reference_source, status} dicts - see the `findings`
    # property below, which is what schemas/document.py actually reads.
    raw_text = Column(Text, nullable=True)
    findings_json = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="completed")
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="documents")
    owner = relationship("User", back_populates="documents")

    @property
    def findings(self) -> list:
        if not self.findings_json:
            return []
        return json.loads(self.findings_json)
