from datetime import datetime  # 생성, 수정 시각 응답 필드에 사용
from typing import Optional  # 선택 필드, None 허용에 사용
from uuid import UUID  # note_id, user_id 같은 UUID 타입에 사용

from pydantic import BaseModel, ConfigDict, Field  # Pydantic 스키마 정의용


# 노트 생성 요청 body 스키마
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="노트 제목")
    description: Optional[str] = Field(default=None, description="노트 설명")


# 노트 수정 요청 body 스키마
# PATCH 이므로 각 필드는 선택적으로 들어올 수 있음
class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="수정할 노트 제목")
    description: Optional[str] = Field(default=None, description="수정할 노트 설명")


# 노트 단건 응답 스키마
# SQLAlchemy 객체를 그대로 반환해도 읽을 수 있게 from_attributes 사용
class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


# 노트 목록 조회 응답 스키마
class NoteListResponse(BaseModel):
    items: list[NoteResponse]
    total: int