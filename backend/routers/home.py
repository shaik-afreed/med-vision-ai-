from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {"message": "Welcome to MediVision AI"}


@router.get("/about")
def about():
    return {"message": "AI Smart Healthcare Platform"}


@router.get("/contact")
def contact():
    return {"email": "support@medivision.ai"}
