import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from main import app
from core.config import settings


# ============================================================
# Isolated in-memory test database (never touches medivision.db)
# ============================================================

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    """Every test writes uploads to its own throwaway temp directory."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "DOCUMENT_UPLOAD_DIR", str(tmp_path / "documents"))


@pytest.fixture(autouse=True)
def reset_login_limiter():
    from utils import login_limiter

    login_limiter.clear_all()
    yield
    login_limiter.clear_all()


@pytest.fixture(autouse=True)
def local_llm_offline(monkeypatch):
    """Tests never depend on (or talk to) a real local Ollama server;
    chatbot tests that need the LLM path install a stub explicitly."""
    from services import chatbot

    def offline(*_args, **_kwargs):
        raise chatbot.LocalLLMUnavailable("disabled in tests")

    # backend/.env holds the developer's real NVIDIA key; tests must never
    # read it or make real (billable) calls. NVIDIA tests install a fake
    # key and a local fake server explicitly.
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", None)
    monkeypatch.setattr(chatbot, "_nvidia_down_until", 0.0)
    monkeypatch.setattr(chatbot, "_llm_down_until", 0.0)
    monkeypatch.setattr(chatbot, "_call_local_llm", offline)
    monkeypatch.setattr(
        chatbot, "local_llm_status", lambda: {"running": False, "model_ready": False}
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _unique_email():
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def register_and_login(client):
    """Returns a function that registers+logs in a fresh user and returns
    (auth_headers, email) so tests can create as many independent users
    as they need for ownership/isolation tests."""

    def _make_user(password="testpass123"):
        email = _unique_email()

        response = client.post(
            "/auth/register",
            json={"name": "Test Doctor", "email": email, "password": password},
        )
        assert response.status_code == 201, response.text

        response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, email

    return _make_user


@pytest.fixture
def auth_headers(register_and_login):
    headers, _ = register_and_login()
    return headers


def make_test_image_bytes(fmt="JPEG", size=(224, 224)):
    """A small, valid, in-memory image for upload tests. Content doesn't
    need to resemble a real X-ray - these tests exercise upload/storage/
    ownership plumbing, not model accuracy (that's ai_model/evaluate_model.py's
    job)."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(120, 120, 120)).save(buffer, format=fmt)
    buffer.seek(0)
    return buffer


def make_test_lab_report_text():
    """A small, realistic-shaped lab report for document-analysis tests:
    exercises the reference-range-in-report path (Hemoglobin, WBC) and the
    general-fallback path (Total Cholesterol has no range stated)."""
    return (
        "COMPLETE BLOOD COUNT REPORT\n"
        "Patient: Jane Roe   Age: 52   Sex: F\n"
        "\n"
        "Hemoglobin: 10.8 g/dL (12.0-15.5)\n"
        "WBC Count: 13.2 x10^9/L (4.0-11.0)\n"
        "Total Cholesterol 185 mg/dL\n"
    ).encode("utf-8")
