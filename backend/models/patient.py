from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    disease = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Every patient record belongs to the doctor/user who created it.
    # Authorization checks in routers/patient.py and routers/report.py
    # rely on this to enforce per-user isolation.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User", back_populates="patients")
    reports = relationship(
        "Report", back_populates="patient", cascade="all, delete-orphan"
    )
