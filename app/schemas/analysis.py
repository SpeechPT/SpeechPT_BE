from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    document_upload_id: UUID = Field(..., description="문서 업로드 ID")
    audio_upload_id: UUID = Field(..., description="음성 업로드 ID")
    pipeline_version: str = Field(..., min_length=1, max_length=50, description="파이프라인 버전")
    model_version_ce: Optional[str] = Field(default=None, max_length=100, description="CE 모델 버전")
    model_version_ae: Optional[str] = Field(default=None, max_length=100, description="AE 모델 버전")


class AnalysisCreateResponse(BaseModel):
    analysis_id: UUID
    status: str
    progress: int
    stage: str


class AnalysisStatusResponse(BaseModel):
    analysis_id: UUID
    note_id: UUID
    user_id: UUID
    document_upload_id: UUID
    audio_upload_id: UUID
    pipeline_version: str
    model_version_ce: Optional[str]
    model_version_ae: Optional[str]
    status: str
    progress: int
    stage: str
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class AnalysisResultResponse(BaseModel):
    analysis_id: UUID
    status: str
    message: str
