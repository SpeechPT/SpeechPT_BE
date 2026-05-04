import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", ROOT_DIR / "local_uploads"))
API_PUBLIC_BASE_URL = os.getenv("API_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
UPLOAD_STORAGE = os.getenv("UPLOAD_STORAGE", "local").lower()
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION")
S3_PRESIGN_EXPIRATION = int(os.getenv("S3_PRESIGN_EXPIRATION", DUMMY_EXPIRES_IN))

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


def get_local_upload_path(upload_id: UUID, original_filename: str) -> Path:
    safe_name = Path(original_filename).name
    return LOCAL_UPLOAD_DIR / str(upload_id) / safe_name


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
        storage="s3" if UPLOAD_STORAGE == "s3" and S3_BUCKET else "local",
        bucket=S3_BUCKET if UPLOAD_STORAGE == "s3" and S3_BUCKET else "local",
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

    if UPLOAD_STORAGE == "s3" and S3_BUCKET:
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"S3 업로드를 사용하려면 boto3/botocore 설치가 필요합니다: {exc}",
            )

        try:
            s3_client = boto3.session.Session().client(
                "s3",
                region_name=S3_REGION,
                endpoint_url=f"https://s3.{S3_REGION}.amazonaws.com" if S3_REGION else None,
                config=Config(signature_version="s3v4"),
            )
            upload_url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": S3_BUCKET,
                    "Key": object_key,
                    "ContentType": payload.content_type or "application/octet-stream",
                },
                ExpiresIn=S3_PRESIGN_EXPIRATION,
                HttpMethod="PUT",
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"S3 업로드 URL 생성에 실패했습니다: {exc}",
            )
    else:
        upload_url = f"{API_PUBLIC_BASE_URL}/uploads/local/{upload_id}"

    return {
        "upload_id": upload_id,
        "method": "PUT",
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in_sec": S3_PRESIGN_EXPIRATION,
    }


@router.put("/local/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def upload_local_file(
    upload_id: UUID,
    request: Request,
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

    if upload.storage != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="로컬 업로드 대상이 아닙니다.",
        )

    upload_path = get_local_upload_path(upload.upload_id, upload.original_filename)
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with upload_path.open("wb") as file_object:
        async for chunk in request.stream():
            total_bytes += len(chunk)
            file_object.write(chunk)

    if total_bytes != upload.size_bytes:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="전송된 파일 크기가 업로드 요청과 일치하지 않습니다.",
        )

    upload.url = str(upload_path)
    db.commit()
    return None


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
