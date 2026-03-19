

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.analysis import Analysis
from app.models.note import Note
from app.models.upload import Upload
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisResultResponse,
    AnalysisStatusResponse,
)

router = APIRouter(tags=["analyses"])

# 임시 고정 user_id, 나중에 auth 붙이면 current_user.user_id 로 교체
DUMMY_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


@router.post(
    "/notes/{note_id}/analyses",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis(note_id: UUID, payload: AnalysisCreateRequest, db: Session = Depends(get_db)):
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == DUMMY_USER_ID)
        .first()
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="노트를 찾을 수 없습니다.",
        )

    document_upload = (
        db.query(Upload)
        .filter(
            Upload.upload_id == payload.document_upload_id,
            Upload.user_id == DUMMY_USER_ID,
            Upload.note_id == note_id,
        )
        .first()
    )
    if document_upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서 업로드 정보를 찾을 수 없습니다.",
        )
    if document_upload.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="문서 파일 업로드가 아직 완료되지 않았습니다.",
        )

    audio_upload = (
        db.query(Upload)
        .filter(
            Upload.upload_id == payload.audio_upload_id,
            Upload.user_id == DUMMY_USER_ID,
            Upload.note_id == note_id,
        )
        .first()
    )
    if audio_upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="음성 업로드 정보를 찾을 수 없습니다.",
        )
    if audio_upload.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="음성 파일 업로드가 아직 완료되지 않았습니다.",
        )

    analysis = Analysis(
        note_id=note_id,
        user_id=DUMMY_USER_ID,
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

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "progress": analysis.progress,
        "stage": analysis.stage,
    }


@router.get("/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(analysis_id: UUID, db: Session = Depends(get_db)):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.analysis_id == analysis_id, Analysis.user_id == DUMMY_USER_ID)
        .first()
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석 정보를 찾을 수 없습니다.",
        )

    return analysis


@router.get("/analyses/{analysis_id}/result", response_model=AnalysisResultResponse)
def get_analysis_result(analysis_id: UUID, db: Session = Depends(get_db)):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.analysis_id == analysis_id, Analysis.user_id == DUMMY_USER_ID)
        .first()
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석 정보를 찾을 수 없습니다.",
        )

    if analysis.status != "done":
        return {
            "analysis_id": analysis.analysis_id,
            "status": analysis.status,
            "message": "아직 최종 분석 결과가 생성되지 않았습니다.",
        }

    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "message": "추후 analysis_results, analysis_sections와 연결 예정입니다.",
    }