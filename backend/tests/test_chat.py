import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pydantic import SecretStr

from core.config import settings
from services import chatbot
from tests.conftest import make_test_image_bytes

# Captured at import, before the autouse `local_llm_offline` fixture
# replaces them, so the HTTP client code itself can be tested.
REAL_CALL_LOCAL_LLM = chatbot._call_local_llm
REAL_LOCAL_LLM_STATUS = chatbot.local_llm_status

FAKE_KEY = "nvapi-test-fake-key-for-unit-tests"

PATIENT_PAYLOAD = {
    "full_name": "Distinctive Patientname",
    "age": 45,
    "gender": "Male",
    "phone": "5550001111",
    "address": "742 Evergreen Terrace",
    "disease": None,
}


def _upload_report(client, headers):
    patient_id = client.post(
        "/patients/", json=PATIENT_PAYLOAD, headers=headers
    ).json()["patient"]["id"]
    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    return client.post(
        "/reports/upload", data=data, files=files, headers=headers
    ).json()["report"]


def _question(text="What does this result mean?", report_id=None):
    return {"report_id": report_id, "messages": [{"role": "user", "content": text}]}


# ------------------------------------------------------------
# API behaviour
# ------------------------------------------------------------

def test_chat_requires_auth(client):
    assert client.post("/chat", json=_question()).status_code == 401
    assert client.get("/chat/status").status_code == 401


def test_status_reports_no_llm_when_nothing_is_available(client, auth_headers):
    response = client.get("/chat/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"llm_available": False, "provider": "none", "model": None}


def test_status_reports_nvidia_when_key_is_configured(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", SecretStr(FAKE_KEY))
    response = client.get("/chat/status", headers=auth_headers)
    assert response.json() == {
        "llm_available": True,
        "provider": "nvidia",
        "model": settings.NVIDIA_MODEL,
    }
    assert FAKE_KEY not in response.text


def test_chat_rejects_malformed_conversation(client, auth_headers):
    bad_order = {
        "messages": [
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "hello"},
        ]
    }
    assert client.post("/chat", json=bad_order, headers=auth_headers).status_code == 422

    ends_with_assistant = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
    }
    assert client.post(
        "/chat", json=ends_with_assistant, headers=auth_headers
    ).status_code == 422

    too_long = _question("x" * 4001)
    assert client.post("/chat", json=too_long, headers=auth_headers).status_code == 422


