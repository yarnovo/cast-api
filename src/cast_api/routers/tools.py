"""tools registry · 平台级 tools 注册中心 + agent ↔ tool 关联管理

architecture.md §2.4 · runtime 在 tick 时 · 按 agent 当前的 tools 列表注入到 LLM 的 function-calling 参数。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(tags=["tools"])


@router.get("/api/tools", response_model=list[schemas.ToolPublic])
def list_tools(
    platform: str | None = Query(None, description="cast | bilibili-fake | global"),
    scope: str | None = Query(None, description="normal | meta-only | admin"),
    db: Session = Depends(get_db),
) -> list[schemas.ToolPublic]:
    """注册中心查 · 平台 + scope 双过滤"""
    stmt = select(models.Tool)
    if platform:
        stmt = stmt.where(models.Tool.platform == platform)
    if scope:
        stmt = stmt.where(models.Tool.scope == scope)
    stmt = stmt.order_by(models.Tool.id)
    rows = db.execute(stmt).scalars().all()
    return [schemas.ToolPublic.model_validate(t) for t in rows]


@router.get("/api/agents/{agent_id}/tools", response_model=list[schemas.ToolPublic])
def list_agent_tools(
    agent_id: str,
    db: Session = Depends(get_db),
) -> list[schemas.ToolPublic]:
    """该 agent 能调的 tools"""
    if not db.get(models.Agent, agent_id):
        raise HTTPException(404, "agent not found")
    rows = db.execute(
        select(models.Tool)
        .join(models.AgentTool, models.AgentTool.tool_id == models.Tool.id)
        .where(models.AgentTool.agent_id == agent_id)
        .order_by(models.Tool.id)
    ).scalars().all()
    return [schemas.ToolPublic.model_validate(t) for t in rows]


@router.post("/api/agents/{agent_id}/tools/{tool_id}", response_model=schemas.ToolPublic, status_code=201)
def grant_tool(
    agent_id: str,
    tool_id: str,
    db: Session = Depends(get_db),
) -> schemas.ToolPublic:
    if not db.get(models.Agent, agent_id):
        raise HTTPException(404, "agent not found")
    tool = db.get(models.Tool, tool_id)
    if not tool:
        raise HTTPException(404, "tool not found")
    existing = db.get(models.AgentTool, (agent_id, tool_id))
    if existing:
        # 已 grant · 幂等返 200 当前 tool
        return schemas.ToolPublic.model_validate(tool)
    db.add(models.AgentTool(agent_id=agent_id, tool_id=tool_id))
    db.commit()
    return schemas.ToolPublic.model_validate(tool)


@router.delete("/api/agents/{agent_id}/tools/{tool_id}", status_code=204)
def revoke_tool(
    agent_id: str,
    tool_id: str,
    db: Session = Depends(get_db),
) -> None:
    link = db.get(models.AgentTool, (agent_id, tool_id))
    if not link:
        raise HTTPException(404, "agent_tool not found")
    db.delete(link)
    db.commit()
