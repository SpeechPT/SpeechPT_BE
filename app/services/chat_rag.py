"""RAG 검색 + LLM 답변 생성.

흐름:
1. 의도 분류 (룰 기반)
2. 의도별 강제 포함 청크 + cosine top-k 청크 검색
3. [1][2] 마커로 컨텍스트 패킹 → LLM이 마커만 인용
4. LLM 응답 파싱 + 마커→chunk_id 후매핑 + 검증
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage
from app.services.openai_client import OpenAIClientError, chat_responses_json, embed_texts, stream_chat_text

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = int(os.environ.get("RAG_TOP_K", "8"))
MAX_HISTORY_TURNS = 6


class Intent(str, Enum):
    PROGRESS_COMPARISON = "progress_comparison"
    SLIDE_SPECIFIC = "slide_specific"
    METRIC = "metric"
    ACTION_PLAN = "action_plan"
    GENERAL = "general"


_COMPARISON_PAT = re.compile(r"(지난번|이전|예전|비교|나아졌|좋아졌|개선|얼마나\s*늘|얼마나\s*줄)")
_SLIDE_PAT = re.compile(r"슬라이드\s*(\d+)")
_METRIC_PAT = re.compile(r"(점수|스코어|몇\s*점|score)")
_ACTION_PAT = re.compile(r"(어떻게|방법|어떡|연습|개선|고치|훈련|tip|팁)")


@dataclass
class Intent_:
    kind: Intent
    slide_id: Optional[int] = None


def classify_intent(question: str) -> Intent_:
    q = question or ""
    slide_match = _SLIDE_PAT.search(q)
    if _COMPARISON_PAT.search(q):
        return Intent_(Intent.PROGRESS_COMPARISON, slide_id=int(slide_match.group(1)) if slide_match else None)
    if slide_match:
        return Intent_(Intent.SLIDE_SPECIFIC, slide_id=int(slide_match.group(1)))
    if _METRIC_PAT.search(q):
        return Intent_(Intent.METRIC)
    if _ACTION_PAT.search(q):
        return Intent_(Intent.ACTION_PLAN)
    return Intent_(Intent.GENERAL)


def _latest_done_analysis_id(db: Session, note_id: UUID, user_id: UUID) -> UUID | None:
    row = (
        db.query(Analysis.analysis_id)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc().nullslast(), Analysis.created_at.desc())
        .first()
    )
    return row[0] if row else None


def _vector_literal(emb: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.7f}" for x in emb) + "]"


def _retrieve_chunks(
    db: Session,
    *,
    user_id: UUID,
    note_id: UUID,
    latest_analysis_id: UUID | None,
    question_embedding: list[float],
    intent: Intent_,
    top_k: int,
) -> list[dict]:
    """의도별 forced + cosine 결합 검색.

    forced_types: 항상 포함되는 청크 종류 (조건 부합 시 무조건 반환)
    cosine_types: cosine 유사도 상위만 가져오는 청크 종류 (latest analysis 한정)
    """
    forced_clauses: list[str] = []  # SQL 조각
    cosine_types: list[str] = []
    params: dict[str, Any] = {
        "uid": str(user_id),
        "nid": str(note_id),
        "lid": str(latest_analysis_id) if latest_analysis_id else None,
        "qemb": _vector_literal(question_embedding),
        "limit": top_k,
    }

    kind = intent.kind

    if kind == Intent.PROGRESS_COMPARISON:
        forced_clauses.append("chunk_type IN ('metric','progress_delta')")
        if intent.slide_id is not None:
            forced_clauses.append("(chunk_type IN ('transcript_segment','feedback_slide') AND slide_id = :slide_id)")
            params["slide_id"] = intent.slide_id
        cosine_types = ["feedback_overall", "slide_text"]
    elif kind == Intent.SLIDE_SPECIFIC:
        forced_clauses.append("(slide_id = :slide_id AND (analysis_id = :lid OR analysis_id IS NULL))")
        params["slide_id"] = intent.slide_id
        cosine_types = ["feedback_overall", "metric", "practice_plan"]
    elif kind == Intent.METRIC:
        forced_clauses.append("chunk_type IN ('metric','progress_delta')")
        cosine_types = ["feedback_overall", "feedback_slide"]
    elif kind == Intent.ACTION_PLAN:
        forced_clauses.append(
            "(chunk_type = 'practice_plan' AND analysis_id = :lid) OR "
            "(chunk_type = 'feedback_overall' AND chunk_key LIKE 'priority_action:%' AND analysis_id = :lid)"
        )
        cosine_types = ["feedback_slide", "transcript_segment", "slide_text"]
    else:
        cosine_types = ["transcript_segment", "feedback_slide", "feedback_overall", "slide_text", "metric"]

    # forced 절: 항상 user_id+note_id 필터
    forced_sql = ""
    if forced_clauses:
        forced_sql = f"""
            SELECT chunk_id, chunk_type, chunk_key, content, metadata, slide_id, start_sec, end_sec,
                   attempt_index, analysis_id, 1.0::float8 AS sim, TRUE AS forced
            FROM rag_chunks
            WHERE user_id = :uid AND note_id = :nid
              AND ({" OR ".join(forced_clauses)})
        """

    cosine_sql = ""
    if cosine_types:
        params["cosine_types"] = cosine_types
        # latest 한정 + cosine
        cosine_sql = """
            SELECT chunk_id, chunk_type, chunk_key, content, metadata, slide_id, start_sec, end_sec,
                   attempt_index, analysis_id,
                   1 - (embedding <=> CAST(:qemb AS vector)) AS sim,
                   FALSE AS forced
            FROM rag_chunks
            WHERE user_id = :uid AND note_id = :nid
              AND chunk_type = ANY(:cosine_types)
              AND (analysis_id = :lid OR analysis_id IS NULL)
        """

    if not forced_sql and not cosine_sql:
        return []

    combined = []
    if forced_sql:
        combined.append(forced_sql)
    if cosine_sql:
        combined.append(cosine_sql)

    sql = f"""
        WITH combined AS (
            {" UNION ALL ".join(combined)}
        ),
        deduped AS (
            SELECT DISTINCT ON (chunk_id) *
            FROM combined
            ORDER BY chunk_id, forced DESC, sim DESC
        )
        SELECT * FROM deduped
        ORDER BY forced DESC, sim DESC
        LIMIT :limit
    """

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def _format_context_block(chunks: list[dict]) -> str:
    """LLM에 줄 컨텍스트. 각 청크 앞에 [N] 마커를 부여."""
    if not chunks:
        return "(분석 결과 컨텍스트가 비어 있습니다.)"
    lines = []
    for i, c in enumerate(chunks, start=1):
        meta_bits = []
        if c.get("attempt_index"):
            meta_bits.append(f"{c['attempt_index']}차 시도")
        if c.get("slide_id") is not None:
            meta_bits.append(f"슬라이드 {c['slide_id']}")
        meta = f" ({', '.join(meta_bits)})" if meta_bits else ""
        lines.append(f"[{i}]{meta} {c['content']}")
    return "\n".join(lines)


def _format_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(이전 대화 없음)"
    out = []
    for m in messages:
        role = "사용자" if m.role == "user" else "코치"
        content = (m.content or "").strip()
        if not content:
            continue
        out.append(f"{role}: {content[:300]}")
    return "\n".join(out)


SYSTEM_PROMPT = """당신은 SpeechPT의 발표 코치 챗봇입니다.

