from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id")
    )

    report_name = Column(
        String,
        nullable=False
    )

    file_path = Column(
        String,
        nullable=False
    )

    report_type = Column(
        String,
        nullable=False
    )

    # ==============================
    # AI PREDICTION
    # ==============================

    prediction = Column(
        String,
        nullable=True
    )

    confidence = Column(
        Float,
        nullable=True
    )
