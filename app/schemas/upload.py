from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadPresignRequest(BaseModel):
    note_id: Optional[UUID] = Field(default=None, description="연결할 노트 ID")
    kind: str = Field(..., min_length=1, max_length=20, description="파일 종류, document / audio / other")
    file_name: str = Field(..., min_length=1, max_length=255, description="업로드할 원본 파일명")
    content_type: str = Field(..., min_length=1, max_length=100, description="MIME 타입")
    size_bytes: int = Field(..., ge=0, description="파일 크기(byte)")


class UploadPresignResponse(BaseModel):
    upload_id: UUID
    method: str
    upload_url: str
    object_key: str
    expires_in_sec: int


class UploadCompleteRequest(BaseModel):
    upload_id: UUID
    etag: Optional[str] = Field(default=None, description="S3 업로드 결과 ETag")
    checksum: Optional[str] = Field(default=None, description="무결성 검사용 checksum")


class UploadCompleteResponse(BaseModel):
    upload_id: UUID
    status: str


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_id: UUID
    user_id: UUID
    note_id: Optional[UUID]
    kind: str
    storage: str
    bucket: str
    object_key: str
    original_filename: str
    url: Optional[str]
    content_type: str
    size_bytes: int
    checksum: Optional[str]
    status: str
    created_at: datetime


class UploadListResponse(BaseModel):
    items: list[UploadResponse]
    total: int