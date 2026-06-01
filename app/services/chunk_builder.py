"""분석 결과 → RAG 청크 변환.

7종 청크: slide_text, transcript_segment, feedback_slide, feedback_overall,
metric, practice_plan, progress_delta.

각 청크는:
- content: 임베딩 / LLM 컨텍스트에 들어갈 자연어 본문 (헤더 포함)
- chunk_key: analysis 내(또는 note 내) 고유 식별자 (UNIQUE 키 일부)
- metadata: 추가 구조화 정보 (severity, score 등)

progress_delta는 deterministic — LLM 호출 없이 metric 비교로 생성.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Chunk:
    chunk_type: str
    chunk_key: str
    content: str
    slide_id: Optional[int] = None
    start_sec: Optional[int] = None
    end_sec: Optional[int] = None
    is_note_scoped: bool = False  # True면 analysis_id=NULL로 저장
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


def _trim(text: str, max_len: int = 1200) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def build_slide_text_chunks(payload: dict) -> list[Chunk]:
    """슬라이드 정적 정보 (제목 + 발화 미포함). note 공유.

    현재 모델 출력에는 slide title/bullets/visual_caption이 직접 노출되지 않아,
    per_slide_detail의 slide_role과 missed 키포인트로 대체. PDF 파싱 확장 시 보강.
    """
    chunks: list[Chunk] = []
    per_slide = payload.get("per_slide_detail") or []
    for slide in per_slide:
        slide_id = slide.get("slide_id")
        if slide_id is None:
            continue
        role = slide.get("slide_role") or ""
        missed = slide.get("missed") or []
        lines = [f"슬라이드 {slide_id}"]
        if role:
            lines.append(f"역할: {role}")
        if missed:
            lines.append("주요 키포인트: " + ", ".join(missed[:6]))
        content = "\n".join(lines)
        chunks.append(
            Chunk(
                chunk_type="slide_text",
                chunk_key=f"slide:{slide_id}",
                content=content,
                slide_id=int(slide_id),
                is_note_scoped=True,
                metadata={"role": role, "keypoints": missed[:6]},
            )
        )
    return chunks


def build_transcript_chunks(payload: dict) -> list[Chunk]:
    chunks: list[Chunk] = []
    segments = payload.get("transcript_segments") or []
    by_slide: dict[int, list[dict]] = {}
    for seg in segments:
        sid = seg.get("slide_id")
        if sid is None:
            continue
        by_slide.setdefault(int(sid), []).append(seg)
    for slide_id, segs in by_slide.items():
        text = " ".join((s.get("text") or "").strip() for s in segs).strip()
        if not text:
            continue
        start = int(min(s.get("start_sec") or 0 for s in segs))
        end = int(max(s.get("end_sec") or 0 for s in segs))
        mmss = f"{start//60:02d}:{start%60:02d}-{end//60:02d}:{end%60:02d}"
        content = f"슬라이드 {slide_id} ({mmss}) 발화: {_trim(text, 800)}"
        chunks.append(
            Chunk(
                chunk_type="transcript_segment",
                chunk_key=f"slide:{slide_id}",
                content=content,
                slide_id=slide_id,
                start_sec=start,
                end_sec=end,
            )
        )
    return chunks


def build_feedback_slide_chunks(payload: dict) -> list[Chunk]:
    chunks: list[Chunk] = []
    llm = payload.get("llm_feedback") or {}
    slide_comments = llm.get("slide_comments") or []
    highlight_map = {h["slide_id"]: h for h in (payload.get("highlight_sections") or []) if "slide_id" in h}

    for item in slide_comments:
        slide_id = item.get("slide_id")
        comment = (item.get("comment") or "").strip()
        if slide_id is None or not comment:
            continue
        hl = highlight_map.get(slide_id) or {}
        severity = hl.get("severity") or "low"
        issues = hl.get("issues") or []
        content = f"슬라이드 {slide_id} 코칭 (심각도 {severity}): {_trim(comment, 600)}"
        chunks.append(
            Chunk(
                chunk_type="feedback_slide",
                chunk_key=f"slide:{slide_id}",
                content=content,
                slide_id=int(slide_id),
                metadata={"severity": severity, "issues": issues},
            )
        )
    return chunks


def build_overall_feedback_chunks(payload: dict) -> list[Chunk]:
    chunks: list[Chunk] = []
    llm = payload.get("llm_feedback") or {}

    overall = (llm.get("overall_comment") or "").strip()
    if overall:
        chunks.append(
            Chunk(
                chunk_type="feedback_overall",
                chunk_key="summary",
                content=f"전체 요약: {_trim(overall, 800)}",
            )
        )

    for i, s in enumerate(llm.get("strengths") or []):
        text = s if isinstance(s, str) else (s.get("text") if isinstance(s, dict) else "")
        text = (text or "").strip()
        if not text:
            continue
        chunks.append(
            Chunk(
                chunk_type="feedback_overall",
                chunk_key=f"strength:{i}",
                content=f"강점: {_trim(text, 400)}",
            )
        )

    for i, a in enumerate(llm.get("priority_actions") or []):
        text = a if isinstance(a, str) else (a.get("text") if isinstance(a, dict) else "")
        text = (text or "").strip()
        if not text:
            continue
        chunks.append(
            Chunk(
                chunk_type="feedback_overall",
                chunk_key=f"priority_action:{i}",
                content=f"우선 개선 액션: {_trim(text, 400)}",
            )
        )

    return chunks


def build_metric_chunk(payload: dict, attempt_index: int) -> Optional[Chunk]:
    scores = payload.get("overall_scores") or {}
    cc = scores.get("content_coverage_user")
    if cc is None:
        cc = scores.get("content_coverage")
    ds = scores.get("delivery_stability")
    ps = scores.get("pacing_score")
    if cc is None or ds is None or ps is None:
        return None
    reliability = (payload.get("reliability") or {}).get("alignment_level", "unknown")
    cc_i, ds_i, ps_i = round(cc), round(ds), round(ps)
    overall = round((cc_i + ds_i + ps_i) / 3)
    content = (
        f"{attempt_index}차 시도 점수: 내용 연결 {cc_i}점, 전달 안정성 {ds_i}점, "
        f"발표 속도 {ps_i}점, 종합 {overall}점, 분석 신뢰도 {reliability}"
    )
    return Chunk(
        chunk_type="metric",
        chunk_key="scores",
        content=content,
        metadata={
            "attempt_index": attempt_index,
            "content_coverage": cc_i,
            "delivery_stability": ds_i,
            "pacing_score": ps_i,
            "overall": overall,
            "reliability": reliability,
        },
    )


def build_practice_plan_chunks(payload: dict) -> list[Chunk]:
    """priority_actions를 practice_plan으로도 노출 (별도 인덱싱 키)."""
    chunks: list[Chunk] = []
    llm = payload.get("llm_feedback") or {}
    actions = llm.get("priority_actions") or []
    if not actions:
        return chunks
    lines = []
    for i, a in enumerate(actions, start=1):
        text = a if isinstance(a, str) else (a.get("text") if isinstance(a, dict) else "")
        text = (text or "").strip()
        if not text:
            continue
        lines.append(f"{i}. {text}")
    if not lines:
        return chunks
    body = "\n".join(lines)
    chunks.append(
        Chunk(
            chunk_type="practice_plan",
            chunk_key="next_recording",
            content=f"다음 녹음 연습 계획:\n{_trim(body, 1000)}",
        )
    )
    return chunks


def build_progress_delta_chunk(
    prev_metric_meta: dict, this_metric_meta: dict, *, prev_attempt: int, this_attempt: int
) -> Optional[Chunk]:
    """결정적 metric diff. LLM 호출 없음."""
    if not prev_metric_meta or not this_metric_meta:
        return None
    keys = [
        ("content_coverage", "내용 연결"),
        ("delivery_stability", "전달 안정성"),
        ("pacing_score", "발표 속도"),
        ("overall", "종합"),
    ]
    diffs = []
    for k, label in keys:
        prev = prev_metric_meta.get(k)
        cur = this_metric_meta.get(k)
        if prev is None or cur is None:
            continue
        delta = cur - prev
        sign = "+" if delta > 0 else ("" if delta == 0 else "")
        diffs.append(f"{label} {sign}{delta}점({prev}→{cur})")
    if not diffs:
        return None
    content = f"{prev_attempt}차→{this_attempt}차 변화: " + ", ".join(diffs)
    return Chunk(
        chunk_type="progress_delta",
        chunk_key=f"vs:{prev_attempt}",
        content=content,
        metadata={
            "prev_attempt": prev_attempt,
            "this_attempt": this_attempt,
            "diffs": {k: this_metric_meta.get(k, 0) - prev_metric_meta.get(k, 0) for k, _ in keys},
        },
    )


def build_all_chunks(payload: dict, attempt_index: int) -> list[Chunk]:
    """progress_delta 제외한 전체 청크. progress_delta는 호출자가 metric 비교 후 별도 추가."""
    chunks: list[Chunk] = []
    chunks.extend(build_slide_text_chunks(payload))
    chunks.extend(build_transcript_chunks(payload))
    chunks.extend(build_feedback_slide_chunks(payload))
    chunks.extend(build_overall_feedback_chunks(payload))
    metric = build_metric_chunk(payload, attempt_index)
    if metric is not None:
        chunks.append(metric)
    chunks.extend(build_practice_plan_chunks(payload))
    return chunks
