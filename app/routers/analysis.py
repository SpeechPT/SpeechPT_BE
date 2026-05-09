"""분석 트리거 + 상태/결과 조회 라우터.

<<<<<<< HEAD
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

=======
흐름(프로덕션):
  POST → analyses INSERT → SQS enqueue → Worker가 STT+채점 후 DB 업데이트

흐름(로컬 / SQS 미설정):
  POST → analyses INSERT → BackgroundTask로 직접 STT 실행 → DB 업데이트
"""
from __future__ import annotations

import uuid as _uuid
>>>>>>> b7c9480 (버그 수정 및 개선)
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
<<<<<<< HEAD
from app.core.sqs import enqueue_analysis
from app.db import get_db
=======
from app.db import SessionLocal, get_db
>>>>>>> b7c9480 (버그 수정 및 개선)
from app.models.analysis import Analysis
from app.models.analysis_input import AnalysisInput
from app.models.analysis_result import AnalysisResult
from app.models.note import Note
from app.models.upload import Upload
from app.models.user import User
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisResultResponse,
    AnalysisStatusResponse,
)

router = APIRouter(tags=["analyses"])

<<<<<<< HEAD
=======

# ──────────────────────────────────────────────────────────────
# 로컬 BackgroundTask: STT 실행 → Analysis 업데이트
# ──────────────────────────────────────────────────────────────

def _local_analysis_task(analysis_id: _uuid.UUID, audio_path: str) -> None:
    """SQS 없이 로컬에서 STT를 실행하고 DB를 업데이트한다."""
    from app.services.stt_service import run_stt

    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        if analysis is None:
            return

        analysis.status = "running"
        analysis.stage = "loading_model"
        analysis.progress = 25
        db.commit()

        # STT 실행 (수 초~수십 초 소요)
        stt_result = run_stt(audio_path)
        analysis.stage = "transcribing"
        analysis.progress = 55
        db.commit()

        transcript = stt_result.get("text", "")

        analysis.transcript = transcript
        analysis.stage = "postprocessing"
        analysis.progress = 80
        db.commit()

        analysis.status = "done"
        analysis.progress = 100
        analysis.stage = "finished"
        analysis.finished_at = datetime.now(timezone.utc)
        db.commit()

        # AnalysisResult mock 행 생성 (AI 파이프라인 연결 전까지 임시 점수)
        existing = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == analysis_id).first()
        if existing is None:
            mock_result = AnalysisResult(
                analysis_id=analysis_id,
                content_coverage=82,
                delivery_stability=76,
                pacing_score=69,
                overall_score=76,
                severity_json={},
                report_json={
                    "summary": "STT 변환이 완료되었습니다. 점수는 AI 파이프라인 연결 후 실제 분석값으로 대체됩니다.",
                    "strengths": [
                        {"text": "핵심 메시지 전달이 비교적 명확합니다."},
                        {"text": "슬라이드 흐름과 발화 내용의 정합성이 좋습니다."},
                    ],
                    "improvements": [
                        {"text": "후반부 말속도가 빨라져 전달력이 떨어집니다."},
                        {"text": "일부 구간에서 발화 안정성이 낮아집니다."},
                    ],
                    "sections": [
                        {
                            "section_index": 1,
                            "title": "도입부",
                            "start_time_sec": 0,
                            "end_time_sec": 22,
                            "score": 84,
                            "feedback": "도입은 안정적이지만 말속도가 살짝 빠릅니다.",
                        },
                        {
                            "section_index": 2,
                            "title": "핵심 내용 설명",
                            "start_time_sec": 23,
                            "end_time_sec": 58,
                            "score": 78,
                            "feedback": "슬라이드와 설명은 잘 맞지만 핵심 단어 강조가 약합니다.",
                        },
                        {
                            "section_index": 3,
                            "title": "마무리",
                            "start_time_sec": 59,
                            "end_time_sec": 83,
                            "score": 65,
                            "feedback": "마무리 구간에서 말속도가 빨라지고 안정감이 떨어집니다.",
                        },
                    ],
                },
            )
            db.add(mock_result)
            db.commit()

    except Exception as exc:  # noqa: BLE001
        db2 = SessionLocal()
        try:
            row = db2.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
            if row:
                row.status = "failed"
                row.error_message = str(exc)[:500]
                db2.commit()
        finally:
            db2.close()
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# POST /notes/{note_id}/analyses
# ──────────────────────────────────────────────────────────────
>>>>>>> b7c9480 (버그 수정 및 개선)

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
<<<<<<< HEAD
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="음성 파일 업로드가 아직 완료되지 않았습니다.",
        )

    # ── 3. analyses 행 INSERT (status=queued) ────────────────
=======
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="음성 파일 업로드가 아직 완료되지 않았습니다.")

    # ── 3. analyses 행 INSERT ─────────────────────────────────
