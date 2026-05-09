"""S3 클라이언트 래퍼 — head_object 검증 + JSON 객체 로드.

업로드용 presigned URL 발행은 routers/upload.py가 직접 수행.
이 모듈은 검증(head)과 결과 읽기(get_json) 유틸만 제공.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

_s3 = boto3.client(
    "s3",
    region_name=_REGION,
    config=Config(signature_version="s3v4"),
)

UPLOADS_BUCKET = os.environ.get("S3_BUCKET_UPLOADS") or os.environ.get("S3_BUCKET", "")
RESULTS_BUCKET = os.environ.get("S3_BUCKET_RESULTS", "speechpt-results")


def head_object(object_key: str, bucket: Optional[str] = None) -> Optional[dict]:
    """S3 객체 메타데이터 조회. 없으면 None."""
    target_bucket = bucket or UPLOADS_BUCKET
    if not target_bucket:
        return None
    try:
        return _s3.head_object(Bucket=target_bucket, Key=object_key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def get_object_json(object_key: str, bucket: Optional[str] = None) -> dict:
    """JSON 객체를 dict로 로드."""
    target_bucket = bucket or RESULTS_BUCKET
    obj = _s3.get_object(Bucket=target_bucket, Key=object_key)
<<<<<<< HEAD
    return json.loads(obj["Body"].read())
=======
    return json.loads(obj["Body"].read())
>>>>>>> b7c9480 (버그 수정 및 개선)
