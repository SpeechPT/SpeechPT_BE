from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import SessionLocal, get_db
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.note import Note
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatReplyRequest,
    ChatReplyResponse,
    ChatSuggestionsResponse,
)
from app.services.chat_rag import STREAM_SYSTEM_PROMPT, answer_question, prepare_rag_context
from app.services.openai_client import OpenAIClientError, stream_chat_text
from app.services.suggestions import build_suggestions

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("/notes/{note_id}/chat")
def get_or_create_chat_session(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == current_user.user_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노트를 찾을 수 없습니다.")

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.note_id == note_id,
            ChatSession.user_id == current_user.user_id,
        )
        .first()
    )

    if session is None:
        session = ChatSession(note_id=note_id, user_id=current_user.user_id)
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_session_id == session.chat_session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "session_id": str(session.chat_session_id),
        "messages": [
            {
                "message_id": str(m.message_id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "citations": m.citations_json or [],
            }
            for m in messages
        ],
    }


@router.get(
    "/notes/{note_id}/chat/suggestions",
    response_model=ChatSuggestionsResponse,
)
def get_chat_suggestions(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == current_user.user_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노트를 찾을 수 없습니다.")
    items = build_suggestions(db, user_id=current_user.user_id, note_id=note_id)
    return {"items": items}


@router.post(
    "/chat-sessions/{session_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
def add_chat_message(
    session_id: UUID,
    payload: ChatMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.chat_session_id == session_id,
            ChatSession.user_id == current_user.user_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")

    message = ChatMessage(
        chat_session_id=session_id,
        role=payload.role,
        content=payload.content,
    )
    db.add(message)
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)

    return {
        "message_id": str(message.message_id),
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


@router.delete(
    "/chat-sessions/{session_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_chat_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.chat_session_id == session_id,
            ChatSession.user_id == current_user.user_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")

    db.query(ChatMessage).filter(ChatMessage.chat_session_id == session_id).delete()
    db.commit()


@router.post(
    "/chat-sessions/{session_id}/reply",
    response_model=ChatReplyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_reply(
    session_id: UUID,
    payload: ChatReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.chat_session_id == session_id,
            ChatSession.user_id == current_user.user_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")

    latest_analysis = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == session.note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc().nullslast(), Analysis.created_at.desc())
        .first()
    )

    # 직전 6턴 히스토리
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
        .all()
    )
    recent_messages = list(reversed(recent))

    user_message = ChatMessage(
        chat_session_id=session_id,
        role="user",
        content=payload.question.strip(),
        related_analysis_id=latest_analysis.analysis_id if latest_analysis else None,
    )
    db.add(user_message)
    db.flush()

    intent_value: str | None = None
    citations: list[dict] = []
    try:
        if latest_analysis is not None and latest_analysis.rag_indexed_at is None:
            answer_text = (
                "분석은 완료됐지만 챗봇 자료를 준비 중입니다. 1~2분 뒤 다시 시도해 주세요."
            )
        else:
            result = answer_question(
                db,
                user_id=current_user.user_id,
                note_id=session.note_id,
                question=payload.question,
                recent_messages=recent_messages,
            )
            answer_text = result["answer"]
            citations = result.get("citations") or []
            intent_value = result.get("intent")
    except OpenAIClientError as exc:
        logger.warning("LLM 호출 실패: %s", exc)
        answer_text = "지금 답변을 만들 수 없습니다. 잠시 후 다시 시도해 주세요."

    assistant_message = ChatMessage(
        chat_session_id=session_id,
        role="assistant",
        content=answer_text,
        related_analysis_id=latest_analysis.analysis_id if latest_analysis else None,
        citations_json=citations,
    )
    db.add(assistant_message)
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return {
        "session_id": session.chat_session_id,
        "user_message_id": user_message.message_id,
        "assistant_message_id": assistant_message.message_id,
        "answer": answer_text,
        "citations": citations,
        "intent": intent_value,
    }


@router.post("/chat-sessions/{session_id}/stream-reply")
def create_chat_stream_reply(
    session_id: UUID,
    payload: ChatReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.chat_session_id == session_id,
            ChatSession.user_id == current_user.user_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")

    latest_analysis = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == session.note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc().nullslast(), Analysis.created_at.desc())
        .first()
    )

    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
        .all()
    )
    recent_messages = list(reversed(recent))

    user_message = ChatMessage(
        chat_session_id=session_id,
        role="user",
        content=payload.question.strip(),
        related_analysis_id=latest_analysis.analysis_id if latest_analysis else None,
    )
    db.add(user_message)
    db.commit()

    # Capture values for the generator (no DB object references across sessions)
    user_id = current_user.user_id
    note_id = session.note_id
    analysis_id = latest_analysis.analysis_id if latest_analysis else None
    rag_indexed = latest_analysis.rag_indexed_at if latest_analysis else None
    question = payload.question.strip()

    def generate():
        tokens: list[str] = []

        try:
            if latest_analysis is not None and rag_indexed is None:
                msg = "분석은 완료됐지만 챗봇 자료를 준비 중입니다. 1~2분 뒤 다시 시도해 주세요."
                tokens.append(msg)
                yield f"data: {json.dumps({'type': 'token', 'token': msg}, ensure_ascii=False)}\n\n"
            else:
                gen_db = SessionLocal()
                try:
                    ctx = prepare_rag_context(
                        gen_db,
                        user_id=user_id,
                        note_id=note_id,
                        question=question,
                        recent_messages=recent_messages,
                    )
                finally:
                    gen_db.close()

                if ctx is None:
                    msg = "분석 결과에서 관련 자료를 찾지 못했습니다. 다른 표현으로 다시 질문해 주세요."
                    tokens.append(msg)
                    yield f"data: {json.dumps({'type': 'token', 'token': msg}, ensure_ascii=False)}\n\n"
                else:
                    for token in stream_chat_text(
                        system_prompt=STREAM_SYSTEM_PROMPT,
                        user_prompt=ctx["user_prompt"],
                        max_tokens=900,
                        temperature=0.2,
                    ):
                        tokens.append(token)
                        yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"

        except Exception as exc:
            logger.warning("스트리밍 LLM 실패: %s", exc)
            msg = "지금 답변을 만들 수 없습니다. 잠시 후 다시 시도해 주세요."
            tokens.append(msg)
            yield f"data: {json.dumps({'type': 'token', 'token': msg}, ensure_ascii=False)}\n\n"

        answer_text = "".join(tokens)
        try:
            save_db = SessionLocal()
            try:
                asst_msg = ChatMessage(
                    chat_session_id=session_id,
                    role="assistant",
                    content=answer_text,
                    related_analysis_id=analysis_id,
                    citations_json=[],
                )
                chat_session = (
                    save_db.query(ChatSession)
                    .filter(ChatSession.chat_session_id == session_id)
                    .first()
                )
                save_db.add(asst_msg)
                if chat_session:
                    chat_session.updated_at = datetime.now(timezone.utc)
                save_db.commit()
            finally:
                save_db.close()
        except Exception as exc:
            logger.error("어시스턴트 메시지 저장 실패: %s", exc)

        yield f"data: {json.dumps({'type': 'done', 'citations': []}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
