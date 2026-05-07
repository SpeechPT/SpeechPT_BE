import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    __table_args__ = (
        Index("ix_practice_sessions_analysis_id", "analysis_id"),
        Index("ix_practice_sessions_user_id", "user_id"),
    )

    practice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sections.section_id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    target_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="practice_sessions")
    section = relationship("AnalysisSection", back_populates="practice_sessions")
    user = relationship("User", back_populates="practice_sessions")
    result = relationship("PracticeResult", back_populates="session", uselist=False, cascade="all, delete-orphan")
