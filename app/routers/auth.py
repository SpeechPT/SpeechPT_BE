import json
import os
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/auth/oauth/callback")
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"


class Provider(str, Enum):
    local = "local"
    google = "google"


router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _ensure_email_domain(email: str, provider: Provider) -> None:
    domain = email.split("@")[-1]

    if provider == Provider.google and domain != "gmail.com":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="구글 로그인은 gmail.com 계정만 사용할 수 있습니다.",
        )


def _build_oauth_url(provider: Provider) -> str:
    if provider == Provider.google:
        if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth 설정이 올바르지 않습니다.",
            )

        query = {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": provider.value,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(query)}"

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원되지 않는 OAuth 제공자입니다.")


def _exchange_oauth_code(provider: Provider, code: str) -> dict:
    if provider != Provider.google:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원되지 않는 OAuth 제공자입니다.",
        )

    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET or not GOOGLE_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth 설정이 올바르지 않습니다.",
        )

    client_id = GOOGLE_OAUTH_CLIENT_ID
    client_secret = GOOGLE_OAUTH_CLIENT_SECRET
    redirect_uri = GOOGLE_OAUTH_REDIRECT_URI
    token_endpoint = GOOGLE_TOKEN_ENDPOINT

    data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        token_endpoint,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8") if error.fp else str(error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_google_id_token(id_token: str) -> dict:
    url = f"{GOOGLE_TOKENINFO_ENDPOINT}?id_token={urllib.parse.quote_plus(id_token)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google id_token 검증에 실패했습니다.",
        )

    if payload.get("aud") != GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google 토큰 클라이언트가 올바르지 않습니다.",
        )

    email_verified = payload.get("email_verified")
    if email_verified not in (True, "true"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google 이메일 인증이 완료되지 않았습니다.",
        )

    return payload


def _fetch_oauth_user_info(provider: Provider, token_data: dict) -> dict:
    if provider != Provider.google:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원되지 않는 OAuth 제공자입니다.",
        )

    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google id_token을 가져오지 못했습니다.",
        )

    return _validate_google_id_token(id_token)


def _create_or_get_user_from_google(payload: dict, provider: Provider, db: Session) -> User:
    email = _normalize_email(payload.get("email", ""))
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google 계정 이메일을 가져올 수 없습니다.",
        )

    _ensure_email_domain(email, provider)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=None,
            name=payload.get("name") or email.split("@")[0],
            provider=provider.value,
            provider_id=payload.get("sub") or email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.provider != provider.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이 이메일은 다른 로그인 방식으로 이미 등록되어 있습니다.",
        )

    return user


def _redirect_with_tokens(access_token: str, refresh_token: str) -> RedirectResponse:
    query = urllib.parse.urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )
    redirect_url = f"{FRONTEND_URL}/note.html?{query}"
    return RedirectResponse(url=redirect_url)


@router.get("/oauth/login")
def oauth_login(provider: Provider = Query(Provider.google, description="google")):
    return RedirectResponse(url=_build_oauth_url(provider))


@router.get("/oauth/callback")
def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth 인증 코드가 누락되었습니다.",
        )

    provider = Provider(state or Provider.google)
    token_data = _exchange_oauth_code(provider, code)
    payload = _fetch_oauth_user_info(provider, token_data)
    user = _create_or_get_user_from_google(payload, provider, db)

    token_data = {
        "user_id": str(user.user_id),
        "email": user.email,
        "provider": user.provider,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return _redirect_with_tokens(access_token, refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    provider = Provider(payload.provider)
    password = payload.password
    name = payload.name or email.split("@")[0]

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        if provider == Provider.local and not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="로컬 로그인 시 비밀번호가 필요합니다.",
            )

        if provider == Provider.google:
            _ensure_email_domain(email, provider)

        user = User(
            email=email,
            password_hash=hash_password(password) if provider == Provider.local else None,
            name=name,
            provider=provider.value,
            provider_id=email if provider != Provider.local else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.provider != provider.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이 이메일은 다른 로그인 방식으로 이미 등록되어 있습니다.",
            )

        if provider == Provider.local:
            if not password or not verify_password(password, user.password_hash or ""):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="이메일 또는 비밀번호가 올바르지 않습니다.",
                )
        else:
            _ensure_email_domain(email, provider)

    token_data = {
        "user_id": str(user.user_id),
        "email": user.email,
        "provider": user.provider,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest):
    token_payload = decode_jwt(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 필요합니다.",
        )

    token_data = {
        "user_id": token_payload["user_id"],
        "email": token_payload["email"],
        "provider": token_payload["provider"],
    }
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
