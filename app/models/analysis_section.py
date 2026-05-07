import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class AnalysisSection(Base):
    __tablename__ = "analysis_sections"

    __table_args__ = (
        Index("ix_analysis_sections_analysis_id", "analysis_id"),
    )

    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_time_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slide_range_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    targets_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    feedback_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    score_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="sections")
    practice_sessions = relationship("PracticeSession", back_populates="section")
    chat_messages = relationship("ChatMessage", back_populates="related_section")
