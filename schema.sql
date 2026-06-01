-- SpeechPT Database Schema
-- Generated from SQLAlchemy models

-- Users table
CREATE TABLE users (
        user_id UUID NOT NULL,
        email VARCHAR(100) NOT NULL,
        password_hash VARCHAR(255),
        name VARCHAR(100) NOT NULL,
        provider VARCHAR(20) NOT NULL,
        provider_id VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (user_id),
        UNIQUE (email)
);

-- Notes table
CREATE TABLE notes (
        note_id UUID NOT NULL,
        user_id UUID NOT NULL,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE,
        PRIMARY KEY (note_id),
        FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Uploads table
CREATE TABLE uploads (
        upload_id UUID NOT NULL,
        user_id UUID NOT NULL,
        note_id UUID,
        kind VARCHAR(20) NOT NULL,
        storage VARCHAR(20) NOT NULL,
        bucket VARCHAR(200) NOT NULL,
        object_key VARCHAR(500) NOT NULL,
        original_filename VARCHAR(255) NOT NULL,
        url VARCHAR(1000),
        content_type VARCHAR(100) NOT NULL,
        size_bytes BIGINT NOT NULL,
        checksum VARCHAR(128),
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (upload_id),
        CONSTRAINT uq_upload_bucket_object_key UNIQUE (bucket, object_key),
        FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY(note_id) REFERENCES notes (note_id) ON DELETE SET NULL
);

-- Analyses table
CREATE TABLE analyses (
        analysis_id UUID NOT NULL,
        note_id UUID NOT NULL,
        user_id UUID NOT NULL,
        document_upload_id UUID NOT NULL,
        audio_upload_id UUID NOT NULL,
        pipeline_version VARCHAR(50) NOT NULL,
        model_version_ce VARCHAR(100),
        model_version_ae VARCHAR(100),
        status VARCHAR(20) NOT NULL,
        progress INTEGER NOT NULL,
        stage VARCHAR(20) NOT NULL,
        trigger_type VARCHAR(20),
        worker_id VARCHAR(100),
        error_code VARCHAR(50),
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        started_at TIMESTAMP WITH TIME ZONE,
        finished_at TIMESTAMP WITH TIME ZONE,
        PRIMARY KEY (analysis_id),
        CONSTRAINT ck_analysis_progress_range CHECK (progress >= 0 AND progress <= 100),
        FOREIGN KEY(note_id) REFERENCES notes (note_id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY(document_upload_id) REFERENCES uploads (upload_id) ON DELETE RESTRICT,
        FOREIGN KEY(audio_upload_id) REFERENCES uploads (upload_id) ON DELETE RESTRICT
);

-- Indexes
CREATE INDEX ix_upload_note_id ON uploads (note_id);
CREATE INDEX ix_upload_note_kind ON uploads (note_id, kind);
CREATE INDEX ix_upload_created_at ON uploads (created_at);
CREATE INDEX ix_analysis_note_id ON analyses (note_id);
CREATE INDEX ix_analysis_status ON analyses (status);
CREATE INDEX ix_analysis_created_at ON analyses (created_at);

-- ─────────────────────────────────────────────────────────────
-- RAG (Retrieval-Augmented Generation) for chat
-- ─────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS vector;

-- analyses.rag_indexed_at: 챗 응답이 가능한 상태인지 판단용
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS rag_indexed_at TIMESTAMP WITH TIME ZONE;

-- chat_messages.citations_json: assistant 메시지에 인용 정보 부착
ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS citations_json JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE rag_chunks (
    chunk_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(user_id)        ON DELETE CASCADE,
    note_id       UUID NOT NULL REFERENCES notes(note_id)        ON DELETE CASCADE,
    analysis_id   UUID          REFERENCES analyses(analysis_id) ON DELETE CASCADE,
    chunk_type    VARCHAR(30) NOT NULL,
    chunk_key     VARCHAR(200) NOT NULL,
    slide_id      INTEGER,
    start_sec     INTEGER,
    end_sec       INTEGER,
    attempt_index INTEGER,
    content       TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding     VECTOR(1536) NOT NULL,
    content_hash  VARCHAR(64),
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    -- analysis별 청크의 고유 키 (chunk_key가 NULL이 아니라 안전)
    CONSTRAINT uq_rag_analysis_chunk UNIQUE (analysis_id, chunk_type, chunk_key),
    -- note 단위 공유 청크(slide_text 등): analysis_id가 NULL일 때 별도 유니크
    CONSTRAINT uq_rag_note_shared_chunk UNIQUE (note_id, chunk_type, chunk_key)
);

CREATE INDEX ix_rag_user_note     ON rag_chunks (user_id, note_id);
CREATE INDEX ix_rag_analysis      ON rag_chunks (analysis_id);
CREATE INDEX ix_rag_note_type     ON rag_chunks (note_id, chunk_type);
CREATE INDEX ix_rag_embedding     ON rag_chunks USING hnsw (embedding vector_cosine_ops);