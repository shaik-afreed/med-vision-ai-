import pytest

from services import chatbot, health_assistant


def _ask(client, headers, text, history=None):
    messages = (history or []) + [{"role": "user", "content": text}]
    return client.post("/chat/health", json={"messages": messages}, headers=headers)


def test_health_chat_requires_auth(client):
    response = client.post("/chat/health", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 401


def test_health_chat_rejects_a_malformed_conversation(client, auth_headers):
    bad = {"messages": [{"role": "assistant", "content": "hello"}]}
    assert client.post("/chat/health", json=bad, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("question", [
    "I have chest pain and my left arm hurts",
    "my father cannot breathe properly",
    "she has difficulty breathing and blue lips",
    "I think he is having a stroke, face drooping",
    "this is the worst headache of my life",
    "my baby has a fever, he is 2 months old",
    "heavy bleeding that won't stop",
    "my throat is swelling after eating peanuts",
    "he took an overdose of tablets",
])
def test_emergencies_always_get_the_fixed_urgent_answer(client, auth_headers, monkeypatch, question):
    # No model may be consulted for an emergency.
    def boom(*_a, **_k):
        raise AssertionError("a model was called for an emergency")

    monkeypatch.setattr(chatbot, "_call_nvidia", boom)
    monkeypatch.setattr(chatbot, "_call_local_llm", boom)

    body = _ask(client, auth_headers, question).json()
    assert body["source"] == "builtin"
    assert "emergency" in body["reply"].lower()


@pytest.mark.parametrize("question", [
    "I want to kill myself", "sometimes I think of suicide", "I don't want to live anymore",
])
def test_self_harm_gets_a_supportive_crisis_answer(client, auth_headers, question):
    reply = _ask(client, auth_headers, question).json()["reply"]
    assert "crisis line" in reply and "not have to go through this alone" in reply


@pytest.mark.parametrize("question, must_mention", [
    ("I have a headache since morning", "worst of your life"),
    ("fewer and cold since yesterday", "Antibiotics do not work on viruses"),
    ("my stomach hurts and I am vomiting", "dehydration"),
    ("I have back pain", "numbness"),
    ("I can't sleep at night", "crisis line"),
])
def test_builtin_answers_cover_everyday_complaints_with_warning_signs(client, auth_headers, question, must_mention):
    body = _ask(client, auth_headers, question).json()
    assert body["source"] == "builtin"
    assert must_mention in body["reply"]
    assert "doctor" in body["reply"].lower()


def test_builtin_answers_never_give_medicine_doses():
    import re

    for _keywords, answer in health_assistant.TOPICS:
        assert not re.search(r"\b\d+\s?(mg|ml|mcg|g)\b", answer.lower()), answer[:60]
        assert "every 4 hours" not in answer and "twice daily" not in answer


def test_two_topics_in_one_message_are_both_answered():
    reply = health_assistant.builtin_reply("I have a headache and fever")
    assert "worst of your life" in reply and "baby under 3 months" in reply


def test_unknown_topic_and_greeting_get_helpful_defaults(client, auth_headers):
    greeting = _ask(client, auth_headers, "hello").json()["reply"]
    assert "AI Doctor" in greeting
    unknown = _ask(client, auth_headers, "what is the capital of france").json()["reply"]
    assert "everyday health concerns" in unknown


def test_the_model_gets_the_doctor_prompt_and_history_but_nothing_about_patients(client, auth_headers, monkeypatch):
    calls = []

    def fake_llm(system_prompt, messages):
        calls.append((system_prompt, messages))
        return "**Model** answer"

    monkeypatch.setattr(chatbot, "_call_local_llm", fake_llm)
    history = [
        {"role": "user", "content": "I have a cough"},
        {"role": "assistant", "content": "How long?"},
    ]

    body = _ask(client, auth_headers, "three days, no fever", history).json()

    assert body["source"] == "local_llm"
    assert body["reply"] == "Model answer"  # markdown stripped
    system_prompt, messages = calls[0]
    assert "MediVision AI Doctor" in system_prompt
    assert "NEVER give doses" in system_prompt
    assert [m["content"] for m in messages] == ["I have a cough", "How long?", "three days, no fever"]
    assert "Patient age" not in system_prompt  # no patient/report data on this endpoint
