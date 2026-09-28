import os
import uuid

from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
import io

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from database.database import get_db
from models.report import Report
from models.patient import Patient
from schemas.report import (
    ReportListResponse,
    ReportUploadResponse,
    ReportResponse,
    ReportUpdate,
)
from services.prediction import predict_disease
from dependencies.auth import get_current_user
from models.user import User
from core.config import settings


router = APIRouter(
    prefix="/reports",
    tags=["Medical Reports"]
)

# Map validated MIME type -> safe extension. The stored filename is never
# derived from the client-supplied filename, which closes off path
# traversal and extension-spoofing on the upload path entirely.
EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _get_owned_patient(patient_id: int, current_user: User, db: Session) -> Patient:
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.owner_id == current_user.id,
    ).first()

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


def _get_owned_report(report_id: int, current_user: User, db: Session) -> Report:
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.owner_id == current_user.id,
    ).first()

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


async def _read_and_validate_upload(file: UploadFile) -> bytes:

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG and PNG X-ray images are allowed."
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit."
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Trust the actual image bytes, not the client-supplied Content-Type
    # header: open and verify the file is a real, undamaged image.
    try:
        Image.open(io.BytesIO(content)).verify()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image."
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image could not be read; it may be corrupted."
        )

    return content


@router.post("/upload", response_model=ReportUploadResponse)
async def upload_report(
    patient_id: int = Form(...),
    report_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Uploading a report for a patient you don't own is not allowed.
    _get_owned_patient(patient_id, current_user, db)

    content = await _read_and_validate_upload(file)

    extension = EXTENSION_BY_CONTENT_TYPE[file.content_type]
    safe_filename = f"{uuid.uuid4().hex}{extension}"

    upload_folder = settings.UPLOAD_DIR
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # ==============================
        # AI PREDICTION
        # ==============================

        result = predict_disease(file_path)

        # ==============================
        # SAVE REPORT + AI RESULT
        # ==============================

        display_name = os.path.basename(file.filename or safe_filename)

        report = Report(
            patient_id=patient_id,
            owner_id=current_user.id,
            report_name=display_name,
            report_type=report_type,
            file_path=file_path,
            prediction=result["disease"],
            confidence=result["confidence"],
            pneumonia_probability=result["pneumonia_probability"],
            threshold_used=result["threshold"],
            model_version=settings.MODEL_VERSION,
            status="completed",
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return {
            "message": "Report uploaded and AI analysis completed",
            "report": report,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail=f"Report processing failed: {str(e)}"
        )

    finally:

        await file.close()


# ==============================
# GET ALL REPORTS (current user only)
# ==============================

@router.get("/", response_model=ReportListResponse)
def get_all_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    reports = db.query(Report).filter(
        Report.owner_id == current_user.id
    ).order_by(
        Report.id.desc()
    ).all()

    return {
        "total": len(reports),
        "reports": reports,
    }


# ==============================
# UPDATE REPORT (notes / status)
# ==============================

@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    report = _get_owned_report(report_id, current_user, db)

    if payload.status is not None:
        report.status = payload.status

    if payload.notes is not None:
        report.notes = payload.notes

    db.commit()
    db.refresh(report)

    return report


# ==============================
# GET REPORT IMAGE
# ==============================

@router.get("/{report_id}/image")
def get_report_image(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    report = _get_owned_report(report_id, current_user, db)

    if not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=404,
            detail="Report image file not found"
        )

    return FileResponse(
        report.file_path,
        media_type="image/jpeg",
        filename=report.report_name
    )
