from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    report_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    report_type = Column(String, nullable=False)

    # ==============================
    # AI PREDICTION
    # ==============================

    prediction = Column(String, nullable=True)
    # Confidence in the reported prediction (i.e. "how sure the model is
    # about NORMAL vs PNEUMONIA either way"), 0-100.
    confidence = Column(Float, nullable=True)
    # Raw model output: probability the image is PNEUMONIA, 0-100.
    pneumonia_probability = Column(Float, nullable=True)
    # The operating threshold and model version in effect when this
    # report was generated, so historical reports stay interpretable even
    # after evaluate_model.py selects a different threshold later.
    threshold_used = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)

    # ==============================
    # WORKFLOW
    # ==============================

    status = Column(String, nullable=False, default="completed")
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="reports")
    owner = relationship("User", back_populates="reports")
