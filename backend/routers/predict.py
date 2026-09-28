from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

from services.prediction import predict_disease


router = APIRouter(
    prefix="/predict",
    tags=["AI Prediction"]
)


# ==============================
# UPLOAD DIRECTORY
# ==============================

UPLOAD_DIR = "uploads/xrays"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==============================
# X-RAY PREDICTION API
# ==============================

@router.post("/")
async def predict(
    file: UploadFile = File(...)
):

    # --------------------------
    # CHECK FILE TYPE
    # --------------------------

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

    # --------------------------
    # SAVE UPLOADED FILE
    # --------------------------

    file_path = os.path.join(
        UPLOAD_DIR,
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

        # ----------------------
        # AI PREDICTION
        # ----------------------

        result = predict_disease(
            file_path
        )

        # ----------------------
        # RESPONSE
        # ----------------------

        return {
            "message": "X-ray prediction successful",
            "filename": file.filename,
            "prediction": result
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

    finally:

        file.file.close()