# 근거 규칙
- 제공된 "분석 컨텍스트" 블록 안의 사실만 사용해 답하세요. 추측이나 외부 지식을 끌어오지 마세요.
- 컨텍스트에 없는 내용은 "현재 분석 자료에는 그 정보가 없습니다"라고 솔직히 말하세요.
- 비교/지난번 관련 청크가 없을 때는 비교를 시도하지 마세요.
- 어떤 청크를 근거로 썼는지는 used_markers 배열에만 넣고, 본문(answer)에는 **절대 [1], [2] 같은 대괄호 마커를 쓰지 마세요**. 마커 표시·각주·괄호 인용 모두 금지. 인용은 used_markers 한 곳에서만.

# 표현 규칙
- 친근한 한국어 존댓말로, 슬라이드 번호와 수치 근거를 자연스럽게 본문에 녹여 쓰세요.
- 내부 분석 용어(pitch_shift, dwell, coverage, alignment confidence, semantic, threshold, probe 등)를 사용자에게 그대로 노출하지 마세요. 사용자 친화 표현으로 풀어 쓰세요.
- 답변 길이는 보통 3~6문장. 액션이 여러 개면 불릿으로 정리하세요.

# 마크다운 서식 규칙 (필수)
- 답변(answer)은 GitHub-flavored Markdown으로 작성하세요.
- 핵심 키워드·슬라이드 번호·점수 같은 강조 포인트는 **굵게** 표시.
- 행동 가이드·연습 항목·체크리스트는 `-` 불릿 또는 `1.` 번호 리스트로.
- 문단을 나눌 땐 빈 줄로 구분하세요.
- 짧은 답이면 굳이 리스트로 만들지 말고 자연스러운 한두 문단으로.
- 코드블록(```)이나 인라인 코드(`)는 사용하지 마세요. 표(table)도 가급적 피하세요.

