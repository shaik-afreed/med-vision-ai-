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

    # Grad-CAM heatmap image path (server-side only, never returned to the
    # client directly - served via GET /reports/{id}/gradcam instead, same
    # pattern as file_path/GET /reports/{id}/image) and the plain-language,
    # rule-based explanation generated alongside it. Both are nullable:
    # heatmap generation is a best-effort explainability feature and must
    # never block saving the underlying prediction if it fails.
    gradcam_path = Column(String, nullable=True)
    ai_explanation = Column(String, nullable=True)

    # ==============================
    # WORKFLOW
    # ==============================

    status = Column(String, nullable=False, default="completed")
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="reports")
    owner = relationship("User", back_populates="reports")

    @property
    def has_gradcam(self) -> bool:
        return bool(self.gradcam_path)

    @property
    def assessment(self):
        from services.assessment import assess

        age = self.patient.age if self.patient is not None else None
        return assess(self.pneumonia_probability, self.model_version, age)