>>>>>>> b7c9480 (버그 수정 및 개선)
    analysis = Analysis(
        note_id=note_id,
        user_id=current_user.user_id,
        document_upload_id=payload.document_upload_id,
        audio_upload_id=payload.audio_upload_id,
        pipeline_version=payload.pipeline_version,
        model_version_ce=payload.model_version_ce,
        model_version_ae=payload.model_version_ae,
<<<<<<< HEAD
        status="queued",
        progress=0,
        stage="ingest",
=======
        status="running",
        progress=10,
        stage="queued",
>>>>>>> b7c9480 (버그 수정 및 개선)
        trigger_type="manual",
        worker_id=None,
        error_code=None,
        error_message=None,
<<<<<<< HEAD
        started_at=None,
=======
        started_at=datetime.now(timezone.utc),
>>>>>>> b7c9480 (버그 수정 및 개선)
        finished_at=None,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # ── 4. analysis_inputs 행 INSERT ──────────────────────────
<<<<<<< HEAD
    analysis_input = AnalysisInput(
        analysis_id=analysis.analysis_id,
        document_path=_storage_uri(document_upload),
        audio_path=_storage_uri(audio_upload),
=======
    audio_path = _storage_uri(audio_upload)
    analysis_input = AnalysisInput(
        analysis_id=analysis.analysis_id,
        document_path=_storage_uri(document_upload),
        audio_path=audio_path,
>>>>>>> b7c9480 (버그 수정 및 개선)
    )
    db.add(analysis_input)
    db.commit()

<<<<<<< HEAD
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
=======
    # ── 5. SQS 또는 로컬 BackgroundTask ──────────────────────
    import os
    queue_url = os.environ.get("ANALYSIS_QUEUE_URL", "")

    if queue_url:
        # 프로덕션: SQS enqueue
        try:
            from app.core.sqs import enqueue_analysis
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
            analysis.status = "failed"
            analysis.error_code = "ENQUEUE_FAILED"
            analysis.error_message = str(exc)[:500]
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"분석 작업 큐 등록에 실패했습니다: {exc}",
            )
    else:
        # 로컬 개발: BackgroundTask로 STT 직접 실행
        background_tasks.add_task(_local_analysis_task, analysis.analysis_id, audio_path)
>>>>>>> b7c9480 (버그 수정 및 개선)

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "progress": analysis.progress,
        "stage": analysis.stage,
    }


def _storage_uri(upload: Upload) -> str:
<<<<<<< HEAD
    """Upload의 위치를 단일 문자열로 표현."""
=======
>>>>>>> b7c9480 (버그 수정 및 개선)
    if upload.storage == "s3":
        return f"s3://{upload.bucket}/{upload.object_key}"
    return upload.url or upload.object_key


<<<<<<< HEAD
=======
# ──────────────────────────────────────────────────────────────
# GET /notes/{note_id}/analyses/latest/result
# ──────────────────────────────────────────────────────────────

@router.get("/notes/{note_id}/analyses/latest/result", response_model=AnalysisResultResponse)
def get_latest_analysis_result(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc())
        .first()
    )
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="완료된 분석 결과가 없습니다.",
        )

    result_row = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_id == analysis.analysis_id)
        .first()
    )
    if result_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석 결과 데이터가 없습니다.",
        )

    report = result_row.report_json or {}

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "is_ready": True,
        "transcript": analysis.transcript,
        "scores": {
            "content_coverage": result_row.content_coverage,
            "delivery_stability": result_row.delivery_stability,
            "pacing_score": result_row.pacing_score,
        },
        "summary": report.get("summary"),
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "sections": report.get("sections", []),
    }


# ──────────────────────────────────────────────────────────────
# GET /analyses/{analysis_id}/status
# ──────────────────────────────────────────────────────────────

>>>>>>> b7c9480 (버그 수정 및 개선)
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

<<<<<<< HEAD
    # 분석이 끝나지 않았으면 빈 응답
=======
>>>>>>> b7c9480 (버그 수정 및 개선)
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

<<<<<<< HEAD
    # analysis_results 테이블에서 결과 로드
=======
>>>>>>> b7c9480 (버그 수정 및 개선)
    result_row = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .first()
    )
<<<<<<< HEAD

    if result_row is None:
        # 데이터 정합성 문제: status=done인데 결과 row가 없음
=======
    if result_row is None:
>>>>>>> b7c9480 (버그 수정 및 개선)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 결과 행이 존재하지 않습니다. 관리자에게 문의하세요.",
        )

    report = result_row.report_json or {}

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "is_ready": True,
        "transcript": analysis.transcript,
        "scores": {
            "content_coverage": result_row.content_coverage,
            "delivery_stability": result_row.delivery_stability,
            "pacing_score": result_row.pacing_score,
        },
        "summary": report.get("summary"),
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "sections": report.get("sections", []),
    }
