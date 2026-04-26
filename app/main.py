from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from app.db import Base, engine 
from app import models
from app.routers.note import router as note_router  
from app.routers.upload import router as upload_router
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router

app = FastAPI(title="SpeechPT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(note_router)
app.include_router(upload_router)
app.include_router(analysis_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def health_check():
    return {"status": "ok"}