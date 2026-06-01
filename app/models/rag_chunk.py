import uuid
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Minimal pgvector type — server-side cast handles parsing."""

    cache_ok = True

    def __init__(self, dim: int):
        self.dim = dim

    def get_col_spec(self, **kw):
        return f"VECTOR({self.dim})"

    def bind_expression(self, bindvalue):
        from sqlalchemy import cast
        return cast(bindvalue, self)

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return "[" + ",".join(f"{float(x):.7f}" for x in value) + "]"
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return value
            s = value.strip()
            if s.startswith("[") and s.endswith("]"):
                s = s[1:-1]
            if not s:
                return []
            return [float(x) for x in s.split(",")]
        return process


from app.db import Base  # noqa: E402


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    __table_args__ = (
        UniqueConstraint("analysis_id", "chunk_type", "chunk_key", name="uq_rag_analysis_chunk"),
        UniqueConstraint("note_id", "chunk_type", "chunk_key", name="uq_rag_note_shared_chunk"),
        Index("ix_rag_user_note", "user_id", "note_id"),
        Index("ix_rag_analysis", "analysis_id"),
        Index("ix_rag_note_type", "note_id", "chunk_type"),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.note_id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"),
        nullable=True,
    )
    chunk_type: Mapped[str] = mapped_column(String(30), nullable=False)
    chunk_key: Mapped[str] = mapped_column(String(200), nullable=False)
    slide_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempt_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict,
    )
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
