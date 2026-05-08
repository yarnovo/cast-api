"""C2A2C 虚拟角色管理 · 真人 owner 创建 / 编辑自己的虚拟角色 · 访客浏览市场"""

from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _new_id(prefix: str = "ag") -> str:
    return f"{prefix}_{token_urlsafe(8)}"


def _summary(agent: models.Agent) -> schemas.AgentSummary:
    services = [s for s in agent.services if s.enabled]
    starting = min((s.price_cents for s in services), default=None)
    return schemas.AgentSummary(
        id=agent.id,
        name=agent.name,
        tagline=agent.tagline,
        persona=schemas.UserPublic.model_validate(agent.persona),
        starting_price_cents=starting,
        services_count=len(services),
        status=agent.status,
    )


def _detail(agent: models.Agent) -> schemas.AgentDetail:
    base = _summary(agent)
    return schemas.AgentDetail(
        **base.model_dump(),
        soul=agent.soul,
        playbook=agent.playbook,
        style=agent.style,
        expertise=agent.expertise,
        owner_id=agent.owner_id,
        services=[schemas.ServicePublic.model_validate(s) for s in agent.services if s.enabled],
        created_at=agent.created_at,
    )


@router.get("", response_model=list[schemas.AgentSummary])
def market(
    q: str | None = Query(None, description="搜索 name / tagline / expertise"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[schemas.AgentSummary]:
    """虚拟角色市场首页"""
    stmt = (
        select(models.Agent)
        .options(selectinload(models.Agent.persona), selectinload(models.Agent.services))
        .where(models.Agent.status == "active")
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (models.Agent.name.ilike(like))
            | (models.Agent.tagline.ilike(like))
            | (models.Agent.expertise.ilike(like))
        )
    stmt = stmt.order_by(models.Agent.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [_summary(a) for a in rows]


@router.post("", response_model=schemas.AgentDetail, status_code=201)
def create_agent(
    body: schemas.AgentCreate,
    owner_id: str = Query(..., description="真人 owner user_id"),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    if not db.get(models.User, owner_id):
        raise HTTPException(404, "owner not found")

    # 虚拟角色同时是平台上一个 user · 给他注册一个 user_id (虚拟角色用这个收发私信)
    persona_id = _new_id("u_ag")
    persona = models.User(
        id=persona_id,
        name=body.name,
        avatar=body.avatar,
        bio=body.tagline,
    )
    db.add(persona)

    aid = _new_id("ag")
    agent = models.Agent(
        id=aid,
        owner_id=owner_id,
        persona_user_id=persona_id,
        name=body.name,
        tagline=body.tagline,
        soul=body.soul,
        playbook=body.playbook,
        style=body.style,
        expertise=body.expertise,
        status="active",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent, attribute_names=["persona", "services"])
    return _detail(agent)


@router.get("/mine", response_model=list[schemas.AgentSummary])
def my_agents(
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[schemas.AgentSummary]:
    rows = db.execute(
        select(models.Agent)
        .options(selectinload(models.Agent.persona), selectinload(models.Agent.services))
        .where(models.Agent.owner_id == owner_id)
        .order_by(models.Agent.created_at.desc())
    ).scalars().all()
    return [_summary(a) for a in rows]


@router.get("/{agent_id}", response_model=schemas.AgentDetail)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> schemas.AgentDetail:
    agent = db.execute(
        select(models.Agent)
        .options(selectinload(models.Agent.persona), selectinload(models.Agent.services))
        .where(models.Agent.id == agent_id)
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "agent not found")
    return _detail(agent)


@router.patch("/{agent_id}", response_model=schemas.AgentDetail)
def update_agent(
    agent_id: str,
    body: schemas.AgentUpdate,
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    if agent.owner_id != owner_id:
        raise HTTPException(403, "not your agent")

    data = body.model_dump(exclude_unset=True)
    avatar = data.pop("avatar", None)
    for k, v in data.items():
        setattr(agent, k, v)
    if avatar is not None:
        agent.persona.avatar = avatar
    if "name" in data:
        agent.persona.name = data["name"]
    if "tagline" in data:
        agent.persona.bio = data["tagline"]

    db.commit()
    db.refresh(agent, attribute_names=["persona", "services"])
    return _detail(agent)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
) -> None:
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    if agent.owner_id != owner_id:
        raise HTTPException(403, "not your agent")
    db.delete(agent)
    db.commit()


# === Services 子资源 ===

@router.post("/{agent_id}/services", response_model=schemas.ServicePublic, status_code=201)
def add_service(
    agent_id: str,
    body: schemas.ServiceCreate,
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.ServicePublic:
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    if agent.owner_id != owner_id:
        raise HTTPException(403, "not your agent")
    if body.mode not in {"ai", "human", "hybrid"}:
        raise HTTPException(400, "mode must be ai/human/hybrid")
    svc = models.Service(
        agent_id=agent_id,
        title=body.title,
        description=body.description,
        price_cents=body.price_cents,
        sla_hours=body.sla_hours,
        mode=body.mode,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return schemas.ServicePublic.model_validate(svc)


@router.delete("/{agent_id}/services/{service_id}", status_code=204)
def remove_service(
    agent_id: str,
    service_id: int,
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
) -> None:
    svc = db.get(models.Service, service_id)
    if not svc or svc.agent_id != agent_id:
        raise HTTPException(404, "service not found")
    agent = db.get(models.Agent, agent_id)
    if agent.owner_id != owner_id:
        raise HTTPException(403, "not your agent")
    db.delete(svc)
    db.commit()
