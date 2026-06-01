"""기존 status='done' 분석들을 RAG 인덱스에 적재.

사용:
  cd SpeechPT_BE
  python -m scripts.backfill_rag                # 모두
  python -m scripts.backfill_rag --note-id ...  # 특정 노트
  python -m scripts.backfill_rag --force        # 이미 인덱싱된 것도 재처리

DB의 analysis_results.report_json + analysis_sections에서 payload를 재구성하므로
워커가 보낸 원본 transcript_segments/highlight_sections이 슬라이드 수준까지 일치하지는
않는다. 대략적인 인덱싱이며, 새 분석은 submit_analysis_result 트리거로 자동 처리된다.
"""
from __future__ import annotations

import argparse
import logging
import sys
from uuid import UUID

from app.db import SessionLocal
from app.models.analysis import Analysis
from app.services.rag_indexer import index_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_rag")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--note-id", type=str, default=None, help="대상 note_id (UUID)")
    parser.add_argument("--force", action="store_true", help="이미 rag_indexed_at이 있어도 재처리")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 건수 (0=무제한)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(Analysis).filter(Analysis.status == "done")
        if args.note_id:
            q = q.filter(Analysis.note_id == UUID(args.note_id))
        if not args.force:
            q = q.filter(Analysis.rag_indexed_at.is_(None))
        q = q.order_by(Analysis.created_at.asc())
        if args.limit:
            q = q.limit(args.limit)
        targets = q.all()
        analysis_ids = [a.analysis_id for a in targets]
    finally:
        db.close()

    logger.info("백필 대상 %d건", len(analysis_ids))
    ok, fail = 0, 0
    for aid in analysis_ids:
        try:
            index_analysis(aid)
            ok += 1
        except Exception:  # noqa: BLE001
            logger.exception("실패: %s", aid)
            fail += 1

    logger.info("완료: 성공 %d, 실패 %d", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
