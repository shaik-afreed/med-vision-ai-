<div align="center">

# 🩺 MediVision AI

### AI-assisted chest X-ray screening platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13-FF6F00?logo=tensorflow&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![Playwright](https://img.shields.io/badge/E2E-Playwright-2EAD33?logo=playwright&logoColor=white)

A FastAPI backend, a React frontend, and a fine-tuned MobileNetV2 model
that screens chest X-rays for signs consistent with pneumonia.

</div>

<br>

> ### ⚠️ Medical disclaimer
> **MediVision AI is a research/educational screening-support tool. It is
> not a medical device and does not produce a clinical diagnosis.** Every
> AI result must be reviewed by a qualified healthcare professional before
> any clinical decision is made. See [🚧 Limitations](#limitations--medical-disclaimer)
> below — in particular, the model's known failure to generalize to X-rays
> outside its training dataset.

<br>

## 📚 Contents

| | | |
|---|---|---|
| 🏗️ [Architecture](#architecture) | ✨ [Features](#features) | 🧠 [AI Model](#ai-model) |
| 🚀 [Getting Started](#getting-started) | 🔐 [Environment Variables](#environment-variables) | 📡 [API](#api) |
| 🧪 [Testing](#testing) | 📁 [Project Structure](#project-structure) | 🚧 [Limitations](#limitations--medical-disclaimer) |

<br>

## 🏗️ Architecture

```
frontend (React + Vite)  --HTTP-->  backend (FastAPI)  --loads-->  ai_model/saved_models/*.h5
                                        |
                                        v
                                   SQLite (dev) via SQLAlchemy + Alembic migrations
```

| Layer | Stack |
|---|---|
| 🎨 **Frontend** | React 19, Vite, react-router-dom. Talks to the backend only through `frontend/src/api/api.js` (a single axios client with request/response interceptors for auth and 401 handling). |
| ⚙️ **Backend** | FastAPI, SQLAlchemy, JWT auth (python-jose + passlib/bcrypt), Pydantic schemas, Alembic migrations. Config comes from environment variables via `pydantic-settings` (`backend/core/config.py`) — never hardcoded secrets. |
| 🧠 **AI** | A MobileNetV2-based transfer-learning model (`ai_model/saved_models/fine_tuned_model.h5`), loaded **once** at backend startup (`backend/services/prediction.py`), not per-request. |
| 🗄️ **Database** | SQLite for local development (schema in `backend/alembic/versions/`); every patient and report row is scoped to the user (doctor) who created it — one user cannot read, edit, or delete another user's patients or reports. |

<br>

## ✨ Features

- 🔑 JWT-based registration/login
- 👥 Patient CRUD, scoped per user
- 🩻 Chest X-ray upload with **real image validation** (not just a `Content-Type` header check), a hard size cap, and non-guessable stored filenames
- 📊 AI screening result: prediction, pneumonia probability, model confidence, the operating threshold and model version used, and a medical disclaimer — not just a bare "Pneumonia 99%"
- 📝 Medical reports list/detail view with a lightweight clinical-notes/status workflow (`PATCH /reports/{id}`)
- 📈 Dashboard stats pulled from the **real database** and the **real evaluation report** (`GET /model/info`) — no hardcoded numbers
- 💓 `GET /health` for basic liveness/DB connectivity checks

<br>

## 🧠 AI Model

- **Base**: MobileNetV2 (ImageNet weights), trained in two phases — `ai_model/train.py` (frozen backbone) then `ai_model/fine_tune.py` (unfreezes the last 30 layers, keeping BatchNorm frozen)
- **Input**: 224×224 RGB. `mobilenet_v2.preprocess_input` is applied *inside* the model graph (part of the saved `.h5`), so every caller — training, evaluation, and the backend — feeds raw 0–255 pixel arrays and never normalizes externally. This is verified consistent across the whole pipeline.
- **Output**: a single sigmoid probability that the image is `PNEUMONIA`

### 🔬 Evaluation methodology

<details>
<summary><strong>Click to expand — a real bug was found and fixed here, worth reading for viva</strong></summary>

<br>

The project used to have 9 different, partly conflicting evaluation
scripts, and the deployed operating threshold (`0.66`) had no traceable
derivation. Auditing them surfaced a real bug: `fine_tune.py`'s validation
split used `shuffle=False`, which (given `image_dataset_from_directory`'s
behavior) produced a validation set that was 100% PNEUMONIA — so the
val_auc-based checkpointing during the fine-tuning phase that produced the
deployed model was driven by a degenerate, single-class signal. That bug is
fixed in `fine_tune.py`, and since Phase 1 training had already seen nearly
the entire `train/` directory by the time Phase 2 ran, there was no
leakage-free subset of `train/` left to calibrate a threshold on the
already-trained weights.

`ai_model/evaluate_model.py` is now the **single authoritative evaluation
script** (the old ones are kept in `ai_model/archive/` for reference, with
notes on why each was retired). It treats the untouched **test** set as the
only clean data available, splits it once (stratified, seeded) into a
calibration subset and a disjoint holdout subset, selects the operating
threshold via Youden's J on calibration only, and reports final metrics on
holdout only — so the threshold is never chosen using the same images the
reported numbers come from.

</details>

<br>

**Run it with:**

```bash
cd ai_model
python evaluate_model.py
```

It writes `ai_model/evaluation_report.json`, which the backend's
`GET /model/info` endpoint reads directly (the frontend dashboard's "AI
Model AUC" card is not a hardcoded number).

### 📊 Current results

`ai_model/evaluation_report.json`, threshold = **0.82**

| Metric | Holdout subset (375 images) | Full test set (624 images) |
|---|:---:|:---:|
| 🎯 AUC | — | **0.967** |
| ✅ Accuracy | **0.907** | — |
| 🎪 Precision | **0.950** | — |
| 🔍 Recall (sensitivity) | **0.897** | — |
| 🛡️ Specificity | **0.922** | — |
| ⚖️ F1 | **0.923** | — |

AUC is threshold-independent and computed on the full test set; the other
metrics are only meaningful at a chosen threshold and are reported on the
375-image holdout subset that was never used to pick that threshold.

### 🌍 External generalization check

`ai_model/evaluate_model.py` also scores the 3 images in `real_test/`,
which are not part of the training dataset's distribution. This is *not* a
validated benchmark (3 images is not a sample size to draw conclusions
from), but the result is disclosed rather than hidden: **2 of the 3
external images were misclassified**, including images intended as
known-normal. This suggests the model does not reliably generalize beyond
the imaging conditions of its single-source training dataset
(Kermany/Guangzhou pediatric chest X-rays) — see
[🚧 Limitations](#limitations--medical-disclaimer).

### 🎨 Explainability (Grad-CAM)

❌ **Not implemented.** The brief for this project explicitly said not to
fake a heatmap, and implementing Grad-CAM correctly against the nested
MobileNetV2 sub-model (extracting intermediate conv-layer activations,
verifying the gradient path, and testing it produces sensible
localization) is real engineering work that wasn't completed in this pass.
This is flagged as future work rather than shipped incorrectly.

<br>

## 🚀 Getting Started

### ⚙️ Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

copy .env.example .env       # Windows: copy; macOS/Linux: cp
# then edit .env and set a real SECRET_KEY:
# python -c "import secrets; print(secrets.token_urlsafe(32))"

alembic upgrade head          # creates/updates medivision.db
uvicorn main:app --reload --port 8000
```

📍 API docs: **http://127.0.0.1:8000/docs**

### 🎨 Frontend

```bash
cd frontend
npm install
copy .env.example .env       # Windows: copy; macOS/Linux: cp
npm run dev
```

📍 App: **http://localhost:5173**

### 🧠 AI model *(optional — only needed to retrain or re-run evaluation)*

```bash
cd ai_model
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# dataset/archive/chest_xray/{train,test}/{NORMAL,PNEUMONIA}/ must exist
# (Kermany et al. chest X-ray dataset; not committed to this repo — see
# https://data.mendeley.com/datasets/rscbjbr9sj)
python evaluate_model.py
```

> 💡 **Troubleshooting:** if `pip install` fails with an SSL certificate
> error inside a fresh virtual environment, it's usually a local
> proxy/certificate-store issue, not a problem with this project. Try:
> `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`

<br>

## 🔐 Environment Variables

### `backend/.env` — see `backend/.env.example`

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy database URL (default: local SQLite file) |
| `SECRET_KEY` | JWT signing secret — **must** be set to a real random value outside local dev |
| `ALGORITHM` | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `UPLOAD_DIR` | Where uploaded X-rays are stored |
| `MAX_UPLOAD_SIZE_MB` | Upload size cap |
| `MODEL_VERSION` | Label shown on reports/API responses |

### `frontend/.env` — see `frontend/.env.example`

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL the frontend talks to |

<br>

## 📡 API

Interactive docs (Swagger UI) at `/docs` 📖, ReDoc at `/redoc`, once the
backend is running. Every route has a proper `response_model`, so the
schemas shown there match what the API actually returns.

| Route | Notes |
|---|---|
| 🔑 `POST /auth/register`, `POST /auth/login` | JWT auth |
| 👥 `GET /patients/`, `POST /patients/`, `GET/PUT/DELETE /patients/{id}` | Scoped to the authenticated user |
| 🩻 `POST /reports/upload` | Validates + stores an X-ray, runs AI prediction, saves the report |
| 📝 `GET /reports/`, `GET /reports/{id}/image`, `PATCH /reports/{id}` | Also scoped to the authenticated user |
| 🧠 `GET /model/info` | Real metrics from `ai_model/evaluation_report.json` |
| 💓 `GET /health` | DB connectivity + model version |

<br>

## 🧪 Testing

### 🐍 Backend (pytest)

```bash
cd backend
pytest
```

**20 tests ✅** covering auth (register/login/duplicate-email/wrong-password/short-password),
patient CRUD and cross-user isolation, and the report upload flow —
including the security fixes verified against a live server during this
project's rebuild: unauthenticated upload rejected, non-image and
corrupted-image uploads rejected, and cross-user access to another user's
patient/report returns 404. Tests run against an isolated in-memory SQLite
database and exercise the real trained model (not a mock), so
`predict_disease()`'s actual behavior is what's being tested.

AI model evaluation (`ai_model/evaluate_model.py`) is intentionally kept
separate from application tests — it validates model quality, not API
behavior. See [🧠 AI Model](#ai-model) above.

### 🎭 End-to-end (Playwright)

```bash
cd e2e
npm install
npx playwright install chromium   # first time only
npm test
```

**3 specs ✅**, nothing mocked. `playwright.config.js` starts both the
backend and the frontend dev server itself, so this doesn't require either
to already be running. `tests/golden-path.spec.js` drives a real browser
through:

```
register → dashboard (live AUC card) → create patient → upload real X-ray
  → real model prediction renders in the AI result panel
  → same report appears in Medical Reports with image + result
  → sign out → protected routes redirect to /login ✅
```

Plus: unauthenticated visitors get redirected, and a wrong password
surfaces an error instead of failing silently.

<br>

## 📁 Project Structure

```
backend/
  core/config.py           # env-driven settings (pydantic-settings)
  models/                  # SQLAlchemy models (User, Patient, Report)
  schemas/                 # Pydantic request/response schemas
  routers/                 # auth, patient, report, model_info, home
  services/prediction.py   # loads the model once, runs inference
  dependencies/auth.py     # get_current_user (JWT -> real User row)
  alembic/                 # migrations
  tests/                   # pytest suite

frontend/
  src/api/api.js           # the only place that talks to the backend
  src/context/AuthContext.jsx
  src/components/          # Layout, ProtectedRoute, ResultPanel
  src/pages/                # Dashboard, Patients, XRayAnalysis, MedicalReports, Login

ai_model/
  train.py, fine_tune.py    # 2-phase MobileNetV2 transfer learning
  evaluate_model.py         # the one authoritative evaluation pipeline
  evaluation_report.json    # its output - read by backend's /model/info
  archive/                  # superseded evaluation scripts, kept for reference

e2e/
  playwright.config.js      # boots backend + frontend, then runs tests
  tests/golden-path.spec.js
```

<br>

## 🚧 Limitations & Medical Disclaimer

- 🚫 **This is not a diagnostic tool.** It produces a screening probability, not a diagnosis. It has not been validated for clinical use.
- 🌍 **Single-source training data.** The model was trained on one dataset (Kermany/Guangzhou pediatric chest X-rays). The external check in `ai_model/evaluate_model.py` found it misclassifies X-rays outside that dataset's imaging conditions more often than the in-distribution test metrics would suggest — do not extrapolate the reported accuracy to X-rays from other sources, scanners, or patient populations.
- 📏 **Small holdout sample.** Precision/recall/specificity/F1 are reported on a 375-image holdout subset; treat them as estimates with real sampling uncertainty, not exact figures. AUC (computed on the full 624-image test set) is the more stable number.
- 🎨 **No explainability yet.** There is no Grad-CAM or other visual explanation of *why* the model predicted what it did — see [Explainability](#explainability-grad-cam).
- ⛔ **Never** treat an AI "Normal" result as ruling out disease, or a "Pneumonia" result as confirming it. Always route to a qualified healthcare professional for clinical review.

<br>

<div align="center">

Built as a hands-on exercise in shipping an AI product honestly — bugs found, disclosed, and fixed, not hidden.

</div>
