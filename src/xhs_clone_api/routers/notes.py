from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=schemas.FeedResponse)
def list_notes(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> schemas.FeedResponse:
    stmt = select(models.Note).options(selectinload(models.Note.author)).order_by(
        models.Note.created_at.desc(), models.Note.id.desc()
    )
    if cursor:
        stmt = stmt.where(models.Note.id < cursor)
    stmt = stmt.limit(limit + 1)
    rows = db.execute(stmt).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if has_more and items else None
    return schemas.FeedResponse(
        items=[schemas.NoteSummary.model_validate(r) for r in items],
        next_cursor=next_cursor,
    )


@router.get("/{note_id}", response_model=schemas.NoteDetail)
def get_note(note_id: str, db: Session = Depends(get_db)) -> schemas.NoteDetail:
    note = db.execute(
        select(models.Note)
        .options(selectinload(models.Note.author))
        .where(models.Note.id == note_id)
    ).scalar_one_or_none()
    if not note:
        raise HTTPException(404, "note not found")
    return schemas.NoteDetail.model_validate(note)


@router.get("/{note_id}/comments", response_model=list[schemas.CommentPublic])
def list_comments(note_id: str, db: Session = Depends(get_db)) -> list[schemas.CommentPublic]:
    rows = db.execute(
        select(models.Comment)
        .options(selectinload(models.Comment.author))
        .where(models.Comment.note_id == note_id)
        .order_by(models.Comment.created_at.desc())
    ).scalars().all()
    return [schemas.CommentPublic.model_validate(c) for c in rows]


@router.post("/{note_id}/comments", response_model=schemas.CommentPublic, status_code=201)
def create_comment(
    note_id: str,
    body: schemas.CommentCreate,
    user_id: str = Query("u01", description="MVP 阶段 hardcode 默认用户"),
    db: Session = Depends(get_db),
) -> schemas.CommentPublic:
    note = db.get(models.Note, note_id)
    if not note:
        raise HTTPException(404, "note not found")
    cnt = db.execute(
        select(func.count()).where(models.Comment.note_id == note_id)
    ).scalar_one()
    cid = f"c-{note_id}-u-{cnt}"
    c = models.Comment(id=cid, note_id=note_id, author_id=user_id, content=body.content)
    db.add(c)
    note.comments_count += 1
    db.commit()
    db.refresh(c, attribute_names=["author"])
    return schemas.CommentPublic.model_validate(c)


@router.post("/{note_id}/like", response_model=schemas.ToggleResponse)
def toggle_like(
    note_id: str,
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> schemas.ToggleResponse:
    note = db.get(models.Note, note_id)
    if not note:
        raise HTTPException(404, "note not found")
    existing = db.execute(
        select(models.Like).where(
            models.Like.user_id == user_id, models.Like.note_id == note_id
        )
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        note.likes = max(0, note.likes - 1)
        active = False
    else:
        db.add(models.Like(user_id=user_id, note_id=note_id))
        note.likes += 1
        active = True
    db.commit()
    return schemas.ToggleResponse(active=active, count=note.likes)


@router.post("/{note_id}/collect", response_model=schemas.ToggleResponse)
def toggle_collect(
    note_id: str,
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> schemas.ToggleResponse:
    note = db.get(models.Note, note_id)
    if not note:
        raise HTTPException(404, "note not found")
    existing = db.execute(
        select(models.Collect).where(
            models.Collect.user_id == user_id, models.Collect.note_id == note_id
        )
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        note.collects = max(0, note.collects - 1)
        active = False
    else:
        db.add(models.Collect(user_id=user_id, note_id=note_id))
        note.collects += 1
        active = True
    db.commit()
    return schemas.ToggleResponse(active=active, count=note.collects)


@router.post("", response_model=schemas.NoteDetail, status_code=201)
def create_note(
    body: schemas.NoteCreate,
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> schemas.NoteDetail:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    cnt = db.execute(select(func.count()).select_from(models.Note)).scalar_one()
    nid = f"n{cnt + 1:03d}"
    note = models.Note(
        id=nid,
        author_id=user_id,
        title=body.title,
        content=body.content,
        cover=body.cover,
        images=body.images,
        tags=body.tags,
        ratio=body.ratio,
    )
    db.add(note)
    db.commit()
    db.refresh(note, attribute_names=["author"])
    return schemas.NoteDetail.model_validate(note)
