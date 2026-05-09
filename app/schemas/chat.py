from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreateRequest(BaseModel):
    note_id: UUID
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_session_id: UUID
    note_id: UUID
    user_id: UUID
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int


class ChatMessageCreateRequest(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    related_analysis_id: Optional[UUID] = None
    related_section_id: Optional[UUID] = None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    chat_session_id: UUID
    role: str
    content: str
    related_analysis_id: Optional[UUID]
    related_section_id: Optional[UUID]
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int


class ChatReplyRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=3000)


class ChatReplyResponse(BaseModel):
    session_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    answer: str
