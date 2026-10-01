import json
import secrets
from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==============================
    # APP
    # ==============================
    APP_NAME: str = "MediVision AI"
    ENVIRONMENT: str = "development"

    # ==============================
    # DATABASE
    # ==============================
    DATABASE_URL: str = "sqlite:///./medivision.db"
    # Apply Alembic migrations when the server starts. Off by default (local
    # dev runs `alembic upgrade head` by hand). Turn on for hosts where you
    # can't add that step to the start command, e.g. AUTO_MIGRATE=true.
    AUTO_MIGRATE: bool = False

    # ==============================
    # AUTH
    # ==============================
    # Signs login tokens. In development a random key is generated if unset
    # (tokens then don't survive a restart). With ENVIRONMENT=production the
    # app refuses to start without one - see require_secret_key_in_production.
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ==============================
    # CORS
    # ==============================
    # Frontend addresses allowed to call this API. From an env var, accepts
    # either a JSON list or a comma-separated list, e.g.
    #   CORS_ORIGINS=https://my-app.vercel.app,http://localhost:5173
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "https://med-vision-ai-indol.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # ==============================
    # UPLOADS
    # ==============================
    UPLOAD_DIR: str = "uploads/xrays"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/jpg", "image/png"]

    DOCUMENT_UPLOAD_DIR: str = "uploads/documents"
    ALLOWED_DOCUMENT_TYPES: list[str] = ["application/pdf", "text/plain"]

    # ==============================
    # AI MODEL
    # ==============================
    MODEL_VERSION: str = "mobilenetv2-finetuned-v1"

    # ==============================
    # CHATBOT
    # ==============================
    # Declared here so they can be set from .env (extra="ignore" drops any
    # .env variable that isn't declared as a field).
    #
    # NVIDIA-hosted LLM (preferred when a key is set). SecretStr keeps the
    # key masked in reprs/logs; it is only ever read in services/chatbot.py.
    NVIDIA_API_KEY: SecretStr | None = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "openai/gpt-oss-20b"

    # Local open-source LLM via Ollama - optional fallback on the same machine.
    LOCAL_LLM_URL: str = "http://127.0.0.1:11434"
    LOCAL_LLM_MODEL: str = "qwen2.5:7b"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            text = value.strip()
            value = json.loads(text) if text.startswith("[") else text.split(",")
        # Browsers send the Origin header without a trailing slash, so a
        # pasted "https://my-app.vercel.app/" would otherwise never match.
        return [origin.strip().rstrip("/") for origin in value if origin.strip()]

    @model_validator(mode="after")
    def require_secret_key_in_production(self):
        if not self.SECRET_KEY:
            if self.ENVIRONMENT.lower() == "production":
                raise ValueError(
                    "SECRET_KEY must be set when ENVIRONMENT=production. Generate "
                    "one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            self.SECRET_KEY = secrets.token_urlsafe(32)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
