from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from utils.jwt_handler import verify_access_token
from database.database import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid or expired token"
    )

    payload = verify_access_token(token)

    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.query(User).filter(User.email == payload["sub"]).first()

    if user is None:
        raise credentials_error

    return user
