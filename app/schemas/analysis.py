from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreateRequest(BaseModel):
    document_upload_id: Optional[UUID] = Field(default=None, description="문서 업로드 ID")
    audio_upload_id: Optional[UUID] = Field(default=None, description="음성 업로드 ID")
    pipeline_version: str = Field(..., min_length=1, max_length=50, description="파이프라인 버전")
    model_version_ce: Optional[str] = Field(default=None, max_length=100, description="CE 모델 버전")
    model_version_ae: Optional[str] = Field(default=None, max_length=100, description="AE 모델 버전")


class AnalysisCreateResponse(BaseModel):
    analysis_id: UUID
    status: str
    progress: int
    stage: str


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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



class AnalysisScoreResponse(BaseModel):
    content_coverage: int = Field(..., ge=0, le=100)
    delivery_stability: int = Field(..., ge=0, le=100)
    pacing_score: int = Field(..., ge=0, le=100)


class AnalysisStrengthItem(BaseModel):
    text: str


class AnalysisImprovementItem(BaseModel):
    text: str


class AnalysisSectionResponse(BaseModel):
    section_index: int
    title: str
    start_time_sec: int
    end_time_sec: int
    score: int = Field(..., ge=0, le=100)
    feedback: str


class AnalysisResultResponse(BaseModel):
    analysis_id: UUID
    status: str
    is_ready: bool
    scores: Optional[AnalysisScoreResponse] = None
    summary: Optional[str] = None
    strengths: list[AnalysisStrengthItem] = Field(default_factory=list)
    improvements: list[AnalysisImprovementItem] = Field(default_factory=list)
    sections: list[AnalysisSectionResponse] = Field(default_factory=list)