def test_chat_about_another_users_report_is_404(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    report = _upload_report(client, headers_a)

    response = client.post(
        "/chat", json=_question(report_id=report["id"]), headers=headers_b
    )
    assert response.status_code == 404


# ------------------------------------------------------------
# Built-in answers (local LLM offline)
# ------------------------------------------------------------

def test_builtin_answer_uses_real_result_data(client, auth_headers):
    report = _upload_report(client, auth_headers)

    response = client.post(
        "/chat", json=_question(report_id=report["id"]), headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "builtin"
    assert f"{report['pneumonia_probability']:.2f}%" in body["reply"]


def test_builtin_result_question_without_report_asks_to_analyze(client, auth_headers):
    response = client.post("/chat", json=_question(), headers=auth_headers)
    assert "No X-ray has been analyzed" in response.json()["reply"]


def test_builtin_topics():
    ctx = {
        "prediction": "Pneumonia",
        "pneumonia_probability": 91.5,
        "confidence": 91.5,
        "threshold": 0.82,
        "model_version": "v1",
        "ai_explanation": "Attention concentrated in the lower-right region.",
        "patient_age": 40,
        "patient_gender": "Male",
    }
    facts = chatbot.load_model_facts()

    assert "lower-right" in chatbot.builtin_answer("What does the heatmap show?", ctx, facts)
    assert "82%" in chatbot.builtin_answer("What is the threshold?", ctx, facts)
    assert "cannot detect" in chatbot.builtin_answer("What can this tool not detect?", ctx, facts)
    assert "doctor" in chatbot.builtin_answer("What should happen next?", ctx, facts)
    assert "infection" in chatbot.builtin_answer("What is pneumonia?", None, facts)
    assert "MobileNetV2" in chatbot.builtin_answer("How does this X-ray screening work?", None, facts)


def test_emergency_question_always_gets_urgent_care_answer(client, auth_headers, monkeypatch):
    called = []
    monkeypatch.setattr(chatbot, "_call_local_llm", lambda *a: called.append(a) or "LLM text")

    response = client.post(
        "/chat", json=_question("My child has chest pain and can't breathe"), headers=auth_headers
    )

    body = response.json()
    assert body["source"] == "builtin"
    assert "urgent medical care" in body["reply"]
    assert called == []


# ------------------------------------------------------------
# Local LLM path
# ------------------------------------------------------------

def test_local_llm_gets_result_context_but_no_patient_identifiers(client, auth_headers, monkeypatch):
    report = _upload_report(client, auth_headers)
    calls = []

    def fake_llm(system_prompt, messages):
        calls.append((system_prompt, messages))
        return "Local model answer."

    monkeypatch.setattr(chatbot, "_call_local_llm", fake_llm)

    response = client.post(
        "/chat", json=_question(report_id=report["id"]), headers=auth_headers
    )

    body = response.json()
    assert body == {
        "reply": "Local model answer.",
        "source": "local_llm",
        "model": settings.LOCAL_LLM_MODEL,
    }

    system_prompt, messages = calls[0]
    assert messages == [{"role": "user", "content": "What does this result mean?"}]
    assert f"Prediction: {report['prediction']}" in system_prompt
    assert "Patient age: 45" in system_prompt
    assert "Distinctive Patientname" not in system_prompt
    assert "5550001111" not in system_prompt
    assert "Evergreen" not in system_prompt


def test_local_llm_receives_only_recent_history_starting_with_user(client, auth_headers, monkeypatch):
    calls = []
    monkeypatch.setattr(chatbot, "_call_local_llm", lambda s, m: calls.append(m) or "ok")

    history = []
    for i in range(5):
        history += [{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"a{i}"}]
    history.append({"role": "user", "content": "latest"})

    client.post("/chat", json={"messages": history}, headers=auth_headers)

    sent = calls[0]
    assert sent[0]["role"] == "user"
    assert sent[-1]["content"] == "latest"
    assert len(sent) <= chatbot.LLM_HISTORY_MESSAGES


def test_unreachable_llm_is_skipped_until_retry_window_passes(client, auth_headers, monkeypatch):
    attempts = []

    def failing_llm(*_args):
        attempts.append(1)
        raise chatbot.LocalLLMUnavailable("connection refused")

    monkeypatch.setattr(chatbot, "_call_local_llm", failing_llm)

    for _ in range(3):
        response = client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)
        assert response.json()["source"] == "builtin"

    assert len(attempts) == 1

    monkeypatch.setattr(chatbot, "_llm_down_until", 0.0)
    client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)
    assert len(attempts) == 2


# ------------------------------------------------------------
# HTTP client against a fake Ollama server
# ------------------------------------------------------------

