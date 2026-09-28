from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from models.patient import Patient
from schemas.patient import PatientCreate
from dependencies.auth import get_current_user

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


# ==========================
# CREATE PATIENT
# ==========================
@router.post("/")
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    new_patient = Patient(
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        phone=patient.phone,
        address=patient.address,
        disease=patient.disease
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return {
        "message": "Patient added successfully",
        "patient": new_patient
    }

# ==========================
# GET ALL PATIENTS
# ==========================


@router.get("/")
def get_all_patients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    patients = db.query(Patient).all()

    return {
        "total": len(patients),
        "patients": patients
    }
# ==========================
# GET PATIENT BY ID
# ==========================


@router.get("/{patient_id}")
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient

# ==========================
# UPDATE PATIENT
# ==========================


@router.put("/{patient_id}")
def update_patient(
    patient_id: int,
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    existing_patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if existing_patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

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
        "patient": existing_patient
    }

# ==========================
# DELETE PATIENT
# ==========================


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    db.delete(patient)
    db.commit()

    return {
        "message": "Patient deleted successfully"
    }
