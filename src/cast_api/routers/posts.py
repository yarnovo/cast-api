"""帖子 (Post) CRUD + 点赞 + 个人主页帖子流"""

import json
import math
import random
from datetime import datetime, UTC
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, distinct, exists
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _new_id(prefix: str = "p") -> str:
    return f"{prefix}_{token_urlsafe(8)}"


def _parse_images(images_json: str | None) -> list[str]:
    if not images_json:
        return []
    try:
        v = json.loads(images_json)
        return v if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def post_to_public(
    post: models.Post,
    *,
    viewer_id: str | None,
    db: Session,
) -> schemas.PostPublic:
    """组装 PostPublic · 含 viewer 视角 is_liked / is_following_author 标记"""
    is_liked = False
    is_following_author = False
    if viewer_id:
        is_liked = db.get(models.PostLike, (viewer_id, post.id)) is not None
        is_following_author = (
            viewer_id != post.author_id
            and db.get(models.Follow, (viewer_id, post.author_id)) is not None
        )
    return schemas.PostPublic(
        id=post.id,
        author=schemas.UserPublic.model_validate(post.author),
        content=post.content,
        images=_parse_images(post.images_json),
        location=post.location,
        likes=post.likes,
        created_at=post.created_at,
        is_liked=is_liked,
        is_following_author=is_following_author,
    )


@router.post("", response_model=schemas.PostPublic, status_code=201)
def create_post(
    body: schemas.PostCreate,
    author_id: str = Query(..., description="当前 active user_id (前端切了哪个就传哪个)"),
    db: Session = Depends(get_db),
) -> schemas.PostPublic:
    if not db.get(models.User, author_id):
        raise HTTPException(404, "author not found")
    if not body.content or not body.content.strip():
        raise HTTPException(400, "content required")
    post = models.Post(
        id=_new_id("p"),
        author_id=author_id,
        content=body.content,
        images_json=json.dumps(body.images) if body.images else None,
        location=body.location,
    )
    db.add(post)
    db.commit()
    db.refresh(post, attribute_names=["author"])
    return post_to_public(post, viewer_id=author_id, db=db)


@router.get("/{post_id}", response_model=schemas.PostPublic)
def get_post(
    post_id: str,
    viewer_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> schemas.PostPublic:
    post = db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "post not found")
    return post_to_public(post, viewer_id=viewer_id, db=db)


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: str,
    author_id: str = Query(..., description="必须 post.author_id 本人"),
    db: Session = Depends(get_db),
) -> None:
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(404, "post not found")
    if post.author_id != author_id:
        raise HTTPException(403, "not your post")
    # 清 likes
    db.execute(
        models.PostLike.__table__.delete().where(models.PostLike.post_id == post_id)
    )
    db.delete(post)
    db.commit()


@router.post("/{post_id}/like", response_model=schemas.PostPublic)
def toggle_like(
    post_id: str,
    user_id: str = Query(..., description="点赞者 user_id (本人)"),
    db: Session = Depends(get_db),
) -> schemas.PostPublic:
    post = db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "post not found")
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")

    existing = db.get(models.PostLike, (user_id, post_id))
    if existing:
        db.delete(existing)
        post.likes = max(0, post.likes - 1)
    else:
        db.add(models.PostLike(user_id=user_id, post_id=post_id))
        post.likes += 1
    db.commit()
    db.refresh(post, attribute_names=["author"])
    return post_to_public(post, viewer_id=user_id, db=db)
