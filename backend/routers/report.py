import os
import shutil

from fastapi.responses import FileResponse


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
from services.prediction import predict_disease
from dependencies.auth import get_current_user


router = APIRouter(
    prefix="/reports",
    tags=["Medical Reports"]
)


@router.post("/upload")
def upload_report(
    patient_id: int = Form(...),
    report_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # ==============================
    # CHECK FILE TYPE
    # ==============================

    allowed_types = [
        "image/jpeg",
        "image/jpg",
        "image/png"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG and PNG X-ray images are allowed."
        )

    # ==============================
    # UPLOAD FOLDER
    # ==============================

    upload_folder = "uploads/reports"

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # ==============================
    # SAVE FILE
    # ==============================

    file_path = os.path.join(
        upload_folder,
        file.filename
    )

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        # ==============================
        # AI PREDICTION
        # ==============================

        result = predict_disease(
            file_path
        )

        # ==============================
        # SAVE REPORT + AI RESULT
        # ==============================

        report = Report(
            patient_id=patient_id,
            report_name=file.filename,
            report_type=report_type,
            file_path=file_path,
            prediction=result["disease"],
            confidence=result["confidence"]
        )

        db.add(report)

        db.commit()

        db.refresh(report)

        # ==============================
        # RESPONSE
        # ==============================

        return {
            "message": "Report uploaded and AI analysis completed",

            "report": {
                "id": report.id,
                "patient_id": report.patient_id,
                "report_name": report.report_name,
                "report_type": report.report_type,
                "prediction": report.prediction,
                "confidence": report.confidence
            }
        }

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Report processing failed: {str(e)}"
        )

    finally:

        file.file.close()

# ==============================
# GET ALL REPORTS
# ==============================


@router.get("/")
def get_all_reports(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    reports = db.query(Report).order_by(
        Report.id.desc()
    ).all()

    return {
        "total": len(reports),
        "reports": [
            {
                "id": report.id,
                "patient_id": report.patient_id,
                "report_name": report.report_name,
                "report_type": report.report_type,
                "prediction": report.prediction,
                "confidence": report.confidence
            }
            for report in reports
        ]
    }

# ==============================
# GET REPORT IMAGE
# ==============================


@router.get("/{report_id}/image")
def get_report_image(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    report = db.query(Report).filter(
        Report.id == report_id
    ).first()

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

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
