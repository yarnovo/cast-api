from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=schemas.MessagePublic, status_code=201)
def send_message(
    body: schemas.MessageCreate,
    user_id: str = Query("u01", description="发送方 (MVP hardcode)"),
    db: Session = Depends(get_db),
) -> schemas.MessagePublic:
    if not db.get(models.User, user_id):
        raise HTTPException(404, "sender not found")
    if not db.get(models.User, body.to_user_id):
        raise HTTPException(404, "receiver not found")
    if user_id == body.to_user_id:
        raise HTTPException(400, "cannot send to self")
    msg = models.Message(from_user_id=user_id, to_user_id=body.to_user_id, content=body.content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return schemas.MessagePublic.model_validate(msg)


@router.get("/inbox", response_model=list[schemas.MessagePublic])
def inbox(
    user_id: str = Query("u01"),
    only_unread: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[schemas.MessagePublic]:
    stmt = select(models.Message).where(models.Message.to_user_id == user_id)
    if only_unread:
        stmt = stmt.where(models.Message.read.is_(False))
    stmt = stmt.order_by(models.Message.created_at.desc())
    rows = db.execute(stmt).scalars().all()
    return [schemas.MessagePublic.model_validate(m) for m in rows]


@router.get("/conversations", response_model=list[schemas.ConversationSummary])
def conversations(
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> list[schemas.ConversationSummary]:
    """会话列表 · 按对方分组 · 每组只取最后一条 + 未读数"""
    msgs = db.execute(
        select(models.Message)
        .where(or_(models.Message.from_user_id == user_id, models.Message.to_user_id == user_id))
        .order_by(models.Message.created_at.desc())
    ).scalars().all()

    grouped: dict[str, list[models.Message]] = {}
    for m in msgs:
        other = m.to_user_id if m.from_user_id == user_id else m.from_user_id
        grouped.setdefault(other, []).append(m)

    result = []
    for other_id, conv in grouped.items():
        last = conv[0]
        unread = sum(1 for m in conv if m.to_user_id == user_id and not m.read)
        other = db.get(models.User, other_id)
        if not other:
            continue
        result.append(
            schemas.ConversationSummary(
                other_user=schemas.UserPublic.model_validate(other),
                last_message=schemas.MessagePublic.model_validate(last),
                unread=unread,
            )
        )
    return result


@router.get("/with/{other_user_id}", response_model=list[schemas.MessagePublic])
def conversation_with(
    other_user_id: str,
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> list[schemas.MessagePublic]:
    rows = db.execute(
        select(models.Message)
        .where(
            or_(
                and_(models.Message.from_user_id == user_id, models.Message.to_user_id == other_user_id),
                and_(models.Message.from_user_id == other_user_id, models.Message.to_user_id == user_id),
            )
        )
        .order_by(models.Message.created_at.asc())
    ).scalars().all()
    # 标已读
    for m in rows:
        if m.to_user_id == user_id and not m.read:
            m.read = True
    db.commit()
    return [schemas.MessagePublic.model_validate(m) for m in rows]


@router.get("/unread-count")
def unread_count(user_id: str = Query("u01"), db: Session = Depends(get_db)) -> dict:
    cnt = db.execute(
        select(func.count())
        .select_from(models.Message)
        .where(models.Message.to_user_id == user_id, models.Message.read.is_(False))
    ).scalar_one()
    return {"unread": int(cnt)}
