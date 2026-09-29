import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

from core.config import settings


# ============================================================
# MEDIVISION AI - X-RAY RESULTS CHATBOT (local, no external API)
# ============================================================
#
# Two answer engines, both running entirely on this machine:
#   1. A local open-source LLM served by Ollama (settings.LOCAL_LLM_URL /
#      LOCAL_LLM_MODEL). Free-form questions, grounded in the result data.
#   2. Built-in answers (no model): used whenever the local LLM isn't
#      running or its model isn't downloaded. Rule-based, answers only from
#      the real result data and evaluation report - never invents facts.

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVALUATION_REPORT_PATH = os.path.join(REPO_ROOT, "ai_model", "evaluation_report.json")

LLM_TIMEOUT_SECONDS = 180
STATUS_TIMEOUT_SECONDS = 1.5
# Small local models have small context windows; sending only the recent
# turns keeps the system prompt (safety rules + result data) from being
# truncated away.
LLM_HISTORY_MESSAGES = 6

# On Windows a refused localhost connection takes ~2s to fail, so after the
# local LLM is found unreachable, skip it for a while instead of paying that
# delay on every question. A successful status check clears this at once.
LLM_RETRY_AFTER_SECONDS = 30
_llm_down_until = 0.0

# Talk to localhost directly - never route local-LLM traffic through a
# system-configured HTTP proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class LocalLLMUnavailable(Exception):
    pass


# ------------------------------------------------------------
# Model facts (real numbers from ai_model/evaluation_report.json)
# ------------------------------------------------------------

