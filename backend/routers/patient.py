from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from models.patient import Patient
from models.user import User
from schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientListResponse,
    PatientMutationResponse,
)
from dependencies.auth import get_current_user

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


def _get_owned_patient(patient_id: int, current_user: User, db: Session) -> Patient:
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.owner_id == current_user.id,
    ).first()

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


# ==========================
# CREATE PATIENT
# ==========================
@router.post("/", response_model=PatientMutationResponse)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_patient = Patient(
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        phone=patient.phone,
        address=patient.address,
        disease=patient.disease,
        owner_id=current_user.id,
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return {
        "message": "Patient added successfully",
        "patient": PatientResponse.model_validate(new_patient)
    }

# ==========================
# GET ALL PATIENTS (current user only)
# ==========================


@router.get("/", response_model=PatientListResponse)
def get_all_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    patients = db.query(Patient).filter(
        Patient.owner_id == current_user.id
    ).all()

    return {
        "total": len(patients),
        "patients": patients
    }

# ==========================
# GET PATIENT BY ID
# ==========================


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return _get_owned_patient(patient_id, current_user, db)

# ==========================
# UPDATE PATIENT
# ==========================


@router.put("/{patient_id}", response_model=PatientMutationResponse)
def update_patient(
    patient_id: int,
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_patient = _get_owned_patient(patient_id, current_user, db)

    existing_patient.full_name = patient.full_name
    existing_patient.age = patient.age
    existing_patient.gender = patient.gender
    existing_patient.phone = patient.phone
    existing_patient.address = patient.address
    existing_patient.disease = patient.disease

    db.commit()
    db.refresh(existing_patient)

    return {
        "message": "Patient updated successfully",
        "patient": PatientResponse.model_validate(existing_patient)
    }

# ==========================
# DELETE PATIENT
# ==========================


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    patient = _get_owned_patient(patient_id, current_user, db)

    db.delete(patient)
    db.commit()

    return {
        "message": "Patient deleted successfully"
    }
