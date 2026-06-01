import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from sqlalchemy import text

from app.db import Base, engine
from app import models
from app.routers.note import router as note_router
from app.routers.upload import router as upload_router
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router

app = FastAPI(title="SpeechPT API")

allowed_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://127.0.0.1:5500,http://localhost:5500"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(note_router)
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup():
    # ── RAG 마이그레이션 (idempotent) ────────────────────────────
    # create_all은 신규 테이블만 만들고 기존 테이블 ALTER는 하지 않으므로,
    # 확장 설치 + 기존 테이블 컬럼 추가는 raw SQL로 명시 실행.
    with engine.begin() as conn:
        # 1) pgvector 확장 (rag_chunks 테이블의 VECTOR 컬럼 생성 전제)
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # 2) 기존 테이블 신규 컬럼 (이미 있으면 무시)
        conn.execute(text(
            "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS rag_indexed_at TIMESTAMPTZ"
        ))
        conn.execute(text(
            "ALTER TABLE chat_messages "
            "ADD COLUMN IF NOT EXISTS citations_json JSONB NOT NULL DEFAULT '[]'::jsonb"
        ))

    # 3) 신규 테이블 (rag_chunks) 생성. 모델 정의된 모든 테이블 idempotent.
    Base.metadata.create_all(bind=engine)

    # 4) HNSW 인덱스 (모델 메타에 없어서 별도 생성)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rag_embedding "
            "ON rag_chunks USING hnsw (embedding vector_cosine_ops)"
        ))


@app.get("/healthz")
def health_check():
    return {"status": "ok"}