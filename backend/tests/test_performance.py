import os
import subprocess
import sys

from passlib.context import CryptContext

from services import prediction
from utils.security import hash_password, verify_password

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_server_startup_does_not_import_heavy_libraries():
    """Sign-in and every other non-AI request must not pay for TensorFlow,
    alembic, or the PDF libraries: on a fractional-CPU host those imports
    made every cold start and every login slow."""
    code = (
        "import sys, main; "
        "heavy = [m for m in ('tensorflow', 'alembic', 'fpdf', 'pypdf') if m in sys.modules]; "
        "print('HEAVY:' + ','.join(heavy))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )

    assert result.returncode == 0, result.stderr[-500:]
    assert "HEAVY:" in result.stdout
    assert result.stdout.strip().splitlines()[-1] == "HEAVY:", result.stdout[-300:]


def test_password_hashing_uses_cost_10_and_still_verifies_older_hashes():
    hashed = hash_password("a-test-password-123")
    assert hashed.startswith("$2b$10$")
    assert verify_password("a-test-password-123", hashed)
    assert not verify_password("wrong-password", hashed)

    # Hashes created earlier at the old default cost (12) must keep working.
    old_hash = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12).hash("legacy-password-1")
    assert old_hash.startswith("$2b$12$")
    assert verify_password("legacy-password-1", old_hash)


def test_model_warmup_requires_login(client):
    assert client.post("/model/warmup").status_code == 401


def test_model_warmup_starts_loading_without_blocking(client, auth_headers, monkeypatch):
    calls = []
    monkeypatch.setattr(prediction, "warm_up_in_background", lambda: calls.append(1) or True)
    monkeypatch.setattr(prediction, "is_model_loaded", lambda: False)

    response = client.post("/model/warmup", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"loaded": False, "started": True}
    assert calls == [1]


def test_get_model_loads_once_and_is_reused(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(prediction, "_model", sentinel)

    assert prediction.get_model() is sentinel
    assert prediction.is_model_loaded() is True
    assert prediction.warm_up_in_background() is False


def test_xray_analysis_does_not_block_other_requests(client, auth_headers, monkeypatch):
    """predict_disease is blocking TensorFlow work. It used to run directly
    inside the async upload endpoint and froze the whole server (even
    /health) until it finished; it must run in a worker thread."""
    import threading
    import time

    from routers import report as report_router
    from tests.conftest import make_test_image_bytes

    started = threading.Event()
    release = threading.Event()

    def slow_predict(_path):
        started.set()
        assert release.wait(timeout=30)
        return {"disease": "Normal", "confidence": 90.0, "pneumonia_probability": 10.0, "threshold": 0.82}

    monkeypatch.setattr(report_router, "predict_disease", slow_predict)
    monkeypatch.setattr(report_router, "generate_gradcam", lambda *a, **k: "explanation")

    patient_id = client.post(
        "/patients/",
        json={"full_name": "Slow Case", "age": 4, "gender": "Male", "phone": "1", "address": "x", "disease": None},
        headers=auth_headers,
    ).json()["patient"]["id"]

    outcome = {}

    def upload():
        files = {"file": ("x.jpg", make_test_image_bytes(), "image/jpeg")}
        outcome["response"] = client.post(
            "/reports/upload",
            data={"patient_id": str(patient_id), "report_type": "X-Ray"},
            files=files,
            headers=auth_headers,
        )

    worker = threading.Thread(target=upload)
    worker.start()
    try:
        assert started.wait(timeout=30), "analysis never started"

        began = time.monotonic()
        health = client.get("/health")
        waited = time.monotonic() - began

        assert health.status_code == 200
        assert waited < 5, f"/health waited {waited:.1f}s behind a running analysis"
    finally:
        release.set()
        worker.join(timeout=60)

    assert outcome["response"].status_code == 200
