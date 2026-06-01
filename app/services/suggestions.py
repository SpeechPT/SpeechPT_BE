"""챗 추천 질문 생성.

정적 4 + 분석 결과 기반 동적 0~3 = 4~7개.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.analysis_result import AnalysisResult


_STATIC_SUGGESTIONS = [
    {"key": "improvements", "question": "이번 발표에서 개선이 가장 필요한 부분은 어디인가요?"},
    {"key": "stability", "question": "전달 안정성을 더 끌어올리려면 어떻게 연습해야 하나요?"},
    {"key": "pacing", "question": "발표 속도가 적절했나요? 더 다듬을 부분이 있을까요?"},
    {"key": "slide_feedback", "question": "슬라이드별 피드백을 자세히 알려주세요."},
]


def build_suggestions(db: Session, *, user_id: UUID, note_id: UUID) -> list[dict]:
    items = list(_STATIC_SUGGESTIONS)

    latest = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc().nullslast(), Analysis.created_at.desc())
        .first()
    )
    if latest is None:
        return items

    result: AnalysisResult | None = latest.result
    if result is None:
        return items

    severity = result.severity_json or {}
    if severity.get("high_severity_count", 0) > 0:
        # 가장 심각도 높은 슬라이드를 찾아 동적 질문 1개 생성
        report = result.report_json or {}
        sections = report.get("sections") or []
        top_section = None
        for sec in sections:
            if sec.get("score", 100) <= 60:
                top_section = sec
                break
        if top_section:
            items.append(
                {
                    "key": "top_issue_slide",
                    "question": f"{top_section.get('title', '해당 슬라이드')}에서 가장 큰 문제는 무엇이고 어떻게 고쳐야 하나요?",
                }
            )

    attempt_count = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == user_id,
            Analysis.status == "done",
        )
        .count()
    )
    if attempt_count >= 2:
        items.append(
            {
                "key": "progress",
                "question": "지난 시도와 비교했을 때 어떤 부분이 달라졌나요?",
            }
        )

    # 최저 점수 축 기반 동적 질문
    axes = [
        ("내용 연결", result.content_coverage),
        ("전달 안정성", result.delivery_stability),
        ("발표 속도", result.pacing_score),
    ]
    weakest = min(axes, key=lambda x: x[1])
    if weakest[1] < 70:
        items.append(
            {
                "key": "weakest_axis",
                "question": f"{weakest[0]} 점수가 낮게 나온 구간은 어디였나요?",
            }
        )

    return items
