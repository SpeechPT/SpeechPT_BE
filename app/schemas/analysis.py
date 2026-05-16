from datetime import datetime
from typing import Optional, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────
# 모델 출력 제출 스키마 (Worker → Backend)
# ──────────────────────────────────────────

class ModelOverallScores(BaseModel):
    """모델이 산출한 전체 점수 (0~100 실수)."""
    content_coverage: float = Field(..., ge=0.0, le=100.0)
    content_coverage_user: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    delivery_stability: float = Field(..., ge=0.0, le=100.0)
    pacing_score: float = Field(..., ge=0.0, le=100.0)


class ModelAEProbe(BaseModel):
    ae_probe_overall_delivery: float = Field(default=0.5, ge=0.0, le=1.0)
    ae_probe_energy_drop_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    ae_probe_pitch_shift_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    ae_probe_speech_rate: float = Field(default=2.5, ge=0.0)


class ModelPerSlideDetail(BaseModel):
    slide_id: int
    slide_role: Optional[str] = None
    coverage_weight: float = 1.0
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    missed: List[str] = Field(default_factory=list)
    speech_rate: float = 0.0
    silence_ratio: float = 0.0
    dwell_sec: float = 0.0
    delivery_stability: float = 0.0
    ae_probe: Optional[ModelAEProbe] = None
    trend: Optional[Any] = None
    change_points: Optional[Any] = None


class ModelSlideComment(BaseModel):
    slide_id: int
    comment: str


class ModelLLMFeedback(BaseModel):
    overall_comment: str = ""
    strengths: List[str] = Field(default_factory=list)
    priority_actions: List[str] = Field(default_factory=list)
    slide_comments: List[ModelSlideComment] = Field(default_factory=list)


class ModelAlignment(BaseModel):
    final_boundaries: List[float] = Field(default_factory=list)


class ModelTranscriptWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float = 1.0


class ModelTranscriptSegment(BaseModel):
    slide_id: int
    start_sec: float
    end_sec: float
    text: str
    words: List[ModelTranscriptWord] = Field(default_factory=list)


class ModelHighlightFeedback(BaseModel):
    text: str


class ModelHighlightSection(BaseModel):
    slide_id: int
    severity: str = "low"
    issues: List[str] = Field(default_factory=list)
    feedback: List[ModelHighlightFeedback] = Field(default_factory=list)


class ModelReliability(BaseModel):
    """모델이 산출한 분석 신뢰도 정보."""
    alignment_level: str = "high"  # "high" | "medium" | "low"
    content_coverage_shown: bool = True
    note: str = ""


class AnalysisSubmitRequest(BaseModel):
    """워커가 모델 report.json 전체를 백엔드에 제출할 때 사용하는 스키마."""
    overall_scores: ModelOverallScores
    per_slide_detail: List[ModelPerSlideDetail] = Field(default_factory=list)
    llm_feedback: Optional[ModelLLMFeedback] = None
    alignment: Optional[ModelAlignment] = None
    transcript_segments: List[ModelTranscriptSegment] = Field(default_factory=list)
    highlight_sections: List[ModelHighlightSection] = Field(default_factory=list)
    reliability: Optional[ModelReliability] = None


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
    content_coverage_user: int = Field(..., ge=0, le=100)
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
    transcript: Optional[str] = None
    scores: Optional[AnalysisScoreResponse] = None
    summary: Optional[str] = None
    strengths: list[AnalysisStrengthItem] = Field(default_factory=list)
    improvements: list[AnalysisImprovementItem] = Field(default_factory=list)
    sections: list[AnalysisSectionResponse] = Field(default_factory=list)
    reliability: Optional[Any] = None
    document_upload_id: Optional[UUID] = None
    document_filename: Optional[str] = None


# ──────────────────────────────────────────
# analysis_inputs 스키마
# ──────────────────────────────────────────

class AnalysisInputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    document_path: str
    audio_path: str
    slide_timestamps_s3_key: Optional[str]
    whisper_words_s3_key: Optional[str]
    config_yaml_path: Optional[str]
    created_at: datetime


# ──────────────────────────────────────────
# analysis_results 스키마
# ──────────────────────────────────────────

class AnalysisResultDBResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    content_coverage: int
    delivery_stability: int
    pacing_score: int
    overall_score: int
    severity_json: Any
    report_json: Any
    result_blob_s3_key: Optional[str]
    created_at: datetime


# ──────────────────────────────────────────
# analysis_sections 스키마
# ──────────────────────────────────────────

class AnalysisSectionDBResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: UUID
    analysis_id: UUID
    order_index: int
    title: str
    start_time_sec: Optional[int]
    end_time_sec: Optional[int]
    slide_range_json: Optional[Any]
    targets_json: Optional[Any]
    feedback_json: Optional[Any]
    score_json: Optional[Any]
    created_at: datetime
