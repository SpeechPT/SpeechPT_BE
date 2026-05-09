"""SQS 클라이언트 래퍼 — 분석 작업 enqueue."""
from __future__ import annotations

import json
import os

import boto3

_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
_sqs = boto3.client("sqs", region_name=_REGION)

QUEUE_URL = os.environ.get("ANALYSIS_QUEUE_URL", "")


def enqueue_analysis(payload: dict) -> str:
    """분석 작업을 큐에 push. message_id 반환."""
    if not QUEUE_URL:
        raise RuntimeError("ANALYSIS_QUEUE_URL 환경변수가 설정되지 않았습니다.")
    response = _sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(payload, ensure_ascii=False),
    )
<<<<<<< HEAD
    return response["MessageId"]
=======
    return response["MessageId"]
>>>>>>> b7c9480 (버그 수정 및 개선)
