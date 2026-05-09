from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.analysis import Analysis
from app.models.analysis_result import AnalysisResult
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.note import Note
from app.models.user import User
from app.schemas.chat import ChatMessageCreateRequest, ChatReplyRequest, ChatReplyResponse

router = APIRouter(tags=["chat"])


def _build_mock_chat_answer(question: str, analysis: Analysis | None, result_row: AnalysisResult | None) -> str:
    normalized_question = question.strip().lower()

    if analysis is None or result_row is None:
        return (
            "아직 완료된 분석 결과가 없어서 자세한 답변은 어렵습니다. "
            "먼저 문서와 음성을 업로드해 분석을 실행하면, 그 결과를 바탕으로 질문에 답할 수 있습니다."
        )

    report = result_row.report_json or {}
    summary = report.get("summary") or "요약 데이터가 아직 없습니다."
    strengths = report.get("strengths") or []
    improvements = report.get("improvements") or []

    if "요약" in normalized_question or "summary" in normalized_question:
        return f"현재 분석 요약은 다음과 같습니다. {summary}"

    if "강점" in normalized_question or "잘한" in normalized_question:
        if strengths:
            joined = " / ".join(item.get("text", "") for item in strengths[:3] if item.get("text"))
            return f"현재 분석에서 잡힌 주요 강점은 다음과 같습니다. {joined}"
        return "현재 분석 결과에는 강점 데이터가 아직 없습니다."

    if "개선" in normalized_question or "부족" in normalized_question or "고쳐" in normalized_question:
        if improvements:
            joined = " / ".join(item.get("text", "") for item in improvements[:3] if item.get("text"))
            return f"우선 개선이 필요한 포인트는 다음과 같습니다. {joined}"
        return "현재 분석 결과에는 개선 포인트 데이터가 아직 없습니다."

    if "점수" in normalized_question or "스코어" in normalized_question:
        return (
            "현재 점수는 "
            f"내용 커버리지 {result_row.content_coverage}점, "
            f"전달 안정성 {result_row.delivery_stability}점, "
            f"발표 속도 {result_row.pacing_score}점입니다."
        )

    if "대본" in normalized_question or "stt" in normalized_question or "스크립트" in normalized_question:
        transcript = (analysis.transcript or "").strip()
        if transcript:
            excerpt = transcript[:220]
            suffix = "..." if len(transcript) > 220 else ""
            return f"현재 변환된 대본 일부는 다음과 같습니다. {excerpt}{suffix}"
        return "아직 STT 대본이 생성되지 않았습니다."

    return (
        f"질문하신 내용에 대해 현재 분석 기준으로 답하면, {summary} "
        "지금은 임시 응답 로직이라 키워드 중심으로 답하고 있고, 이후 실제 LLM 연결 시 더 자연스럽고 자세한 답변으로 확장할 수 있습니다."
    )


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
            }
            for m in messages
        ],
    }


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

    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.note_id == session.note_id,
            Analysis.user_id == current_user.user_id,
            Analysis.status == "done",
        )
        .order_by(Analysis.finished_at.desc())
        .first()
    )
    result_row = None
    if analysis is not None:
        result_row = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.analysis_id == analysis.analysis_id)
            .first()
        )

    user_message = ChatMessage(
        chat_session_id=session_id,
        role="user",
        content=payload.question.strip(),
        related_analysis_id=analysis.analysis_id if analysis else None,
    )
    db.add(user_message)
    db.flush()

    answer = _build_mock_chat_answer(payload.question, analysis, result_row)
    assistant_message = ChatMessage(
        chat_session_id=session_id,
        role="assistant",
        content=answer,
        related_analysis_id=analysis.analysis_id if analysis else None,
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
        "answer": answer,
    }
