from utils.jwt_handler import create_access_token, verify_access_token
from utils.security import hash_password, verify_password
from database.database import get_db
from models.user import User
from schemas.user import UserRegister, UserLogin
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# ==========================
# REGISTER API
# ==========================


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }


# ==========================
# LOGIN API
# ==========================
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    print("Username entered:", form_data.username)
    print("Password entered:", form_data.password)
    print("User found:", existing_user)

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        form_data.password,
        existing_user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": existing_user.email
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ==========================
# PROFILE API (Protected)
# ==========================


@router.get("/profile")
def profile(token: str = Depends(oauth2_scheme)):

    print("TOKEN RECEIVED =", token)

    payload = verify_access_token(token)

    print("PAYLOAD =", payload)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    return {
        "message": "Profile accessed successfully",
        "user": payload["sub"]
    }
