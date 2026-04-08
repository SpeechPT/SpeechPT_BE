from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

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

    # 파일이 없으면 분석을 시작하지 않음
    if payload.document_upload_id is None or payload.audio_upload_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석을 위해서는 문서와 음성 파일이 모두 필요합니다.",
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
        status="running",
        progress=30,
        stage="analyzing",
        trigger_type="manual",
        worker_id=None,
        error_code=None,
        error_message=None,
        started_at=func.now(),
        finished_at=None,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    analysis.status = "done"
    analysis.progress = 100
    analysis.stage = "finished"
    analysis.finished_at = func.now()
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

 # 아직 분석 안 끝났으면
    if analysis.status != "done":
        return {
            "analysis_id": analysis.analysis_id,
            "status": analysis.status,
            "is_ready": False,
            "scores": None,
            "summary": None,
            "strengths": [],
            "improvements": [],
            "sections": [],
        }

    # 분석 완료됐으면 (현재는 mock 데이터)
    return {
        "analysis_id": analysis.analysis_id,
        "status": analysis.status,
        "is_ready": True,
        "scores": {
            "content_coverage": 82,
            "delivery_stability": 76,
            "pacing_score": 69,
        },
        "summary": "전반적인 발표 흐름은 안정적이지만, 후반부로 갈수록 말속도가 빨라지고 일부 구간에서 발화 안정성이 낮아졌습니다.",
        "strengths": [
            {"text": "핵심 메시지 전달이 비교적 명확합니다."},
            {"text": "슬라이드 흐름과 발화 내용의 전반적인 정합성이 좋습니다."},
        ],
        "improvements": [
            {"text": "후반부 말속도가 빨라져 전달력이 떨어집니다."},
            {"text": "일부 구간에서 발화가 급해지며 안정성이 낮아집니다."},
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
    }
# 아직 점수나 리포트내용은 더미데이터로 처리