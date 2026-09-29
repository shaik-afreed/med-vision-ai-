import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # ==============================
    # AUTH
    # ==============================
    # No default in production: if SECRET_KEY isn't set via .env/env var,
    # a random one is generated at startup. That's fine for a single dev
    # process, but it means tokens won't survive a restart and won't be
    # shared across workers - set SECRET_KEY explicitly outside local dev.
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ==============================
    # CORS
    # ==============================
    CORS_ORIGINS: list[str] = [
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
    # CHATBOT (local open-source LLM via Ollama - no external API, no key)
    # ==============================
    # Declared here so they can be overridden from .env (extra="ignore"
    # drops any .env variable that isn't declared as a field).
    LOCAL_LLM_URL: str = "http://127.0.0.1:11434"
    LOCAL_LLM_MODEL: str = "qwen2.5:7b"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
