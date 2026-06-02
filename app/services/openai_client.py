"""Minimal stdlib OpenAI client for embeddings and chat completions.

BE에서 추가 패키지 의존 없이 사용. 시크릿은 환경변수 OPENAI_API_KEY 우선,
없으면 OPENAI_API_KEY_FILE 경로의 파일에서 sk- 토큰을 추출한다.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Generator, Iterable

logger = logging.getLogger(__name__)

_DEFAULT_EMBED_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
_DEFAULT_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
_EMBED_URL = "https://api.openai.com/v1/embeddings"
_RESPONSES_URL = "https://api.openai.com/v1/responses"
_CHAT_URL = "https://api.openai.com/v1/chat/completions"

_KEY_RE = re.compile(r"sk-[A-Za-z0-9_-]+")


def _resolve_key() -> str:
    env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if env_key:
        return env_key
    key_file = os.environ.get("OPENAI_API_KEY_FILE")
    if key_file and os.path.isfile(key_file):
        text = open(key_file, "r", encoding="utf-8", errors="ignore").read()
        match = _KEY_RE.search(text)
        if match:
            return match.group(0)
    return ""


class OpenAIClientError(RuntimeError):
    pass


def _post_json(url: str, payload: dict, timeout: float = 60.0) -> dict:
    api_key = _resolve_key()
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY가 설정되지 않았습니다.")
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIClientError(f"OpenAI HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise OpenAIClientError(f"OpenAI connection error: {exc}") from exc


def embed_texts(texts: list[str], *, model: str | None = None, batch_size: int = 96) -> list[list[float]]:
    """텍스트 리스트 → 임베딩 벡터 리스트. 입력 순서 보존."""
    if not texts:
        return []
    used_model = model or _DEFAULT_EMBED_MODEL
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        payload = {"model": used_model, "input": chunk}
        resp = _post_json(_EMBED_URL, payload, timeout=60.0)
        data = resp.get("data") or []
        if len(data) != len(chunk):
            raise OpenAIClientError(
                f"임베딩 응답 길이 불일치: req={len(chunk)} resp={len(data)}"
            )
        for item in data:
            emb = item.get("embedding")
            if not isinstance(emb, list):
                raise OpenAIClientError("임베딩 응답 형식 오류")
            out.append([float(x) for x in emb])
    return out


def chat_responses_json(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_output_tokens: int = 1200,
    temperature: float = 0.2,
) -> dict:
    """OpenAI Responses API로 JSON 객체를 받는다."""
    payload = {
        "model": model or _DEFAULT_CHAT_MODEL,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "text": {"format": {"type": "json_object"}},
    }
    resp = _post_json(_RESPONSES_URL, payload, timeout=90.0)
    text = resp.get("output_text")
    if not isinstance(text, str):
        parts = []
        for item in resp.get("output", []):
            for content in (item or {}).get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    parts.append(content["text"])
        text = "\n".join(parts).strip()
    if not text:
        raise OpenAIClientError("LLM 응답이 비어 있습니다.")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError(f"LLM JSON 파싱 실패: {exc}") from exc
    if not isinstance(obj, dict):
        raise OpenAIClientError("LLM 응답이 JSON 객체가 아닙니다.")
    return obj


def stream_chat_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = 900,
    temperature: float = 0.2,
) -> Generator[str, None, None]:
    """Call /v1/chat/completions with stream=True, yield text delta tokens."""
    api_key = _resolve_key()
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY가 설정되지 않았습니다.")

    payload = {
        "model": model or _DEFAULT_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _CHAT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120.0) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if not line.startswith("data:"):
                    continue
                data = line[5:].lstrip(" ")
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    token = (obj["choices"][0]["delta"].get("content") or "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIClientError(f"OpenAI HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise OpenAIClientError(f"OpenAI connection error: {exc}") from exc
