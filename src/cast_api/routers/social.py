"""社交关系 · 关注 / 粉丝 / 用户统计 / 用户帖子流 / 3-tab feed"""

import math
import random
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..db import get_db
from .posts import post_to_public

router = APIRouter(tags=["social"])


# === 关注 ===

@router.post("/api/follow")
def toggle_follow(
    follower_id: str = Query(...),
    followee_id: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """切换关注 · 返 { is_following: bool }"""
    if follower_id == followee_id:
        raise HTTPException(400, "cannot follow self")
    if not db.get(models.User, follower_id):
        raise HTTPException(404, "follower not found")
    if not db.get(models.User, followee_id):
        raise HTTPException(404, "followee not found")

    existing = db.get(models.Follow, (follower_id, followee_id))
    if existing:
        db.delete(existing)
        db.commit()
        return {"is_following": False}
    db.add(models.Follow(follower_id=follower_id, followee_id=followee_id))
    db.commit()
    return {"is_following": True}


@router.get("/api/users/{user_id}/followers", response_model=list[schemas.UserPublic])
def list_followers(user_id: str, db: Session = Depends(get_db)) -> list[schemas.UserPublic]:
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")
    rows = db.execute(
        select(models.User)
        .join(models.Follow, models.Follow.follower_id == models.User.id)
        .where(models.Follow.followee_id == user_id)
        .order_by(models.Follow.created_at.desc())
    ).scalars().all()
    return [schemas.UserPublic.model_validate(u) for u in rows]


@router.get("/api/users/{user_id}/following", response_model=list[schemas.UserPublic])
def list_following(user_id: str, db: Session = Depends(get_db)) -> list[schemas.UserPublic]:
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")
    rows = db.execute(
        select(models.User)
        .join(models.Follow, models.Follow.followee_id == models.User.id)
        .where(models.Follow.follower_id == user_id)
        .order_by(models.Follow.created_at.desc())
    ).scalars().all()
    return [schemas.UserPublic.model_validate(u) for u in rows]


@router.get("/api/users/{user_id}/stats", response_model=schemas.UserStats)
def user_stats(user_id: str, db: Session = Depends(get_db)) -> schemas.UserStats:
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")
    posts_count = db.execute(
        select(func.count()).select_from(models.Post).where(models.Post.author_id == user_id)
    ).scalar_one()
    followers_count = db.execute(
        select(func.count()).select_from(models.Follow).where(models.Follow.followee_id == user_id)
    ).scalar_one()
    following_count = db.execute(
        select(func.count()).select_from(models.Follow).where(models.Follow.follower_id == user_id)
    ).scalar_one()
    return schemas.UserStats(
        posts_count=int(posts_count),
        followers_count=int(followers_count),
        following_count=int(following_count),
    )


@router.get("/api/users/{user_id}/posts", response_model=list[schemas.PostPublic])
def user_posts(
    user_id: str,
    viewer_id: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[schemas.PostPublic]:
    """某 user 的所有帖子 · 时间倒序 · 用于个人主页 / MePage 作品 tab"""
    if not db.get(models.User, user_id):
        raise HTTPException(404, "user not found")
    rows = db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.author_id == user_id)
        .order_by(models.Post.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [post_to_public(p, viewer_id=viewer_id, db=db) for p in rows]


# === 3-tab feed ===

def _score_recommend(post: models.Post, now: datetime) -> float:
    """简单推荐打分 v1 · likes * 2 + 100 * exp(-hours / 24) + random(0, 5)"""
    created = post.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    hours = max(0.0, (now - created).total_seconds() / 3600.0)
    return post.likes * 2 + 100.0 * math.exp(-hours / 24.0) + random.uniform(0.0, 5.0)


@router.get("/api/feed", response_model=list[schemas.PostPublic])
def feed(
    type: str = Query("recommend", description="recommend / follow / nearby"),
    user_id: str | None = Query(None, description="viewer user_id · follow / nearby 必填"),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None, description="上一页最后一条 post.id (follow / nearby 用 created_at 倒序游标)"),
    db: Session = Depends(get_db),
) -> list[schemas.PostPublic]:
    if type not in {"recommend", "follow", "nearby"}:
        raise HTTPException(400, "type must be recommend / follow / nearby")

    if type in {"follow", "nearby"} and not user_id:
        raise HTTPException(400, f"user_id required for {type} feed")
    if user_id and not db.get(models.User, user_id):
        raise HTTPException(404, "viewer not found")

    cursor_post = db.get(models.Post, cursor) if cursor else None

    if type == "follow":
        # viewer 关注的所有 followee 的 posts · 时间倒序
        stmt = (
            select(models.Post)
            .options(selectinload(models.Post.author))
            .join(models.Follow, models.Follow.followee_id == models.Post.author_id)
            .where(models.Follow.follower_id == user_id)
            .order_by(models.Post.created_at.desc())
        )
        if cursor_post:
            stmt = stmt.where(models.Post.created_at < cursor_post.created_at)
        rows = db.execute(stmt.limit(limit)).scalars().all()

    elif type == "nearby":
        viewer = db.get(models.User, user_id)
        loc = viewer.location if viewer else None
        stmt = (
            select(models.Post)
            .options(selectinload(models.Post.author))
            .order_by(models.Post.created_at.desc())
        )
        if loc:
            stmt = stmt.where(models.Post.location == loc)
        else:
            # viewer 没填 location · 返 location 字段非空的 distinct 城市最新各 1 条
            stmt = stmt.where(models.Post.location.is_not(None))
        if cursor_post:
            stmt = stmt.where(models.Post.created_at < cursor_post.created_at)
        rows = db.execute(stmt.limit(limit)).scalars().all()

    else:  # recommend
        # 简单算法 · 拉最近 200 条候选 · python 端打分 · 取 top limit · 不上 ML
        stmt = (
            select(models.Post)
            .options(selectinload(models.Post.author))
            .order_by(models.Post.created_at.desc())
            .limit(200)
        )
        if cursor_post:
            stmt = stmt.where(models.Post.created_at < cursor_post.created_at)
        candidates = db.execute(stmt).scalars().all()
        now = datetime.now(UTC)
        candidates.sort(key=lambda p: _score_recommend(p, now), reverse=True)
        rows = candidates[:limit]

    return [post_to_public(p, viewer_id=user_id, db=db) for p in rows]
