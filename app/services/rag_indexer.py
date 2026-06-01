"""분석 결과를 RAG 청크로 인덱싱.

submit_analysis_result 직후 BackgroundTasks로 호출. 실패는 best-effort
(분석 응답 자체를 막지 않음), 단 analyses.rag_indexed_at으로 ready 여부를 노출.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.analysis import Analysis
from app.models.rag_chunk import RagChunk
from app.services.chunk_builder import (
    Chunk,
    build_all_chunks,
    build_progress_delta_chunk,
)
from app.services.openai_client import OpenAIClientError, embed_texts

logger = logging.getLogger(__name__)


def _payload_from_analysis(db: Session, analysis: Analysis) -> dict:
    """analysis_results.report_json + analysis.transcript에서 payload 재구성."""
    result = analysis.result
    if result is None:
        return {}
    report = dict(result.report_json or {})
    payload: dict[str, Any] = {
        "overall_scores": {
            "content_coverage_user": result.content_coverage,
            "delivery_stability": result.delivery_stability,
            "pacing_score": result.pacing_score,
        },
        "llm_feedback": {
            "overall_comment": report.get("summary", ""),
            "strengths": [
                s.get("text") if isinstance(s, dict) else s
                for s in (report.get("strengths") or [])
            ],
            "priority_actions": [
                a.get("text") if isinstance(a, dict) else a
                for a in (report.get("improvements") or [])
            ],
            "slide_comments": [],
        },
        "transcript_segments": [],
        "highlight_sections": [],
        "per_slide_detail": [],
        "reliability": report.get("reliability"),
    }
    # sections에서 slide 단위 transcript / feedback 재구성
    for sec in sorted(analysis.sections or [], key=lambda s: s.order_index):
        title = sec.title or ""
        slide_id = _extract_slide_id(title)
        if slide_id is None:
            continue
        feedback_text = (sec.feedback_json or {}).get("text", "")
        transcript_text = (sec.feedback_json or {}).get("transcript", "")
        if transcript_text:
            payload["transcript_segments"].append(
                {
                    "slide_id": slide_id,
                    "start_sec": float(sec.start_time_sec or 0),
                    "end_sec": float(sec.end_time_sec or 0),
                    "text": transcript_text,
                }
            )
        if feedback_text:
            payload["llm_feedback"]["slide_comments"].append(
                {"slide_id": slide_id, "comment": feedback_text}
            )
    return payload


def _extract_slide_id(title: str) -> int | None:
    import re

    m = re.search(r"(\d+)", title or "")
    return int(m.group(1)) if m else None


def _existing_attempt_count(db: Session, note_id: UUID, this_analysis_id: UUID) -> int:
    """이번 분석을 포함한 attempt 인덱스 (1-base)."""
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS c
            FROM analyses
            WHERE note_id = :nid
              AND status = 'done'
              AND (finished_at IS NOT NULL OR analysis_id = :aid)
            """
        ),
        {"nid": str(note_id), "aid": str(this_analysis_id)},
    ).fetchone()
    return int(row[0] or 0) if row else 1


def _previous_metric_chunk(db: Session, note_id: UUID, this_analysis_id: UUID) -> RagChunk | None:
    return (
        db.query(RagChunk)
        .filter(
            RagChunk.note_id == note_id,
            RagChunk.chunk_type == "metric",
            RagChunk.analysis_id.isnot(None),
            RagChunk.analysis_id != this_analysis_id,
        )
        .order_by(RagChunk.attempt_index.desc().nullslast(), RagChunk.created_at.desc())
        .first()
    )


def _upsert_chunk(
    db: Session,
    *,
    user_id: UUID,
    note_id: UUID,
    analysis_id: UUID | None,
    attempt_index: int | None,
    chunk: Chunk,
    embedding: list[float],
) -> None:
    eff_analysis_id = None if chunk.is_note_scoped else analysis_id

    values = {
        "user_id": user_id,
        "note_id": note_id,
        "analysis_id": eff_analysis_id,
        "chunk_type": chunk.chunk_type,
        "chunk_key": chunk.chunk_key,
        "slide_id": chunk.slide_id,
        "start_sec": chunk.start_sec,
        "end_sec": chunk.end_sec,
        "attempt_index": None if chunk.is_note_scoped else attempt_index,
        "content": chunk.content,
        "metadata": chunk.metadata,
        "embedding": embedding,
        "content_hash": chunk.content_hash,
    }

    if chunk.is_note_scoped:
        constraint = "uq_rag_note_shared_chunk"
    else:
        constraint = "uq_rag_analysis_chunk"

    stmt = pg_insert(RagChunk.__table__).values(**values)
    stmt = stmt.on_conflict_do_update(
        constraint=constraint,
        set_={
            "user_id": stmt.excluded.user_id,
            "slide_id": stmt.excluded.slide_id,
            "start_sec": stmt.excluded.start_sec,
            "end_sec": stmt.excluded.end_sec,
            "attempt_index": stmt.excluded.attempt_index,
            "content": stmt.excluded.content,
            "metadata": stmt.excluded.metadata,
            "embedding": stmt.excluded.embedding,
            "content_hash": stmt.excluded.content_hash,
        },
    )
    db.execute(stmt)


def index_analysis(analysis_id: UUID, *, payload_override: dict | None = None) -> None:
    """분석 결과를 RAG 인덱스에 적재. BackgroundTask에서 호출.

    payload_override: submit_analysis_result에서 워커가 보낸 원본 payload를 그대로
    넘기면 DB 재구성 단계를 생략한다. 백필 등에서는 None으로 호출 → DB에서 재구성.
    """
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        if analysis is None:
            logger.warning("[rag_indexer] analysis not found: %s", analysis_id)
            return

        payload = payload_override or _payload_from_analysis(db, analysis)
        attempt_index = _existing_attempt_count(db, analysis.note_id, analysis.analysis_id)

        chunks = build_all_chunks(payload, attempt_index)

        prev_metric = _previous_metric_chunk(db, analysis.note_id, analysis.analysis_id)
        this_metric = next((c for c in chunks if c.chunk_type == "metric"), None)
        if prev_metric is not None and this_metric is not None and prev_metric.attempt_index:
            delta = build_progress_delta_chunk(
                prev_metric.metadata_json or {},
                this_metric.metadata,
                prev_attempt=prev_metric.attempt_index,
                this_attempt=attempt_index,
            )
            if delta is not None:
                chunks.append(delta)

        if not chunks:
            logger.warning("[rag_indexer] no chunks for analysis %s", analysis_id)
            return

        try:
            embeddings = embed_texts([c.content for c in chunks])
        except OpenAIClientError as exc:
            logger.error("[rag_indexer] embedding failed for %s: %s", analysis_id, exc)
            return

        for chunk, emb in zip(chunks, embeddings):
            _upsert_chunk(
                db,
                user_id=analysis.user_id,
                note_id=analysis.note_id,
                analysis_id=analysis.analysis_id,
                attempt_index=attempt_index,
                chunk=chunk,
                embedding=emb,
            )

        analysis.rag_indexed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "[rag_indexer] indexed %d chunks for analysis %s (attempt %d)",
            len(chunks),
            analysis_id,
            attempt_index,
        )
    except Exception:
        db.rollback()
        logger.exception("[rag_indexer] failed for analysis %s", analysis_id)
    finally:
        db.close()
