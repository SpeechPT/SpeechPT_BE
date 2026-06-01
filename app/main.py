import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app import models
from app.routers.note import router as note_router
from app.routers.upload import router as upload_router
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router

logger = logging.getLogger(__name__)

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


# ──────────────────────────────────────────────────────────────────
# RAG 인덱싱 폴러
#
# 워커(analysis_worker.py)가 분석 결과를 DB에 직접 INSERT/UPDATE하기 때문에
# /analyses/{id}/submit-result 엔드포인트의 BackgroundTask 트리거가
# 동작하지 않는다. 그래서 이 백그라운드 루프가 rag_indexed_at IS NULL인
# done 분석을 주기적으로 잡아 인덱싱한다.
#
# 멱등성:
#   - rag_chunks에 ON CONFLICT DO UPDATE가 걸려 있어 중복 호출 안전
#   - 여러 uvicorn 워커가 동시에 같은 분석을 잡아도 데이터 손상 없음
#     (다만 임베딩 비용이 중복될 뿐. 필요시 advisory lock으로 확장 가능)
# ──────────────────────────────────────────────────────────────────
RAG_POLL_INTERVAL_SEC = int(os.environ.get("RAG_POLL_INTERVAL_SEC", "20"))
RAG_POLL_BATCH_SIZE = int(os.environ.get("RAG_POLL_BATCH_SIZE", "5"))
RAG_POLL_INITIAL_DELAY_SEC = int(os.environ.get("RAG_POLL_INITIAL_DELAY_SEC", "5"))

_rag_poller_task: asyncio.Task | None = None


def _find_pending_analysis_ids(batch_size: int) -> list:
    """status='done' 인데 rag_indexed_at IS NULL인 분석 ID들."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT analysis_id
                FROM analyses
                WHERE status = 'done' AND rag_indexed_at IS NULL
                ORDER BY finished_at DESC NULLS LAST
                LIMIT :limit
                """
            ),
            {"limit": batch_size},
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        db.close()


def _index_one_analysis(analysis_id) -> None:
    """단일 분석 인덱싱. rag_indexer를 호출만 함 (예외는 호출자가 처리)."""
    # 지연 import: OpenAI 키 없는 환경에서 모듈 import 자체 실패 회피
    from app.services.rag_indexer import index_analysis

    index_analysis(analysis_id)


async def _rag_poller_loop() -> None:
    """주기적으로 미인덱싱 분석을 잡아 RAG 인덱싱."""
    # startup hook 완료 후 잠시 대기 (DB 마이그레이션이 먼저 끝나도록)
    await asyncio.sleep(RAG_POLL_INITIAL_DELAY_SEC)
    logger.info(
        "[rag_poller] 시작 (interval=%ds, batch=%d)",
        RAG_POLL_INTERVAL_SEC,
        RAG_POLL_BATCH_SIZE,
    )

    while True:
        try:
            ids = await asyncio.to_thread(
                _find_pending_analysis_ids, RAG_POLL_BATCH_SIZE
            )
            if ids:
                logger.info("[rag_poller] 미인덱싱 %d건 발견: %s", len(ids), ids)
            for aid in ids:
                try:
                    await asyncio.to_thread(_index_one_analysis, aid)
                except Exception:
                    logger.exception("[rag_poller] 분석 %s 인덱싱 실패", aid)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[rag_poller] 루프 에러")

        try:
            await asyncio.sleep(RAG_POLL_INTERVAL_SEC)
        except asyncio.CancelledError:
            raise


@app.on_event("startup")
async def _start_rag_poller():
    global _rag_poller_task
    if _rag_poller_task is None or _rag_poller_task.done():
        _rag_poller_task = asyncio.create_task(_rag_poller_loop())


@app.on_event("shutdown")
async def _stop_rag_poller():
    global _rag_poller_task
    if _rag_poller_task is not None:
        _rag_poller_task.cancel()
        try:
            await _rag_poller_task
        except (asyncio.CancelledError, Exception):
            pass
        _rag_poller_task = None


@app.get("/healthz")
def health_check():
    return {"status": "ok"}