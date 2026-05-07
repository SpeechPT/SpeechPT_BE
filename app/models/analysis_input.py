import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class AnalysisInput(Base):
    __tablename__ = "analysis_inputs"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_path: Mapped[str] = mapped_column(String(500), nullable=False)
    audio_path: Mapped[str] = mapped_column(String(500), nullable=False)
    slide_timestamps_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    whisper_words_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config_yaml_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="input")