class FakeOllama(BaseHTTPRequestHandler):
    known_models = ["llama3.2:3b"]
    received = []

    def log_message(self, *_args):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send(200, {"models": [{"name": n} for n in self.known_models]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.received.append(body)
        if body["model"] not in self.known_models:
            self._send(404, {"error": f"model '{body['model']}' not found"})
            return
        self._send(200, {"message": {"role": "assistant", "content": "Hello from the fake model."}, "done": True})


@pytest.fixture
def fake_ollama(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FakeOllama.received = []
    monkeypatch.setattr(settings, "LOCAL_LLM_URL", f"http://127.0.0.1:{server.server_port}")
    yield FakeOllama
    server.shutdown()
    server.server_close()


def test_http_client_talks_to_ollama_chat_api(fake_ollama, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "llama3.2:3b")

    reply = REAL_CALL_LOCAL_LLM("SYSTEM RULES", [{"role": "user", "content": "hi"}])

    assert reply == "Hello from the fake model."
    sent = fake_ollama.received[0]
    assert sent["stream"] is False
    assert sent["messages"][0] == {"role": "system", "content": "SYSTEM RULES"}
    assert sent["messages"][1] == {"role": "user", "content": "hi"}
    assert REAL_LOCAL_LLM_STATUS() == {"running": True, "model_ready": True}


def test_http_client_reports_missing_model_with_pull_hint(fake_ollama, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "not-downloaded:1b")

    with pytest.raises(chatbot.LocalLLMUnavailable, match="ollama pull not-downloaded:1b"):
        REAL_CALL_LOCAL_LLM("rules", [{"role": "user", "content": "hi"}])

    assert REAL_LOCAL_LLM_STATUS() == {"running": True, "model_ready": False}


# ------------------------------------------------------------
# NVIDIA-hosted model path (against a fake OpenAI-compatible server)
# ------------------------------------------------------------

class FakeNvidia(BaseHTTPRequestHandler):
    mode = "ok"
    received = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        FakeNvidia.received.append({
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "body": json.loads(self.rfile.read(length)),
        })

        def send(code, body):
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        if FakeNvidia.mode == "http_error":
            send(404, {"detail": "Function not found for account"})
        elif FakeNvidia.mode == "empty_content":
            send(200, {"choices": [{"finish_reason": "length", "message": {"content": None, "reasoning_content": "thinking..."}}]})
        elif FakeNvidia.mode == "truncated":
            send(200, {"choices": [{"finish_reason": "length", "message": {"content": "Partial answer"}}]})
        else:
            send(200, {"choices": [{"finish_reason": "stop", "message": {"content": "Hello from the fake NVIDIA model."}}]})


@pytest.fixture
def fake_nvidia(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeNvidia)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeNvidia.mode = "ok"
    FakeNvidia.received = []
    monkeypatch.setattr(settings, "NVIDIA_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", SecretStr(FAKE_KEY))
    yield FakeNvidia
    server.shutdown()
    server.server_close()


def test_nvidia_answer_is_used_and_key_goes_only_in_auth_header(client, auth_headers, fake_nvidia):
    report = _upload_report(client, auth_headers)

    response = client.post("/chat", json=_question(report_id=report["id"]), headers=auth_headers)

    assert response.json() == {
        "reply": "Hello from the fake NVIDIA model.",
        "source": "nvidia",
        "model": settings.NVIDIA_MODEL,
    }
    assert FAKE_KEY not in response.text

    sent = fake_nvidia.received[0]
    assert sent["path"] == "/v1/chat/completions"
    assert sent["auth"] == f"Bearer {FAKE_KEY}"
    assert sent["body"]["model"] == settings.NVIDIA_MODEL
    assert sent["body"]["messages"][0]["role"] == "system"
    assert sent["body"]["messages"][-1] == {"role": "user", "content": "What does this result mean?"}

    prompt = sent["body"]["messages"][0]["content"]
    assert f"Prediction: {report['prediction']}" in prompt
    assert "Distinctive Patientname" not in prompt
    assert "5550001111" not in prompt
    assert FAKE_KEY not in prompt


def test_nvidia_http_error_falls_back_to_builtin_without_leaking_anything(client, auth_headers, fake_nvidia):
    fake_nvidia.mode = "http_error"

    response = client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "builtin"
    assert FAKE_KEY not in response.text
    assert "Function not found" not in response.text


def test_nvidia_answer_that_is_only_thinking_falls_back(client, auth_headers, fake_nvidia):
    fake_nvidia.mode = "empty_content"

    response = client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)

    assert response.json()["source"] == "builtin"


def test_nvidia_truncated_answer_is_flagged(client, auth_headers, fake_nvidia):
    fake_nvidia.mode = "truncated"

    reply = client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers).json()["reply"]

    assert reply.startswith("Partial answer")
    assert "cut short" in reply


def test_nvidia_failure_is_skipped_until_retry_window_passes(client, auth_headers, fake_nvidia, monkeypatch):
    fake_nvidia.mode = "http_error"

    for _ in range(3):
        client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)

    assert len(fake_nvidia.received) == 1

    monkeypatch.setattr(chatbot, "_nvidia_down_until", 0.0)
    fake_nvidia.mode = "ok"
    response = client.post("/chat", json=_question("What is pneumonia?"), headers=auth_headers)
    assert response.json()["source"] == "nvidia"


def test_emergency_question_never_goes_to_nvidia(client, auth_headers, fake_nvidia):
    response = client.post(
        "/chat", json=_question("My child has chest pain and can't breathe"), headers=auth_headers
    )

    assert response.json()["source"] == "builtin"
    assert "urgent medical care" in response.json()["reply"]
    assert fake_nvidia.received == []


def test_plain_text_strips_markdown_and_odd_spaces():
    raw = "## Summary\n\nThis is **very** important.\n\n* first point\n* second point\n\nUse `care`.\n\n\n\nEnd‑to‑end."
    cleaned = chatbot.plain_text(raw)

    assert "**" not in cleaned and "#" not in cleaned and "`" not in cleaned
    assert "very important" in cleaned
    assert "- first point" in cleaned and "- second point" in cleaned
    assert "End-to-end." in cleaned
    assert "\n\n\n" not in cleaned
