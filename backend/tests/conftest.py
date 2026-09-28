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