# 출력 스키마 (필수)
반드시 아래 JSON 객체만 반환하세요. 코드블록·설명·머리말 금지.
{"answer": "<마크다운 본문. 대괄호 마커·각주 없이 자연스러운 문장만>",
 "used_markers": [1, 3]}
"""


USER_PROMPT_TEMPLATE = """=== 이전 대화 (직전 {history_turns}턴) ===
{history}

=== 분석 컨텍스트 ===
{context}

=== 사용자 질문 ===
{question}

위 컨텍스트만 근거로 답하고, 인용한 항목 번호를 used_markers에 정수 배열로 넣으세요.
"""


def _parse_markers(text_value: str) -> list[int]:
    return [int(m) for m in re.findall(r"\[(\d+)\]", text_value or "")]


def answer_question(
    db: Session,
    *,
    user_id: UUID,
    note_id: UUID,
    question: str,
    recent_messages: list[ChatMessage],
    top_k: int = DEFAULT_TOP_K,
) -> dict:
    """질문 → {answer, citations:list, used_chunk_ids:list, intent:str}.

    실패 시 OpenAIClientError 전파. 호출자가 fallback 메시지로 변환.
    """
    intent = classify_intent(question)
    latest_id = _latest_done_analysis_id(db, note_id, user_id)
    if latest_id is None:
        return {
            "answer": (
                "아직 완료된 분석 결과가 없습니다. 문서와 음성을 업로드해 분석을 먼저 실행해 주세요."
            ),
            "citations": [],
            "intent": intent.kind.value,
        }

    embedding = embed_texts([question])[0]
    chunks = _retrieve_chunks(
        db,
        user_id=user_id,
        note_id=note_id,
        latest_analysis_id=latest_id,
        question_embedding=embedding,
        intent=intent,
        top_k=top_k,
    )
    if not chunks:
        return {
            "answer": "분석 결과에서 관련 자료를 찾지 못했습니다. 다른 표현으로 다시 질문해 주세요.",
            "citations": [],
            "intent": intent.kind.value,
        }

    context_block = _format_context_block(chunks)
    history_block = _format_history(recent_messages[-MAX_HISTORY_TURNS:])
    user_prompt = USER_PROMPT_TEMPLATE.format(
        history_turns=MAX_HISTORY_TURNS,
        history=history_block,
        context=context_block,
        question=question.strip(),
    )

    try:
        resp = chat_responses_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_output_tokens=900,
            temperature=0.2,
        )
    except OpenAIClientError:
        raise

    raw_answer = (resp.get("answer") or "").strip()
    if not raw_answer:
        raw_answer = "답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."

    # used_markers는 LLM이 본문 cleanup 전에 갖고 있던 인용 의도이므로 먼저 추출
    markers_in_raw = set(_parse_markers(raw_answer))

    # 사용자에게 보이는 답변에서는 [N] 마커·각주를 안전망으로 제거 (시스템 프롬프트 무시 대비)
    answer_text = re.sub(r"\s*\[\d+\]", "", raw_answer).strip()

    markers = resp.get("used_markers")
    if not isinstance(markers, list):
        markers = list(markers_in_raw)
    valid_markers = []
    seen = set()
    for m in markers:
        try:
            n = int(m)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= len(chunks) and n not in seen:
            valid_markers.append(n)
            seen.add(n)
    # used_markers를 LLM이 부풀렸을 가능성: raw_answer에 [N]이 있었던 것 우선,
    # 없으면 used_markers 그대로 신뢰
    body_filtered = [m for m in valid_markers if m in markers_in_raw]
    if body_filtered:
        valid_markers = body_filtered

    citations = []
    for m in valid_markers:
        c = chunks[m - 1]
        citations.append(
            {
                "marker": m,
                "chunk_id": str(c["chunk_id"]),
                "chunk_type": c["chunk_type"],
                "slide_id": c.get("slide_id"),
                "start_sec": c.get("start_sec"),
                "end_sec": c.get("end_sec"),
                "attempt_index": c.get("attempt_index"),
            }
        )

    return {
        "answer": answer_text,
        "citations": citations,
        "intent": intent.kind.value,
    }


STREAM_SYSTEM_PROMPT = """당신은 SpeechPT의 발표 코치 챗봇입니다.

