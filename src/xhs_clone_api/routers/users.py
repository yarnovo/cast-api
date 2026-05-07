from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=schemas.UserPublic)
def get_user(user_id: str, db: Session = Depends(get_db)) -> schemas.UserPublic:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return schemas.UserPublic.model_validate(user)


@router.get("/{user_id}/notes", response_model=list[schemas.NoteSummary])
def list_user_notes(user_id: str, db: Session = Depends(get_db)) -> list[schemas.NoteSummary]:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    rows = db.execute(
        select(models.Note)
        .options(selectinload(models.Note.author))
        .where(models.Note.author_id == user_id)
        .order_by(models.Note.created_at.desc())
    ).scalars().all()
    return [schemas.NoteSummary.model_validate(n) for n in rows]
