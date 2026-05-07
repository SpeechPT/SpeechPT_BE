from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PracticeSessionCreateRequest(BaseModel):
    analysis_id: UUID
    section_id: Optional[UUID] = None
    mode: str
    target_snapshot_json: dict


class PracticeSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    practice_session_id: UUID
    analysis_id: UUID
    section_id: Optional[UUID]
    user_id: UUID
    mode: str
    target_snapshot_json: dict
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    created_at: datetime


class PracticeResultCreateRequest(BaseModel):
    avg_wpm: Optional[float] = None
    avg_pitch: Optional[float] = None
    silence_ratio: Optional[float] = None
    target_hit_rate: Optional[float] = None
    score_delta_json: Optional[dict] = None
    feedback_json: Optional[dict] = None
    raw_metrics_s3_key: Optional[str] = None


class PracticeResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    practice_result_id: UUID
    practice_session_id: UUID
    avg_wpm: Optional[float]
    avg_pitch: Optional[float]
    silence_ratio: Optional[float]
    target_hit_rate: Optional[float]
    score_delta_json: Optional[Any]
    feedback_json: Optional[Any]
    raw_metrics_s3_key: Optional[str]
    created_at: datetime
