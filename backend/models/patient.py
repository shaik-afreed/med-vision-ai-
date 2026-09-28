from sqlalchemy import Column, Integer, String

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
