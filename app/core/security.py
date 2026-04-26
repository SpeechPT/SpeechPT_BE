import base64
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "900"))
REFRESH_TOKEN_EXPIRE_SECONDS = int(os.getenv("REFRESH_TOKEN_EXPIRE_SECONDS", "604800"))
HASH_ITERATIONS = 120_000
HASH_ALGORITHM = "sha256"
SALT_LENGTH = 16


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding and padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_LENGTH)
    digest = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode("utf-8"), salt, HASH_ITERATIONS)
    return _base64url_encode(salt + digest)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        decoded = _base64url_decode(password_hash)
        salt = decoded[:SALT_LENGTH]
        expected = decoded[SALT_LENGTH:]
        actual = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode("utf-8"), salt, HASH_ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _sign(payload: bytes) -> str:
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).digest()
    return _base64url_encode(signature)


def _encode_jwt(header: dict, payload: dict) -> str:
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = _sign(signing_input)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 토큰 형식입니다.")

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_sig = _sign(signing_input)
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 검증에 실패했습니다.")

    try:
        payload_json = _base64url_decode(encoded_payload)
        payload = json.loads(payload_json.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 payload를 읽을 수 없습니다.")

    exp = payload.get("exp")
    if exp is None or int(time.time()) > int(exp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 만료되었습니다.")

    return payload


def create_access_token(data: dict[str, Any]) -> str:
    payload = {**data}
    payload["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS
    payload["type"] = "access"
    payload["iat"] = int(time.time())
    return _encode_jwt({"alg": "HS256", "typ": "JWT"}, payload)


def create_refresh_token(data: dict[str, Any]) -> str:
    payload = {**data}
    payload["exp"] = int(time.time()) + REFRESH_TOKEN_EXPIRE_SECONDS
    payload["type"] = "refresh"
    payload["iat"] = int(time.time())
    return _encode_jwt({"alg": "HS256", "typ": "JWT"}, payload)


def decode_jwt(token: str) -> dict[str, Any]:
    payload = _decode_jwt(token)
    if payload.get("type") not in {"access", "refresh"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 유형이 올바르지 않습니다.")
    return payload
