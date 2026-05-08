"""agent harness · chat session 持久化 (REQ-001)

跨 FC 实例多轮对话不丢上下文 · akong-agent-harness 的 RdsSession 调本仓 3 endpoint:
- append: POST   /api/chat_messages
- load:   GET    /api/chat_messages?session_id=...&limit=...&before=...
- clear:  DELETE /api/chat_messages?session_id=...

跟 /api/agents/{id}/memories 是分两层抽象 · 不要"统一":
- chat_messages: 短期 turn · LLM 字面消息
- agent_memories: 长期沉淀 · agent 自己写自己读
"""

from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/chat_messages", tags=["chat_messages"])


_VALID_ROLES = {"user", "assistant", "tool", "system"}


def _new_id() -> str:
    return f"cm_{token_urlsafe(8)}"


@router.post("", response_model=schemas.ChatMessageCreated, status_code=201)
def append_message(
    body: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
) -> schemas.ChatMessageCreated:
    """harness RdsSession.append() · 单条 turn 写入"""
    if body.role not in _VALID_ROLES:
        raise HTTPException(400, f"role must be one of {sorted(_VALID_ROLES)}")
    if not db.get(models.Agent, body.agent_id):
        raise HTTPException(404, "agent not found")
    if body.user_id is not None and not db.get(models.User, body.user_id):
        raise HTTPException(404, "user not found")

    msg = models.ChatMessage(
        id=_new_id(),
        session_id=body.session_id,
        agent_id=body.agent_id,
        user_id=body.user_id,
        role=body.role,
        content=body.content,
        content_json=body.content_json,
        tool_call_id=body.tool_call_id,
        tool_name=body.tool_name,
        metadata_json=body.metadata_json,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return schemas.ChatMessageCreated(id=msg.id, created_at=msg.created_at)


@router.get("", response_model=list[schemas.ChatMessagePublic])
def load_session(
    session_id: str = Query(..., description="按 session 拉 history"),
    limit: int = Query(100, ge=1, le=500),
    before: str | None = Query(
        None,
        description="分页 cursor · 上一页最早一条的 cm_id · 拉它之前的更早 N 条",
    ),
    db: Session = Depends(get_db),
) -> list[schemas.ChatMessagePublic]:
    """harness RdsSession.load() · 按 created_at asc 返 history

    分页语义: 不传 before = 取最新 N 条按时序返 · 传 before = 拉它之前更早的 N 条按时序返。
    (asc 排序便于 LLM 直接喂 messages 数组)
    """
    stmt = select(models.ChatMessage).where(models.ChatMessage.session_id == session_id)

    if before is not None:
        cursor = db.get(models.ChatMessage, before)
        if not cursor:
            raise HTTPException(404, "before cursor not found")
        stmt = stmt.where(models.ChatMessage.created_at < cursor.created_at)

    # 取最新 N 条 · 然后 asc 反转
    stmt = stmt.order_by(models.ChatMessage.created_at.desc()).limit(limit)
    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()
    return [schemas.ChatMessagePublic.model_validate(m) for m in rows]


@router.delete("", response_model=schemas.ChatMessageDeleted)
def clear_session(
    session_id: str = Query(..., description="清整个 session 所有 turn"),
    db: Session = Depends(get_db),
) -> schemas.ChatMessageDeleted:
    """harness RdsSession.clear() · 删整个 session"""
    result = db.execute(
        delete(models.ChatMessage).where(models.ChatMessage.session_id == session_id)
    )
    db.commit()
    return schemas.ChatMessageDeleted(deleted=result.rowcount or 0)
