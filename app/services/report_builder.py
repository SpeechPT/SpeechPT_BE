"""모델 출력(STT/CE/AE raw 값) → UI 출력 데이터 변환 알고리즘."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────────────────────

# 한국어 발표의 적절한 말 속도 범위 (음절/초)
_RATE_MIN = 2.0
_RATE_MAX = 3.5

# 이상적 범위 벗어날 때 1음절/초당 감점 폭
_PACING_PENALTY_PER_UNIT = 25

# 섹션 점수 가중치: AE 전달력 60% + CE 내용 커버리지 40%
_SECTION_AE_WEIGHT = 0.6
_SECTION_CE_WEIGHT = 0.4

# AE 피드백 임계값
_ENERGY_DROP_THRESHOLD = 0.6
_PITCH_SHIFT_THRESHOLD = 0.6


# ──────────────────────────────────────────────────────────────
# 1. 점수 계산
# ──────────────────────────────────────────────────────────────

def calc_content_coverage(ce_result: Dict[str, Any]) -> int:
    """CE 출력의 coverage(0~1) → 0~100 정수 점수.

    CE 모델은 슬라이드 키포인트 전체 중 발화에서 언급된 비율을
    0~1 실수로 반환한다. 100을 곱해 점수로 사용한다.

    예) coverage=0.75 → 75점
    """
    raw = float(ce_result.get("coverage", 0.0))
    return max(0, min(100, int(round(raw * 100))))


def calc_delivery_stability(ae_segments: List[Dict[str, Any]]) -> int:
    """AE 구간별 overall_delivery 평균 → 0~100 정수 점수.

    overall_delivery는 AE 모델이 해당 구간의 전달력을 0~1로 평가한 값.
    모든 구간의 평균을 내어 전체 전달 안정성 점수로 사용한다.

    예) [0.9, 0.7, 0.8] 평균 0.8 → 80점
    """
    valid = [s for s in ae_segments if s.get("scores")]
    if not valid:
        return 50
    avg = sum(s["scores"]["overall_delivery"] for s in valid) / len(valid)
    return max(0, min(100, int(round(avg * 100))))


def calc_pacing_score(ae_segments: List[Dict[str, Any]]) -> Tuple[int, float]:
    """AE 구간별 speech_rate 평균이 적절한 범위에서 얼마나 벗어났는지 점수화.

    이상적 범위(2.0~3.5 음절/초) 안이면 감점 없음.
    범위를 벗어나면 1음절/초당 25점씩 감점한다.

    예) avg_rate=4.0 → 범위 초과 0.5 → 100 - 0.5*25 = 87.5 → 88점
        avg_rate=1.0 → 범위 미달 1.0 → 100 - 1.0*25 = 75점

    Returns:
        (pacing_score, avg_rate) — avg_rate는 개선점 문구 생성에 재사용
    """
    valid = [s for s in ae_segments if s.get("scores")]
    if not valid:
        return 50, 2.5

    avg_rate = sum(s["scores"]["speech_rate"] for s in valid) / len(valid)

    if _RATE_MIN <= avg_rate <= _RATE_MAX:
        deviation = 0.0
    elif avg_rate < _RATE_MIN:
        deviation = _RATE_MIN - avg_rate
    else:
        deviation = avg_rate - _RATE_MAX

    score = max(0, min(100, int(round(100 - deviation * _PACING_PENALTY_PER_UNIT))))
    return score, avg_rate


# ──────────────────────────────────────────────────────────────
# 2. 섹션 피드백 생성
# ──────────────────────────────────────────────────────────────

def _per_slide_ce_coverage(
    slides: List[Dict[str, Any]],
    covered_mask: List[bool],
) -> List[Optional[float]]:
    """covered_mask(키포인트 단위 flat 리스트)를 슬라이드별 커버리지 비율로 분해.

    CE 모델은 모든 슬라이드의 키포인트를 하나의 flat 리스트로 받고
    키포인트마다 커버 여부(True/False)를 반환한다.
    슬라이드별 키포인트 개수를 추적해서 마스크를 잘라 비율을 계산한다.

    예) 슬라이드1 키포인트 3개, 슬라이드2 키포인트 2개
        covered_mask = [T, F, T,  T, F]
                        ─── 슬1 ───  ─슬2─
        → 슬라이드1: 2/3=0.67,  슬라이드2: 1/2=0.5
    """
    result: List[Optional[float]] = []
    offset = 0
    for slide in slides:
        n = len(slide.get("keypoints", []))
        if n == 0 or offset >= len(covered_mask):
            result.append(None)
            continue
        slide_mask = covered_mask[offset: offset + n]
        result.append(sum(1 for v in slide_mask if v) / n)
        offset += n
    return result


def _make_section_feedback(ae_scores: Dict[str, Any], ce_coverage: Optional[float]) -> str:
    """AE 수치 + CE 슬라이드 커버리지 → 피드백 문장.

    각 지표가 임계값을 초과하면 이슈 목록에 추가한다.
    이슈가 없으면 '안정적인 발화'를 반환한다.

    AE 기반:
      energy_drop_prob >= 0.6  → 에너지 저하 언급
      pitch_shift_prob >= 0.6  → 피치 불안정 언급
      speech_rate > 3.5        → 말 속도 빠름
      speech_rate < 1.5        → 말 속도 느림

    CE 기반:
      슬라이드 커버리지 < 50%  → 내용 언급 부족 경고
    """
    issues = []

    if ae_scores.get("energy_drop_prob", 0) >= _ENERGY_DROP_THRESHOLD:
        issues.append("발화 에너지가 떨어지는 구간 있음")

    if ae_scores.get("pitch_shift_prob", 0) >= _PITCH_SHIFT_THRESHOLD:
        issues.append("피치 불안정")

    sr = ae_scores.get("speech_rate", 0)
    if sr > _RATE_MAX:
        issues.append(f"말 속도 빠름({sr:.1f}음절/초)")
    elif sr < 1.5:
        issues.append(f"말 속도 느림({sr:.1f}음절/초)")

    if ce_coverage is not None and ce_coverage < 0.5:
        issues.append(f"슬라이드 내용 {int(round(ce_coverage * 100))}%만 언급")

    return "、".join(issues) if issues else "안정적인 발화"


def _calc_section_score(ae_scores: Dict[str, Any], ce_coverage: Optional[float]) -> int:
    """섹션 점수 = AE 전달력(60%) + CE 슬라이드 커버리지(40%) 가중 평균.

    CE 데이터가 없으면 AE 점수만 사용한다.
    """
    ae_score = max(0, min(100, int(round(ae_scores.get("overall_delivery", 0.5) * 100))))
    if ce_coverage is not None:
        ce_score = int(round(ce_coverage * 100))
        return int(round(ae_score * _SECTION_AE_WEIGHT + ce_score * _SECTION_CE_WEIGHT))
    return ae_score


def build_sections(
    slides: List[Dict[str, Any]],
    ae_segments: List[Dict[str, Any]],
    ce_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """슬라이드 메타 + AE 구간 점수 + CE 커버리지 → 섹션 목록.

    슬라이드 순서와 AE segment 순서가 1:1 대응한다고 가정한다.
    """
    covered_mask: List[bool] = ce_result.get("covered_mask", [])
    per_slide_coverage = _per_slide_ce_coverage(slides, covered_mask)

    sections = []
    for i, slide in enumerate(slides):
        ae_seg = ae_segments[i] if i < len(ae_segments) else {}
        ae_scores = ae_seg.get("scores")
        ce_cov = per_slide_coverage[i] if i < len(per_slide_coverage) else None

        if ae_scores:
            score = _calc_section_score(ae_scores, ce_cov)
            feedback = _make_section_feedback(ae_scores, ce_cov)
        else:
            score = 50
            feedback = "분석 데이터 부족"

        sections.append({
            "section_index": i + 1,
            "title": slide.get("title", f"슬라이드 {i + 1}"),
            "start_time_sec": int(ae_seg.get("start_sec", 0)),
            "end_time_sec": int(ae_seg.get("end_sec", 0)),
            "score": score,
            "feedback": feedback,
        })
    return sections


# ──────────────────────────────────────────────────────────────
# 3. 강점 / 개선점 생성
# ──────────────────────────────────────────────────────────────

def build_strengths_and_improvements(
    content_coverage: int,
    delivery_stability: int,
    pacing_score: int,
    avg_rate: float,
    sections: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """3개 점수 + 섹션 데이터 → 강점/개선점 목록.

    점수 구간별 규칙:
      >= 80  → 강점으로 분류
      60~79  → 약한 개선점
      < 60   → 개선점으로 분류

    추가로 섹션 중 최고/최저 구간을 각각 강점/개선점에 언급한다.
    """
    strengths: List[Dict[str, str]] = []
    improvements: List[Dict[str, str]] = []

    # ── 내용 커버리지 ──────────────────────────────────────────
    if content_coverage >= 80:
        strengths.append({
            "text": f"슬라이드 핵심 내용의 {content_coverage}%를 발화에서 다뤄 내용 전달력이 우수합니다."
        })
    elif content_coverage >= 60:
        improvements.append({
            "text": (f"슬라이드 내용의 {100 - content_coverage}%가 발화에서 충분히 다뤄지지 않았습니다. "
                     "키포인트를 더 의식적으로 언급해보세요.")
        })
    else:
        improvements.append({
            "text": (f"슬라이드 내용 커버리지가 {content_coverage}%로 낮습니다. "
                     "발표 시 슬라이드 핵심 내용을 더 많이 언급해야 합니다.")
        })

    # ── 전달 안정성 ────────────────────────────────────────────
    if delivery_stability >= 80:
        strengths.append({
            "text": "발화 에너지와 피치가 전반적으로 안정적으로 유지됐습니다."
        })
    elif delivery_stability >= 60:
        improvements.append({
            "text": "일부 구간에서 발화 에너지가 떨어졌습니다. 발표 후반부에도 목소리 크기를 일정하게 유지하세요."
        })
    else:
        improvements.append({
            "text": "발화 안정성이 낮습니다. 호흡 조절 연습과 반복 연습이 필요합니다."
        })

    # ── 발표 속도 ──────────────────────────────────────────────
    if pacing_score >= 80:
        strengths.append({
            "text": f"발표 속도({avg_rate:.1f}음절/초)가 청중이 이해하기 적절한 수준으로 유지됐습니다."
        })
    elif avg_rate > _RATE_MAX:
        improvements.append({
            "text": (f"평균 말 속도가 {avg_rate:.1f}음절/초로 다소 빠릅니다. "
                     "청중이 따라오기 어려울 수 있으니 의도적으로 속도를 늦춰보세요.")
        })
    else:
        improvements.append({
            "text": (f"평균 말 속도가 {avg_rate:.1f}음절/초로 다소 느립니다. "
                     "좀 더 자신감 있는 발화 속도를 목표로 연습하세요.")
        })

    # ── 최고 / 최저 섹션 ───────────────────────────────────────
    if sections:
        best = max(sections, key=lambda s: s["score"])
        worst = min(sections, key=lambda s: s["score"])

        if best["score"] >= 75:
            strengths.append({
                "text": f"'{best['title']}' 구간({best['section_index']}번)에서 가장 안정적인 발표를 보였습니다."
            })

        # 최저 구간은 최고 구간과 다를 때만 언급 (모든 구간이 같은 점수일 때 방지)
        if worst["score"] < 60 and worst["section_index"] != best["section_index"]:
            improvements.append({
                "text": (f"'{worst['title']}' 구간({worst['section_index']}번)에서 발표 품질이 "
                         f"가장 낮았습니다({worst['score']}점). 해당 부분을 집중 연습하세요.")
            })

    return strengths, improvements


# ──────────────────────────────────────────────────────────────
# 4. 요약 생성
# ──────────────────────────────────────────────────────────────

def build_summary(
    overall_score: int,
    content_coverage: int,
    delivery_stability: int,
    pacing_score: int,
    slide_count: int,
) -> str:
    """전체 점수 구간으로 등급을 결정하고 한 문단 요약을 생성.

    구간별 등급:
      >= 80 : 우수
      >= 65 : 양호
      <  65 : 개선 필요

    세 점수를 나열하고 등급에 맞는 조언 문장으로 마무리한다.
    """
    if overall_score >= 80:
        grade = "우수한"
        advice = "현재 수준을 유지하며 섹션별 피드백으로 세부 개선점을 다듬으면 더욱 완성도 있는 발표가 됩니다."
    elif overall_score >= 65:
        grade = "양호한"
        advice = "개선점을 참고해 약한 부분을 보완하면 발표 품질이 크게 향상됩니다."
    else:
        grade = "개선이 필요한"
        advice = "섹션별 피드백을 참고해 각 슬라이드를 집중 연습해보세요."

    return (
        f"총 {slide_count}개 슬라이드, 전체 {overall_score}점으로 {grade} 발표입니다. "
        f"내용 커버리지 {content_coverage}점 / 전달 안정성 {delivery_stability}점 / 발표 속도 {pacing_score}점. "
        f"{advice}"
    )


# ──────────────────────────────────────────────────────────────
# 5. 통합 빌더 — 외부에서 이 함수 하나만 호출하면 됨
# ──────────────────────────────────────────────────────────────

def build_report(
    transcript: str,
    ce_result: Dict[str, Any],
    ae_result: Dict[str, Any],
    slides: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """STT/CE/AE 모델 raw 출력 → DB 저장 형식으로 변환.

    Args:
        transcript : STT 모델이 반환한 전체 대본 텍스트
        ce_result  : CE 모델 출력 {"coverage": float, "covered_mask": [bool, ...]}
        ae_result  : AE 모델 출력 {"segments": [{slide_id, start_sec, end_sec, scores}, ...]}
        slides     : 문서 파싱 결과 [{slide_id, title, keypoints, full_text}, ...]

    Returns:
        {
            "scores":   {content_coverage, delivery_stability, pacing_score, overall_score},
            "severity": {high/medium/low_severity_count},
            "report":   {summary, strengths, improvements, sections, transcript},
        }
    """
    ae_segments = ae_result.get("segments", [])

    # 1단계: 점수 계산
    content_coverage = calc_content_coverage(ce_result)
    delivery_stability = calc_delivery_stability(ae_segments)
    pacing_score, avg_rate = calc_pacing_score(ae_segments)
    overall_score = int(round((content_coverage + delivery_stability + pacing_score) / 3))

    # 2단계: 슬라이드별 섹션 피드백
    sections = build_sections(slides, ae_segments, ce_result)

    # 3단계: 강점 / 개선점
    strengths, improvements = build_strengths_and_improvements(
        content_coverage, delivery_stability, pacing_score, avg_rate, sections
    )

    # 4단계: 전체 요약 문단
    summary = build_summary(
        overall_score, content_coverage, delivery_stability, pacing_score, len(slides)
    )

    # 5단계: 심각도 통계 (섹션 점수 기준)
    severity = {
        "high_severity_count":   sum(1 for s in sections if s["score"] < 50),
        "medium_severity_count": sum(1 for s in sections if 50 <= s["score"] < 70),
        "low_severity_count":    sum(1 for s in sections if s["score"] >= 70),
    }

    return {
        "scores": {
            "content_coverage":   content_coverage,
            "delivery_stability": delivery_stability,
            "pacing_score":       pacing_score,
            "overall_score":      overall_score,
        },
        "severity": severity,
        "report": {
            "summary":      summary,
            "strengths":    strengths,
            "improvements": improvements,
            "sections":     sections,
            "transcript":   transcript[:5000],
        },
    }
