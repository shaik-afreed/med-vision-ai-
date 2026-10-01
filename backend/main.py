from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

from routers.home import router as home_router
from routers.auth import router as auth_router
from routers.patient import router as patient_router
from routers.report import router as report_router
from routers.document import router as document_router
from routers.chat import router as chat_router
from routers.model_info import router as model_info_router

from database.database import engine

# Schema is managed by Alembic migrations (see alembic/), not
# Base.metadata.create_all(). Run `alembic upgrade head` before starting
# the server, including on a fresh clone - or set AUTO_MIGRATE=true to have
# the server apply them itself at startup (used on the Render deployment).

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.AUTO_MIGRATE:
        # Imported here: alembic is slow to import and unused otherwise.
        from database.migrate import run_migrations

        run_migrations()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    description=(
        "AI-assisted chest X-ray screening platform. "
        "AI predictions are a research-support screening aid, not a "
        "clinical diagnosis."
    ),
)


# ==============================
# CORS
# ==============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# ROUTERS
# ==============================

app.include_router(home_router)
app.include_router(auth_router)
app.include_router(patient_router)
app.include_router(report_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(model_info_router)


# ==============================
# HEALTH
# ==============================

@app.get("/health", tags=["System"])
def health():
    db_status = "ok"

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "model_version": settings.MODEL_VERSION,
    }
