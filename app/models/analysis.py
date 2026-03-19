import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class Analysis(Base):
    __tablename__ = "analyses"

    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_analysis_progress_range"),
        Index("ix_analysis_note_id", "note_id"),
        Index("ix_analysis_status", "status"),
        Index("ix_analysis_created_at", "created_at"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.note_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.upload_id", ondelete="RESTRICT"),
        nullable=False,
    )
    audio_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.upload_id", ondelete="RESTRICT"),
        nullable=False,
    )
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version_ce: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version_ae: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(nullable=False, default=0)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="ingest")
    trigger_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="analyses")
    note = relationship("Note", back_populates="analyses")