import uuid
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class PracticeResult(Base):
    __tablename__ = "practice_results"

    practice_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    practice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_sessions.practice_session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    avg_wpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_pitch: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    silence_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_hit_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_delta_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    feedback_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    raw_metrics_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("PracticeSession", back_populates="result")