# 근거 규칙
- 제공된 "분석 컨텍스트" 블록 안의 사실만 사용해 답하세요. 추측이나 외부 지식을 끌어오지 마세요.
- 컨텍스트에 없는 내용은 "현재 분석 자료에는 그 정보가 없습니다"라고 솔직히 말하세요.
- 비교/지난번 관련 청크가 없을 때는 비교를 시도하지 마세요.
- 답변에 [1], [2] 같은 대괄호 마커·각주를 쓰지 마세요.

# 표현 규칙
- 친근한 한국어 존댓말로, 슬라이드 번호와 수치 근거를 자연스럽게 본문에 녹여 쓰세요.
- 내부 분석 용어(pitch_shift, dwell, coverage, alignment confidence, semantic, threshold, probe 등)를 사용자에게 그대로 노출하지 마세요. 사용자 친화 표현으로 풀어 쓰세요.
- 답변 길이는 보통 3~6문장. 액션이 여러 개면 불릿으로 정리하세요.

# 마크다운 서식 규칙 (필수)
- GitHub-flavored Markdown으로 작성하세요.
- 핵심 키워드·슬라이드 번호·점수 같은 강조 포인트는 **굵게** 표시.
- 행동 가이드·연습 항목·체크리스트는 `-` 불릿 또는 `1.` 번호 리스트로.
- 문단을 나눌 땐 빈 줄로 구분하세요.
- 짧은 답이면 굳이 리스트로 만들지 말고 자연스러운 한두 문단으로.
- 코드블록(```)이나 인라인 코드(`)는 사용하지 마세요.

마크다운 본문만 반환하세요. JSON 래퍼 없이 자연스럽게."""

_STREAM_USER_PROMPT_TEMPLATE = """=== 이전 대화 (직전 {history_turns}턴) ===
{history}

=== 분석 컨텍스트 ===
{context}

=== 사용자 질문 ===
{question}

위 컨텍스트만 근거로 마크다운 형식으로 자연스럽게 답변하세요."""


def prepare_rag_context(
    db: Session,
    *,
    user_id: UUID,
    note_id: UUID,
    question: str,
    recent_messages: list[ChatMessage],
    top_k: int = DEFAULT_TOP_K,
) -> dict | None:
    """임베딩+검색 단계만 실행하고 LLM 호출 없이 결과 반환.

    반환: {"user_prompt": str, "intent": str} 또는 None (분석 없음 / 청크 없음)
    """
    intent = classify_intent(question)
    latest_id = _latest_done_analysis_id(db, note_id, user_id)
    if latest_id is None:
        return None

    embedding = embed_texts([question])[0]
    chunks = _retrieve_chunks(
        db,
        user_id=user_id,
        note_id=note_id,
        latest_analysis_id=latest_id,
        question_embedding=embedding,
        intent=intent,
        top_k=top_k,
    )
    if not chunks:
        return None

    context_block = _format_context_block(chunks)
    history_block = _format_history(recent_messages[-MAX_HISTORY_TURNS:])
    user_prompt = _STREAM_USER_PROMPT_TEMPLATE.format(
        history_turns=MAX_HISTORY_TURNS,
        history=history_block,
        context=context_block,
        question=question.strip(),
    )

    return {
        "user_prompt": user_prompt,
        "intent": intent.kind.value,
        "chunks": chunks,
    }
