from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="노트 제목")
    description: Optional[str] = Field(default=None, description="노트 설명")


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="수정할 노트 제목")
    description: Optional[str] = Field(default=None, description="수정할 노트 설명")


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class NoteListResponse(BaseModel):
    items: list[NoteResponse]
    total: int