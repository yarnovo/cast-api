from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=schemas.UserPublic)
def get_user(user_id: str, db: Session = Depends(get_db)) -> schemas.UserPublic:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return schemas.UserPublic.model_validate(user)
