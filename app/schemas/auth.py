from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="사용자 이메일")
    password: Optional[str] = Field(default=None, description="비밀번호 (local 로그인 시 필수)")
    provider: Literal["local", "google"] = Field(default="local", description="로그인 제공자")
    name: Optional[str] = Field(default=None, description="사용자 이름")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    name: str
    provider: str
    provider_id: Optional[str]
    created_at: datetime
