import json
import logging
import os
import uuid

from fastapi.concurrency import run_in_threadpool
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.database import get_db
from models.document import MedicalDocument
from models.patient import Patient
from schemas.document import (
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentResponse,
    DocumentUpdate,
)
from services.document_analysis import analyze_document
from dependencies.auth import get_current_user
from models.user import User
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Medical Documents"]
)

EXTENSION_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
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


def _get_owned_document(document_id: int, current_user: User, db: Session) -> MedicalDocument:
    document = db.query(MedicalDocument).filter(
        MedicalDocument.id == document_id,
        MedicalDocument.owner_id == current_user.id,
    ).first()

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


async def _read_and_validate_upload(file: UploadFile) -> bytes:

    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and plain text (.txt) medical reports are allowed."
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit."
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if file.content_type == "application/pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF."
        )

    if file.content_type == "text/plain":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="The uploaded text file could not be read as UTF-8 text."
            )

    return content


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    _get_owned_patient(patient_id, current_user, db)

    content = await _read_and_validate_upload(file)

    extension = EXTENSION_BY_CONTENT_TYPE[file.content_type]
    safe_filename = f"{uuid.uuid4().hex}{extension}"

    upload_folder = settings.DOCUMENT_UPLOAD_DIR
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # ==============================
        # TEXT EXTRACTION + LAB VALUE ANALYSIS
        # ==============================

        # PDF text extraction is blocking work; keep it off the event loop.
        analysis = await run_in_threadpool(analyze_document, file_path, file.content_type)

        # ==============================
        # SAVE DOCUMENT + ANALYSIS
        # ==============================

        display_name = os.path.basename(file.filename or safe_filename)

        document = MedicalDocument(
            patient_id=patient_id,
            owner_id=current_user.id,
            file_name=display_name,
            file_path=file_path,
            content_type=file.content_type,
            raw_text=analysis["raw_text"],
            findings_json=json.dumps(analysis["findings"]),
            summary=analysis["summary"],
            status="completed",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return {
            "message": "Document uploaded and analyzed",
            "document": document,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:

        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        # Full traceback goes to the server log only; the client gets a
        # generic message so internal paths/details aren't exposed.
        logger.exception("Medical document processing failed")
        raise HTTPException(
            status_code=500,
            detail="Document processing failed due to a server error. Please try again."
        )

    finally:

        await file.close()


@router.get("/", response_model=DocumentListResponse)
def get_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    documents = db.query(MedicalDocument).filter(
        MedicalDocument.owner_id == current_user.id
    ).order_by(
        MedicalDocument.id.desc()
    ).all()

    return {
        "total": len(documents),
        "documents": documents,
    }


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    document = _get_owned_document(document_id, current_user, db)

    if payload.status is not None:
        document.status = payload.status

    if payload.notes is not None:
        document.notes = payload.notes

    db.commit()
    db.refresh(document)

    return document


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    document = _get_owned_document(document_id, current_user, db)

    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=404,
            detail="Document file not found"
        )

    return FileResponse(
        document.file_path,
        media_type=document.content_type,
        filename=document.file_name
    )
