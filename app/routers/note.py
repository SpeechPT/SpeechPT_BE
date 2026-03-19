from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteListResponse, NoteResponse, NoteUpdate

# /notes 로 시작하는 노트 관련 API 라우터
router = APIRouter(prefix="/notes", tags=["notes"])

# 임시 고정 user_id, 나중에 auth 붙이면 current_user.user_id 로 교체
DUMMY_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


# 노트 생성 API
@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    # 요청 body 값을 DB 모델 객체로 변환
    note = Note(
        user_id=DUMMY_USER_ID,
        title=payload.title,
        description=payload.description,
    )

    # DB 세션에 추가 후 실제 저장
    db.add(note)
    db.commit()

    # 저장 후 생성된 최신값 다시 읽기
    db.refresh(note)
    return note


# 노트 목록 조회 API
@router.get("", response_model=NoteListResponse)
def list_notes(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # 현재 유저의 노트만 최신순으로 조회
    query = (
        db.query(Note)
        .filter(Note.user_id == DUMMY_USER_ID)
        .order_by(Note.created_at.desc())
    )

    # limit 만큼 목록 조회, total 개수 계산
    notes = query.limit(limit).all()
    total = query.count()

    return {
        "items": notes,
        "total": total,
    }


# 노트 상세 조회 API
@router.get("/{note_id}", response_model=NoteResponse)
def get_note(note_id: UUID, db: Session = Depends(get_db)):
    # note_id 와 user_id 조건으로 단건 조회
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == DUMMY_USER_ID)
        .first()
    )

    # 없으면 404 반환
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="노트를 찾을 수 없습니다.",
        )

    return note


# 노트 부분 수정 API
@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(note_id: UUID, payload: NoteUpdate, db: Session = Depends(get_db)):
    # 수정 대상 노트 조회
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == DUMMY_USER_ID)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="노트를 찾을 수 없습니다.",
        )

    # 값이 들어온 필드만 선택적으로 수정
    if payload.title is not None:
        note.title = payload.title
    if payload.description is not None:
        note.description = payload.description

    # 수정 내용 저장 후 최신값 반환
    db.commit()
    db.refresh(note)
    return note


# 노트 삭제 API
@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, db: Session = Depends(get_db)):
    # 삭제 대상 노트 조회
    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == DUMMY_USER_ID)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="노트를 찾을 수 없습니다.",
        )

    # DB에서 삭제 후 커밋
    db.delete(note)
    db.commit()
    return None