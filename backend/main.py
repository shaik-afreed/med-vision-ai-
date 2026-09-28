from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.home import router as home_router
from routers.auth import router as auth_router
from routers.patient import router as patient_router

from database.database import Base, engine
from models.user import User
from models.patient import Patient
from models.report import Report
from routers.report import router as report_router
from routers.predict import router as predict_router


Base.metadata.create_all(bind=engine)


app = FastAPI()


# ==============================
# CORS
# ==============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
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
app.include_router(predict_router)
