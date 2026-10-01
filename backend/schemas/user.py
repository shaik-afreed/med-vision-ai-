from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    # Matches the frontend's register-mode minLength (Login.jsx); enforced
    # here too since the frontend constraint is trivially bypassable via
    # direct API calls.
    password: str = Field(min_length=8)

    # EmailStr only lowercases the domain; "Sam@x.com" and "sam@x.com" must
    # be one account, and sign-in must not depend on how the address was
    # capitalized (phone keyboards often capitalize the first letter).
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
