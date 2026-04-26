import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.upload import Upload
from app.models.user import User
from app.schemas.upload import (
    UploadCompleteRequest,
    UploadCompleteResponse,
    UploadListResponse,
    UploadPresignRequest,
    UploadPresignResponse,
    UploadResponse,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])

DUMMY_BUCKET = "speechpt-dev"
DUMMY_EXPIRES_IN = 900

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".ppt", ".pptx"}
ALLOWED_AUDIO_EXTENSIONS = {".wav"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
ALLOWED_AUDIO_MIME_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}


def validate_upload_request(payload: UploadPresignRequest):
    extension = Path(payload.file_name).suffix.lower()
    content_type = payload.content_type or ""

    if payload.kind == "document":
        if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="허용된 문서 형식은 PDF, PPT, PPTX 입니다.",
            )

        if content_type and content_type != "application/octet-stream" and content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="허용된 문서 MIME 타입은 PDF 또는 PPT/PPTX 입니다.",
            )

    elif payload.kind == "audio":
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="허용된 음성 형식은 WAV 입니다.",
            )

        if content_type and content_type != "application/octet-stream" and content_type not in ALLOWED_AUDIO_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="허용된 음성 MIME 타입은 WAV 입니다.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="kind는 document 또는 audio 이어야 합니다.",
        )


@router.post("/presign", response_model=UploadPresignResponse, status_code=status.HTTP_200_OK)
def create_upload_presign(
    payload: UploadPresignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_upload_request(payload)

    upload_id = uuid.uuid4()
    object_key = f"notes/{payload.note_id or 'unassigned'}/uploads/{upload_id}/{payload.file_name}"

    upload = Upload(
        upload_id=upload_id,
        user_id=current_user.user_id,
        note_id=payload.note_id,
        kind=payload.kind,
        storage="s3",
        bucket=DUMMY_BUCKET,
        object_key=object_key,
        original_filename=payload.file_name,
        url=None,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        checksum=None,
        status="pending",
    )
    db.add(upload)
    db.commit()

    upload_url = f"https://example.com/fake-s3-upload/{upload_id}"

    return {
        "upload_id": upload_id,
        "method": "PUT",
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in_sec": DUMMY_EXPIRES_IN,
    }


@router.post("/complete", response_model=UploadCompleteResponse, status_code=status.HTTP_200_OK)
def complete_upload(
    payload: UploadCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = (
        db.query(Upload)
        .filter(Upload.upload_id == payload.upload_id, Upload.user_id == current_user.user_id)
        .first()
    )

    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업로드 정보를 찾을 수 없습니다.",
        )

    upload.status = "uploaded"
    if payload.checksum is not None:
        upload.checksum = payload.checksum

    db.commit()

    return {
        "upload_id": upload.upload_id,
        "status": upload.status,
    }


@router.get("/{upload_id}", response_model=UploadResponse)
def get_upload(
    upload_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = (
        db.query(Upload)
        .filter(Upload.upload_id == upload_id, Upload.user_id == current_user.user_id)
        .first()
    )

    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업로드 정보를 찾을 수 없습니다.",
        )

    return upload


@router.get("/notes/{note_id}", response_model=UploadListResponse)
def list_uploads_by_note(
    note_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Upload)
        .filter(Upload.note_id == note_id, Upload.user_id == current_user.user_id)
        .order_by(Upload.created_at.desc())
    )

    uploads = query.limit(limit).all()
    total = query.count()

    return {
        "items": uploads,
        "total": total,
    }
