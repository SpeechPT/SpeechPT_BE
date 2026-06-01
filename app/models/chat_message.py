import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    __table_args__ = (
        Index("ix_chat_messages_chat_session_id", "chat_session_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.chat_session_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="SET NULL"),
        nullable=True,
    )
    related_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sections.section_id", ondelete="SET NULL"),
        nullable=True,
    )
    citations_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
    related_analysis = relationship("Analysis", back_populates="chat_messages")
    related_section = relationship("AnalysisSection", back_populates="chat_messages")
