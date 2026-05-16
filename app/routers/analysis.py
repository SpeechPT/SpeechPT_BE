"""분석 트리거 + 상태/결과 조회 라우터.

흐름:
1. POST /notes/{note_id}/analyses
   - analyses 테이블에 status=queued로 INSERT
   - analysis_inputs 테이블에 S3 키 저장
   - SQS에 작업 메시지 enqueue
   - 즉시 응답 (Worker가 백그라운드 처리)

2. GET /analyses/{analysis_id}/status
   - analyses 테이블 조회 → progress, stage 반환

3. GET /analyses/{analysis_id}/result
   - status=done이면 analysis_results 테이블에서 점수+report 로드
   - 아니면 is_ready=False
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.sqs import enqueue_analysis
from app.db import get_db
from app.models.analysis import Analysis
from app.models.analysis_input import AnalysisInput
from app.models.analysis_result import AnalysisResult
from app.models.analysis_section import AnalysisSection
from app.models.note import Note
from app.models.upload import Upload
from app.models.user import User
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisResultResponse,
    AnalysisStatusResponse,
    AnalysisSubmitRequest,
)
from app.services.report_builder import build_report_from_model

router = APIRouter(tags=["analyses"])


@router.post(
    "/notes/{note_id}/analyses",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis(
    note_id: UUID,
    payload: AnalysisCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ── 1. 노트 소유 검증 ─────────────────────────────────────
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == current_user.user_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노트를 찾을 수 없습니다.")

    if payload.document_upload_id is None or payload.audio_upload_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석을 위해서는 문서와 음성 파일이 모두 필요합니다.",
        )

    # ── 2. 업로드 검증 ────────────────────────────────────────
    document_upload = (
        db.query(Upload)
        .filter(
            Upload.upload_id == payload.document_upload_id,
            Upload.user_id == current_user.user_id,
            Upload.note_id == note_id,
        )
        .first()
    )
    if document_upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서 업로드 정보를 찾을 수 없습니다.")
    if document_upload.status != "uploaded":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="문서 파일 업로드가 아직 완료되지 않았습니다.")

    audio_upload = (
        db.query(Upload)
        .filter(
            Upload.upload_id == payload.audio_upload_id,
            Upload.user_id == current_user.user_id,
            Upload.note_id == note_id,
        )
        .first()
    )
    if audio_upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="음성 업로드 정보를 찾을 수 없습니다.")
    if audio_upload.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="음성 파일 업로드가 아직 완료되지 않았습니다.",
        )

    # ── 3. analyses 행 INSERT (status=queued) ────────────────
    analysis = Analysis(
        note_id=note_id,
        user_id=current_user.user_id,
        document_upload_id=payload.document_upload_id,
        audio_upload_id=payload.audio_upload_id,
        pipeline_version=payload.pipeline_version,
        model_version_ce=payload.model_version_ce,
        model_version_ae=payload.model_version_ae,
        status="queued",
        progress=0,
        stage="ingest",
        trigger_type="manual",
        worker_id=None,
        error_code=None,
        error_message=None,
        started_at=None,
        finished_at=None,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # ── 4. analysis_inputs 행 INSERT ──────────────────────────
    analysis_input = AnalysisInput(
        analysis_id=analysis.analysis_id,
        document_path=_storage_uri(document_upload),
        audio_path=_storage_uri(audio_upload),
    )
    db.add(analysis_input)
    db.commit()

    # ── 5. SQS enqueue ────────────────────────────────────────
    try:
        enqueue_analysis({
            "analysis_id": str(analysis.analysis_id),
            "user_id": str(current_user.user_id),
            "note_id": str(note_id),
            "document": {
                "storage": document_upload.storage,
                "bucket": document_upload.bucket,
                "object_key": document_upload.object_key,
                "filename": document_upload.original_filename,
            },
            "audio": {
                "storage": audio_upload.storage,
                "bucket": audio_upload.bucket,
                "object_key": audio_upload.object_key,
                "filename": audio_upload.original_filename,
            },
            "pipeline_version": payload.pipeline_version,
            "model_version_ce": payload.model_version_ce,
            "model_version_ae": payload.model_version_ae,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        # 큐 enqueue 실패 시 분석을 failed로 마킹
        analysis.status = "failed"
        analysis.error_code = "ENQUEUE_FAILED"
        analysis.error_message = str(exc)[:500]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"분석 작업 큐 등록에 실패했습니다: {exc}",
        )

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "progress": analysis.progress,
        "stage": analysis.stage,
    }


def _storage_uri(upload: Upload) -> str:
    """Upload의 위치를 단일 문자열로 표현."""
    if upload.storage == "s3":
        return f"s3://{upload.bucket}/{upload.object_key}"
    return upload.url or upload.object_key


def _build_result_payload(analysis: Analysis, result_row: AnalysisResult, document_upload: Upload | None) -> dict:
    """분석 결과 응답 dict를 생성하는 공통 헬퍼.

    - 점수: analysis_results 테이블 컬럼
    - summary/strengths/improvements: analysis_results.report_json
    - sections: analysis_sections 테이블 (정규화 저장) → 없으면 report_json fallback
    """
    report = result_row.report_json or {}

    # analysis_sections 테이블에서 섹션 읽기 (order_index 순 정렬은 모델 relationship에서 보장)
    sections = [
        {
            "section_index": sec.order_index,
            "title": sec.title,
            "start_time_sec": sec.start_time_sec or 0,
            "end_time_sec": sec.end_time_sec or 0,
            "score": (sec.score_json or {}).get("score", 0),
            "feedback": (sec.feedback_json or {}).get("text", ""),
        }
        for sec in (analysis.sections or [])
    ] or report.get("sections", [])  # 테이블이 비어있으면 report_json fallback

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "is_ready": True,
        "transcript": analysis.transcript,
        "scores": {
            "content_coverage_user": result_row.content_coverage,
            "delivery_stability": result_row.delivery_stability,
            "pacing_score": result_row.pacing_score,
        },
        "summary": report.get("summary"),
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "sections": sections,
        "reliability": report.get("reliability"),
        "document_upload_id": document_upload.upload_id if document_upload else None,
        "document_filename": document_upload.original_filename if document_upload else None,
    }


# ──────────────────────────────────────────────────────────────
# GET /notes/{note_id}/analyses/history
# ──────────────────────────────────────────────────────────────

@router.get("/notes/{note_id}/analyses/history")
def get_analysis_history(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """노트의 완료된 분석 목록을 시간순으로 반환 (히스토리 그래프용)."""
    rows = (
        db.query(Analysis, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.analysis_id == Analysis.analysis_id)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.asc().nulls_last())
        .all()
    )
    return [
        {
            "analysis_id": str(analysis.analysis_id),
            "label": f"{i + 1}차",
            "finished_at": analysis.finished_at.isoformat() if analysis.finished_at else None,
            "scores": {
                "content_coverage_user": result_row.content_coverage,
                "delivery_stability": result_row.delivery_stability,
                "pacing_score": result_row.pacing_score,
            },
        }
        for i, (analysis, result_row) in enumerate(rows)
    ]


# ──────────────────────────────────────────────────────────────
# GET /notes/{note_id}/analyses/latest/result
# ──────────────────────────────────────────────────────────────

@router.get("/notes/{note_id}/analyses/latest/result", response_model=AnalysisResultResponse)
def get_latest_analysis_result(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(Analysis, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.analysis_id == Analysis.analysis_id)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc().nulls_last())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="완료된 분석 결과가 없습니다.")

    analysis, result_row = row

    document_upload = (
        db.query(Upload).filter(Upload.upload_id == analysis.document_upload_id).first()
        if analysis.document_upload_id else None
    )
    return _build_result_payload(analysis, result_row, document_upload)


@router.get("/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.analysis_id == analysis_id, Analysis.user_id == current_user.user_id)
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 정보를 찾을 수 없습니다.")
    return analysis


# ──────────────────────────────────────────────────────────────
# GET /analyses/{analysis_id}/result
# ──────────────────────────────────────────────────────────────

@router.get("/analyses/{analysis_id}/result", response_model=AnalysisResultResponse)
def get_analysis_result(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.analysis_id == analysis_id, Analysis.user_id == current_user.user_id)
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 정보를 찾을 수 없습니다.")

    # 분석이 끝나지 않았으면 빈 응답
    if analysis.status != "done":
        return {
            "analysis_id": analysis.analysis_id,
            "status": analysis.status,
            "is_ready": False,
            "transcript": None,
            "scores": None,
            "summary": None,
            "strengths": [],
            "improvements": [],
            "sections": [],
        }

    # analysis_results 테이블에서 결과 로드
    result_row = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .first()
    )

    if result_row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 결과 행이 존재하지 않습니다. 관리자에게 문의하세요.",
        )

    document_upload = (
        db.query(Upload).filter(Upload.upload_id == analysis.document_upload_id).first()
        if analysis.document_upload_id else None
    )
    return _build_result_payload(analysis, result_row, document_upload)


# ──────────────────────────────────────────────────────────────
# POST /analyses/{analysis_id}/submit-result
# 워커가 모델 report.json을 제출 → 모델 값 그대로 DB 저장
# ──────────────────────────────────────────────────────────────

@router.post("/analyses/{analysis_id}/submit-result", status_code=status.HTTP_200_OK)
def submit_analysis_result(
    analysis_id: UUID,
    payload: AnalysisSubmitRequest,
    db: Session = Depends(get_db),
):
    """워커가 모델 report.json 전체를 보내면 DB에 저장.

    모델이 이미 계산한 점수·LLM 피드백·섹션 데이터를 그대로 사용한다.
    """
    analysis = db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석을 찾을 수 없습니다.")
    if analysis.status == "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 완료된 분석입니다.")

    # 모델 출력 → DB 저장 형식으로 변환 (점수·텍스트 모두 모델 값 직접 사용)
    result = build_report_from_model(payload.model_dump())

    sections = result["report"].pop("sections", [])  # 섹션은 analysis_sections 테이블에 별도 저장
    transcript = result.pop("transcript", "")  # analyses 테이블에 직접 저장

    # ── analysis_results 테이블: 점수 + summary/strengths/improvements ──
    existing = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == analysis_id).first()
    if existing:
        existing.content_coverage = result["scores"]["content_coverage_user"]
        existing.delivery_stability = result["scores"]["delivery_stability"]
        existing.pacing_score = result["scores"]["pacing_score"]
        existing.overall_score = result["scores"]["overall_score"]
        existing.severity_json = result["severity"]
        existing.report_json = result["report"]  # sections 제외
    else:
        db.add(AnalysisResult(
            analysis_id=analysis_id,
            content_coverage=result["scores"]["content_coverage_user"],
            delivery_stability=result["scores"]["delivery_stability"],
            pacing_score=result["scores"]["pacing_score"],
            overall_score=result["scores"]["overall_score"],
            severity_json=result["severity"],
            report_json=result["report"],  # sections 제외
        ))

    # ── analysis_sections 테이블: 섹션별 행으로 정규화 저장 ──
    # 기존 섹션 삭제 후 재삽입 (재분석 시 덮어쓰기)
    db.query(AnalysisSection).filter(AnalysisSection.analysis_id == analysis_id).delete()
    for sec in sections:
        db.add(AnalysisSection(
            analysis_id=analysis_id,
            order_index=sec["section_index"],
            title=sec["title"],
            start_time_sec=sec["start_time_sec"],
            end_time_sec=sec["end_time_sec"],
            score_json={"score": sec["score"]},
            feedback_json={"text": sec["feedback"]},
        ))

    # ── analyses 테이블: 상태 + 대본 ──
    analysis.transcript = transcript
    analysis.status = "done"
    analysis.progress = 100
    analysis.stage = "finished"
    analysis.finished_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "analysis_id": analysis_id,
        "status": "done",
        "scores": result["scores"],
    }
