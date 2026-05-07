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