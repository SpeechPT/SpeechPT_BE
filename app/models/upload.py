import uuid
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class Upload(Base):
    __tablename__ = "uploads"

    __table_args__ = (
        UniqueConstraint("bucket", "object_key", name="uq_upload_bucket_object_key"),
        Index("ix_upload_note_id", "note_id"),
        Index("ix_upload_note_kind", "note_id", "kind"),
        Index("ix_upload_created_at", "created_at"),
    )

    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    note_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.note_id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # document, audio, other
    storage: Mapped[str] = mapped_column(String(20), nullable=False, default="s3")
    bucket: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="uploads")
    note = relationship("Note", back_populates="uploads")