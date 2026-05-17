"""모델 report.json → DB 저장 형식 변환.

모델이 이미 모든 점수와 LLM 피드백을 계산하므로,
이 모듈은 값을 재계산하지 않고 모델 출력을 그대로 DB 스키마에 맞게 매핑한다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_report_from_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    """모델 report.json dict → DB 저장 형식.

    Args:
        payload: AnalysisSubmitRequest.model_dump() 결과
                 (overall_scores, per_slide_detail, llm_feedback,
                  alignment, transcript_segments, highlight_sections)

    Returns:
        {
            "transcript": str,
            "scores":   {content_coverage, delivery_stability, pacing_score, overall_score},
            "severity": {high/medium/low_severity_count},
            "report":   {summary, strengths, improvements, sections},
        }
    """
    overall_scores = payload["overall_scores"]
    per_slide_detail: List[Dict] = payload.get("per_slide_detail") or []
    llm_feedback: Dict = payload.get("llm_feedback") or {}
    alignment: Dict = payload.get("alignment") or {}
    transcript_segments: List[Dict] = payload.get("transcript_segments") or []
    highlight_sections: List[Dict] = payload.get("highlight_sections") or []
    reliability: Optional[Dict] = payload.get("reliability")

    # ── 점수: content_coverage_user 우선, 없으면 raw content_coverage ──
    raw_cc = overall_scores["content_coverage"]
    user_cc = overall_scores.get("content_coverage_user")
    content_coverage = round(user_cc if user_cc is not None else raw_cc)
    delivery_stability = round(overall_scores["delivery_stability"])
    pacing_score = round(overall_scores["pacing_score"])
    overall_score = round((content_coverage + delivery_stability + pacing_score) / 3)

    # ── 대본: transcript_segments의 text를 슬라이드 순서로 합침 ──
    transcript = " ".join(seg["text"] for seg in transcript_segments if seg.get("text"))

    # ── 룩업 맵 ────────────────────────────────────────────────
    boundaries: List[float] = alignment.get("final_boundaries") or []
    highlight_map: Dict[int, Dict] = {h["slide_id"]: h for h in highlight_sections}
    slide_comment_map: Dict[int, str] = {
        sc["slide_id"]: sc["comment"]
        for sc in llm_feedback.get("slide_comments") or []
    }

    # ── 섹션 목록 ───────────────────────────────────────────────
    sections: List[Dict] = []
    for i, slide in enumerate(per_slide_detail):
        slide_id = slide["slide_id"]

        # 시간 경계
        start_sec = boundaries[i] if i < len(boundaries) else 0.0
        end_sec = boundaries[i + 1] if (i + 1) < len(boundaries) else start_sec

        # 섹션 점수: AE probe 전달력(60%) + CE 슬라이드 커버리지(40%)
        ae_probe = slide.get("ae_probe") or {}
        ae_delivery = ae_probe.get("ae_probe_overall_delivery", 0.5)
        coverage = slide.get("coverage", 0.0)
        section_score = max(0, min(100, round((ae_delivery * 100 + coverage * 100) / 2)))

        # 섹션 피드백: LLM slide_comment > highlight feedback > missed keypoints
        feedback = slide_comment_map.get(slide_id, "")
        if not feedback:
            hl = highlight_map.get(slide_id)
            if hl:
                fb_texts = [f["text"] for f in (hl.get("feedback") or []) if f.get("text")]
                feedback = " ".join(fb_texts)
        if not feedback:
            missed = slide.get("missed") or []
            if missed:
                feedback = f"미언급 키포인트: {', '.join(missed[:3])}"
            else:
                feedback = "안정적인 발화"

        sections.append({
            "section_index": i + 1,
            "title": f"슬라이드 {slide_id}",
            "start_time_sec": int(start_sec),
            "end_time_sec": int(end_sec),
            "score": section_score,
            "feedback": feedback,
        })

    # ── 요약: 모델 LLM overall_comment 직접 사용 ───────────────
    summary = llm_feedback.get("overall_comment", "")

    # ── 강점: 모델 LLM strengths 직접 사용 ────────────────────
    strengths = [
        {"text": s} if isinstance(s, str) else s
        for s in (llm_feedback.get("strengths") or [])
    ]

    # ── 개선점: 모델 LLM priority_actions 직접 사용 ────────────
    improvements = [
        {"text": a} if isinstance(a, str) else a
        for a in (llm_feedback.get("priority_actions") or [])
    ]

    # ── 심각도: highlight_sections severity 집계 ───────────────
    sev_count: Dict[str, int] = {}
    for hl in highlight_sections:
        sev = hl.get("severity", "low")
        sev_count[sev] = sev_count.get(sev, 0) + 1

    severity = {
        "high_severity_count":   sev_count.get("high", 0),
        "medium_severity_count": sev_count.get("medium", 0),
        "low_severity_count":    sev_count.get("low", 0),
    }

    return {
        "transcript": transcript,
        "scores": {
            "content_coverage_user": content_coverage,
            "delivery_stability":    delivery_stability,
            "pacing_score":          pacing_score,
            "overall_score":         overall_score,
        },
        "severity": severity,
        "report": {
            "summary":      summary,
            "strengths":    strengths,
            "improvements": improvements,
            "sections":     sections,
            "reliability":  reliability,
        },
    }
