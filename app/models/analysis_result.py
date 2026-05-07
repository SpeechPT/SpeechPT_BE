import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional

from app.db import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    __table_args__ = (
        CheckConstraint("content_coverage BETWEEN 0 AND 100", name="ck_ar_content_coverage"),
        CheckConstraint("delivery_stability BETWEEN 0 AND 100", name="ck_ar_delivery_stability"),
        CheckConstraint("pacing_score BETWEEN 0 AND 100", name="ck_ar_pacing_score"),
        CheckConstraint("overall_score BETWEEN 0 AND 100", name="ck_ar_overall_score"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"),
        primary_key=True,
    )
    content_coverage: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_stability: Mapped[int] = mapped_column(Integer, nullable=False)
    pacing_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result_blob_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="result")