def load_model_facts() -> dict | None:
    if not os.path.exists(EVALUATION_REPORT_PATH):
        return None

    with open(EVALUATION_REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    holdout = report["holdout_subset"]["result"]
    return {
        "images": report["holdout_subset"]["total_images"],
        "auc": holdout["auc"],
        "accuracy": holdout["accuracy"],
        "recall": holdout["recall"],
        "specificity": holdout["specificity"],
        "precision": holdout["precision"],
        "threshold": holdout["threshold"],
        "limitations": report.get("known_limitations", []),
    }


def _metrics_sentence(facts: dict | None) -> str:
    if facts is None:
        return "Evaluation metrics for this model are not available."
    return (
        f"On {facts['images']} held-out test images it scored AUC {facts['auc']:.3f}, "
        f"accuracy {facts['accuracy']:.1%}, sensitivity {facts['recall']:.1%} "
        f"(pneumonia cases caught) and specificity {facts['specificity']:.1%} "
        f"(normal cases correctly cleared)."
    )


# ------------------------------------------------------------
# Local LLM (Ollama HTTP API)
# ------------------------------------------------------------

def _ollama_url(path: str) -> str:
    return f"{settings.LOCAL_LLM_URL.rstrip('/')}{path}"


def _mark_llm_down() -> None:
    global _llm_down_until
    _llm_down_until = time.monotonic() + LLM_RETRY_AFTER_SECONDS


def _llm_recently_down() -> bool:
    return time.monotonic() < _llm_down_until


def local_llm_status() -> dict:
    """{"running": bool, "model_ready": bool} - never raises."""
    global _llm_down_until
    try:
        with _opener.open(_ollama_url("/api/tags"), timeout=STATUS_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        _mark_llm_down()
        return {"running": False, "model_ready": False}

    wanted = settings.LOCAL_LLM_MODEL
    names = {model.get("name", "") for model in body.get("models", [])}
    ready = wanted in names or (":" not in wanted and f"{wanted}:latest" in names)
    if ready:
        _llm_down_until = 0.0
    else:
        _mark_llm_down()
    return {"running": True, "model_ready": ready}


def _call_local_llm(system_prompt: str, messages: list[dict]) -> str:
    payload = json.dumps({
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }).encode("utf-8")

    request = urllib.request.Request(
        _ollama_url("/api/chat"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with _opener.open(request, timeout=LLM_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise LocalLLMUnavailable(
                f"model '{settings.LOCAL_LLM_MODEL}' is not downloaded "
                f"(run: ollama pull {settings.LOCAL_LLM_MODEL})"
            )
        raise LocalLLMUnavailable(f"local LLM returned HTTP {e.code}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LocalLLMUnavailable(f"local LLM not reachable ({type(e).__name__})")

    content = ((body.get("message") or {}).get("content") or "").strip()
    if not content:
        raise LocalLLMUnavailable("local LLM returned an empty answer")
    return content


def _result_lines(report_context: dict) -> list[str]:
    lines = [
        f"Prediction: {report_context['prediction']}",
        f"Pneumonia probability: {report_context['pneumonia_probability']:.2f}%",
        f"Model confidence in that prediction: {report_context['confidence']:.2f}%",
        f"Decision threshold: {report_context['threshold'] * 100:.0f}% "
        "(pneumonia probability at or above this is reported as Pneumonia)",
        f"Model version: {report_context['model_version']}",
        f"Patient age: {report_context['patient_age']}",
        f"Patient gender: {report_context['patient_gender']}",
    ]
    if report_context.get("ai_explanation"):
        lines.append(f"Heatmap explanation shown to the user: {report_context['ai_explanation']}")
    return lines


def _system_prompt(report_context: dict | None, facts: dict | None) -> str:
    limitations = "\n".join(f"- {item}" for item in (facts or {}).get("limitations", []))

    if report_context is None:
        result = (
            "No X-ray result is loaded yet. Answer general questions and explain "
            "how the screening tool works. If asked about a specific result, ask "
            "the user to analyze an X-ray first."
        )
    else:
        result = "The screening result on the user's screen:\n" + "\n".join(_result_lines(report_context))

    return f"""You are the MediVision AI assistant inside a chest X-ray screening app. Doctors, medical staff, or patients ask you questions, often about the screening result below.

Rules:
- Answer every question the user asks as helpfully and accurately as you can, including general health, medical, and other questions.
- When talking about this particular X-ray, use only the result data and model facts below. You did not see the image. Never invent findings, numbers, or medical history.
- For medical topics, give clear general educational information. This is a screening aid, not a diagnosis: never diagnose the patient, prescribe, or give medicine doses, and recommend a qualified doctor for personal medical decisions.
- If the user mentions emergency symptoms (severe breathing difficulty, chest pain, bluish lips, confusion, very high fever in an infant), tell them to get urgent medical care immediately.
- If you are not sure of something, say so instead of guessing.
- Use simple, clear language and keep answers focused. Plain text only, no Markdown symbols like ** or #. For a list, start lines with "- ".

About the screening model:
- It only decides Normal vs Pneumonia. It cannot detect tuberculosis, lung cancer, fractures, or other conditions; a Normal result does not rule them out.
- The heatmap (Grad-CAM) shows which image regions influenced the model. It is not a confirmed location of disease.
- {_metrics_sentence(facts)}
Known limitations:
{limitations}

{result}"""


# ------------------------------------------------------------
# Built-in answers (no model needed)
# ------------------------------------------------------------

def _mentions(text: str, words: list[str]) -> bool:
    return any(re.search(r"\b" + re.escape(word) + r"\b", text) for word in words)


EMERGENCY_WORDS = [
    "can't breathe", "cannot breathe", "cant breathe", "trouble breathing",
    "difficulty breathing", "short of breath", "chest pain", "blue lips",
    "bluish", "unconscious", "fainted", "emergency", "confused", "seizure",
]
NO_RESULT = (
    "No X-ray has been analyzed on this page yet. Upload and analyze an X-ray "
    "first, then ask again and I'll explain that specific result."
)


def _answer_result(ctx: dict | None) -> str:
    if ctx is None:
        return NO_RESULT
    threshold_pct = ctx["threshold"] * 100
    if ctx["prediction"] == "Pneumonia":
        return (
            f"The AI flagged this X-ray as possible pneumonia. It estimated a "
            f"{ctx['pneumonia_probability']:.2f}% pneumonia probability, which is at or "
            f"above its {threshold_pct:.0f}% decision threshold.\n"
            "- This is a screening result, not a diagnosis.\n"
            "- A doctor should review the X-ray together with symptoms and an examination."
        )
    return (
        f"The AI did not flag pneumonia on this X-ray. It estimated a "
        f"{ctx['pneumonia_probability']:.2f}% pneumonia probability, below its "
        f"{threshold_pct:.0f}% decision threshold, so the result is Normal.\n"
        "- A Normal screening does not rule out pneumonia or other conditions.\n"
        "- If symptoms continue or get worse, see a doctor."
    )


def _answer_threshold(ctx: dict | None, facts: dict | None) -> str:
    threshold = ctx["threshold"] if ctx else (facts or {}).get("threshold")
    if threshold is None:
        return "The decision threshold for this model is not available."
    text = (
        f"The model outputs a pneumonia probability from 0% to 100%. The threshold is "
        f"{threshold * 100:.0f}%: at or above it the result is Pneumonia, below it Normal. "
        "It was chosen on a separate calibration set of test images to balance catching "
        "pneumonia against false alarms."
    )
    if ctx:
        text += f" This X-ray scored {ctx['pneumonia_probability']:.2f}%."
    return text


def _answer_heatmap(ctx: dict | None) -> str:
    general = (
        "The heatmap (Grad-CAM) colors the parts of the image that most influenced the "
        "model's output: red and yellow mean more influence. It shows where the model "
        "looked, not a confirmed location of disease."
    )
    if ctx and ctx.get("ai_explanation"):
        return f"{general}\n\nFor this X-ray: {ctx['ai_explanation']}"
    return general


def _answer_reliability(facts: dict | None) -> str:
    text = _metrics_sentence(facts)
    if facts and facts["limitations"]:
        text += (
            "\n- It was trained on one pediatric dataset and did not generalize reliably "
            "to external images.\n"
            "- It is a research screening tool, not validated for clinical use.\n"
            "- Every result should be confirmed by a qualified doctor."
        )
    return text


def _answer_next_steps(ctx: dict | None) -> str:
    text = (
        "I can't give medical advice or treatment, but in general:\n"
        "- Share this result with a doctor, who can review the X-ray itself, the "
        "symptoms and an examination.\n"
        "- Only a doctor should decide on tests or medicines."
    )
    if ctx and ctx["prediction"] == "Pneumonia":
        text += "\n- Because pneumonia was flagged, arrange that review soon."
    text += (
        "\n- If there is severe difficulty breathing, chest pain, bluish lips or "
        "confusion, get urgent medical care immediately."
    )
    return text


def _answer_limitations() -> str:
    return (
        "This model only decides Normal vs Pneumonia. It cannot detect tuberculosis, "
        "lung cancer, fractures, heart problems or other conditions, and a Normal "
        "result does not rule them out. It also cannot tell bacterial from viral "
        "pneumonia."
    )


def _answer_pneumonia() -> str:
    return (
        "Pneumonia is an infection that inflames the air sacs in one or both lungs; "
        "they can fill with fluid or pus. Common symptoms are cough, fever, chills and "
        "difficulty breathing. It can be caused by bacteria, viruses or fungi. A doctor "
        "diagnoses it using symptoms, an examination and often a chest X-ray."
    )


def _answer_how_it_works(facts: dict | None) -> str:
    threshold = (facts or {}).get("threshold")
    threshold_text = f"{threshold * 100:.0f}%" if threshold is not None else "a fixed threshold"
    return (
        "You upload a chest X-ray. A MobileNetV2 deep-learning model, trained on labeled "
        "chest X-rays, outputs a pneumonia probability from 0% to 100%. If it is at or "
        f"above {threshold_text} the result is Pneumonia, otherwise Normal. A Grad-CAM "
        "heatmap then shows which image regions influenced that output. It is a "
        "screening aid; a doctor makes the diagnosis."
    )


def builtin_answer(question: str, ctx: dict | None, facts: dict | None) -> str:
    text = question.lower()

    if _mentions(text, EMERGENCY_WORDS):
        return (
            "If someone has severe difficulty breathing, chest pain, bluish lips, "
            "confusion or a very high fever, please get urgent medical care now "
            "(call your local emergency number). This tool can't help in an emergency."
        )
    if _mentions(text, ["heatmap", "heat map", "grad-cam", "gradcam", "colors", "colours",
                        "red", "yellow", "highlighted", "focus", "focused"]):
        return _answer_heatmap(ctx)
    if _mentions(text, ["threshold", "cutoff", "cut-off", "cut off"]):
        return _answer_threshold(ctx, facts)
    if _mentions(text, ["reliable", "reliability", "accurate", "accuracy", "trust",
                        "sure", "auc", "sensitivity", "specificity", "wrong", "mistake"]):
        return _answer_reliability(facts)
    if _mentions(text, ["next", "should i", "what do i do", "what should", "treatment",
                        "treat", "medicine", "medication", "antibiotic", "antibiotics", "doctor"]):
        return _answer_next_steps(ctx)
    if _mentions(text, ["detect", "limitation", "limitations", "tuberculosis", "tb",
                        "cancer", "covid", "other disease", "other diseases"]):
        return _answer_limitations()
    if _mentions(text, ["what is pneumonia", "pneumonia mean", "symptom", "symptoms",
                        "cause", "causes", "contagious"]):
        return _answer_pneumonia()
    if _mentions(text, ["how does", "how do", "work", "works", "working", "how it works"]):
        return _answer_how_it_works(facts)
    if _mentions(text, ["mean", "means", "result", "explain", "normal", "positive",
                        "negative", "probability", "percent", "confidence", "score"]):
        return _answer_result(ctx)
    if _mentions(text, ["hi", "hello", "hey", "help"]):
        return (
            "Hello! I can explain this X-ray screening result: what it means, the "
            "threshold, the heatmap, how reliable the model is, what it can't detect, "
            "and general next steps."
        )

    return (
        "I'm running in offline mode, so I can only answer common questions about "
        "this result. Try asking: what the result means, what the threshold is, what "
        "the heatmap shows, how reliable the model is, what it can't detect, or what "
        "to do next. Start the local AI model to ask free-form questions."
    )


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def ask(messages: list[dict], report_context: dict | None) -> dict:
    """messages: [{"role": "user"|"assistant", "content": str}, ...],
    already validated to start and end with a user turn."""
    facts = load_model_facts()
    question = messages[-1]["content"]

    # Safety first: emergency wording always gets the fixed urgent-care
    # answer, never a small model's improvisation.
    if _mentions(question.lower(), EMERGENCY_WORDS):
        return {"reply": builtin_answer(question, report_context, facts), "source": "builtin", "model": None}

    builtin = {"reply": builtin_answer(question, report_context, facts), "source": "builtin", "model": None}

    if _llm_recently_down():
        return builtin

    recent = messages[-LLM_HISTORY_MESSAGES:]
    if recent[0]["role"] != "user":
        recent = recent[1:]

    try:
        reply = _call_local_llm(_system_prompt(report_context, facts), recent)
        return {"reply": reply, "source": "local_llm", "model": settings.LOCAL_LLM_MODEL}
    except LocalLLMUnavailable as e:
        logger.info("Chatbot: using built-in answers (%s)", e)
        _mark_llm_down()
        return builtin
