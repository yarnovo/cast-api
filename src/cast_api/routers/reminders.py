from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

# 备注: reminders 给虚拟角色和 owner 用 · 比如"明早 9 点提醒我跟 buyer 沟通工单 X 进度"

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.post("", response_model=schemas.ReminderPublic, status_code=201)
def create_reminder(
    body: schemas.ReminderCreate,
    user_id: str = Query("u01"),
    db: Session = Depends(get_db),
) -> schemas.ReminderPublic:
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")
    r = models.Reminder(user_id=user_id, fire_at=body.fire_at, what=body.what, why=body.why)
    db.add(r)
    db.commit()
    db.refresh(r)
    return schemas.ReminderPublic.model_validate(r)


@router.get("", response_model=list[schemas.ReminderPublic])
def list_reminders(
    user_id: str = Query("u01"),
    pending_only: bool = Query(True),
    db: Session = Depends(get_db),
) -> list[schemas.ReminderPublic]:
    stmt = select(models.Reminder).where(models.Reminder.user_id == user_id)
    if pending_only:
        stmt = stmt.where(models.Reminder.fired.is_(False))
    stmt = stmt.order_by(models.Reminder.fire_at.asc())
    return [schemas.ReminderPublic.model_validate(r) for r in db.execute(stmt).scalars().all()]


@router.get("/due", response_model=list[schemas.ReminderPublic])
def list_due(db: Session = Depends(get_db)) -> list[schemas.ReminderPublic]:
    """所有 user 的已到时但未触发的 reminder · runtime scheduler 拉这个"""
    now = datetime.now(UTC)
    rows = db.execute(
        select(models.Reminder)
        .where(models.Reminder.fired.is_(False), models.Reminder.fire_at <= now)
        .order_by(models.Reminder.fire_at.asc())
    ).scalars().all()
    return [schemas.ReminderPublic.model_validate(r) for r in rows]


@router.post("/{reminder_id}/fire", response_model=schemas.ReminderPublic)
def mark_fired(reminder_id: int, db: Session = Depends(get_db)) -> schemas.ReminderPublic:
    r = db.get(models.Reminder, reminder_id)
    if not r:
        raise HTTPException(404, "reminder not found")
    r.fired = True
    db.commit()
    db.refresh(r)
    return schemas.ReminderPublic.model_validate(r)


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)) -> None:
    r = db.get(models.Reminder, reminder_id)
    if not r:
        raise HTTPException(404, "reminder not found")
    db.delete(r)
    db.commit()
