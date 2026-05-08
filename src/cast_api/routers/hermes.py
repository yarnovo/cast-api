"""Hermes / Skills / Tools router · 老板 5-9 拍 · akong-hermes 抽象的 RDS endpoint。

Endpoints:
  Hermes
    POST   /api/hermes                 创建 (idempotent 通过 id_override / static_ref)
    GET    /api/hermes                 list (?owner_user_id= / ?agent_id= / ?static_ref=)
    GET    /api/hermes/{id}            get one
    PUT    /api/hermes/{id}            update (含 skills/tools 全量替换)
    DELETE /api/hermes/{id}

  Skills (akong_skills 表 · 不跟老 platform tools 表冲突)
    POST   /api/skills
    GET    /api/skills                 list (?owner_user_id= / ?source= / ?agent_id=)
    GET    /api/skills/{id}
    DELETE /api/skills/{id}

  Tools (akong_tools 表)
    POST   /api/tools                  注: 跟老 /api/tools (platform registry · routers/tools.py) prefix 重叠 ·
                                       本仓走 /api/tools 是 platform tools list · /api/akong-tools 是新表
                                       (避免冲突 · 新表用独立 prefix)

  Agent ↔ Skill / Tool 关联
    POST   /api/agents/{agent_id}/skills       link 关联
    DELETE /api/agents/{agent_id}/skills/{skill_id}
    POST   /api/agents/{agent_id}/tools-link   注: 老 router 已有 POST /api/agents/{id}/tools (platform) ·
                                                避免歧义 · 本路径用 -link 后缀挂 akong_tools
    DELETE /api/agents/{agent_id}/tools-link/{tool_id}
"""

from __future__ import annotations

import json
from secrets import token_urlsafe
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db


router = APIRouter(tags=["hermes"])


def _new_id(prefix: str) -> str:
    return f"{prefix}_{token_urlsafe(8)}"


def _serialize_extra(extra: dict | None) -> str | None:
    if extra is None:
        return None
    return json.dumps(extra, ensure_ascii=False)


def _deserialize_extra(extra_json: str | None) -> dict:
    if not extra_json:
        return {}
    try:
        return json.loads(extra_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def _hermes_to_public(
    h: models.Hermes,
    *,
    skills: list[models.AgentSkill] | None = None,
    tools: list[models.AgentAkongTool] | None = None,
    skill_rows: dict[str, models.AkongSkill] | None = None,
    tool_rows: dict[str, models.AkongTool] | None = None,
) -> schemas.HermesPublic:
    skills = skills or []
    tools = tools or []
    skill_rows = skill_rows or {}
    tool_rows = tool_rows or {}

    skill_refs: list[schemas.SkillRefPublic] = []
    for link in skills:
        sk = skill_rows.get(link.skill_id)
        skill_refs.append(schemas.SkillRefPublic(
            id=link.skill_id,
            source=link.source,
            static_ref=sk.static_ref if sk else None,
            config=json.loads(link.config_json) if link.config_json else {},
        ))

    tool_refs: list[schemas.ToolRefPublic] = []
    for link in tools:
        tl = tool_rows.get(link.tool_id)
        tool_refs.append(schemas.ToolRefPublic(
            id=link.tool_id,
            source=link.source,
            static_ref=tl.static_ref if tl else None,
            config=json.loads(link.config_json) if link.config_json else {},
        ))

    return schemas.HermesPublic(
        id=h.id,
        agent_id=h.agent_id,
        name=h.name,
        soul=h.soul,
        playbook=h.playbook,
        style=h.style,
        static_ref=h.static_ref,
        owner_user_id=h.owner_user_id,
        extra=_deserialize_extra(h.extra_json),
        skills=skill_refs,
        tools=tool_refs,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


def _load_hermes_with_relations(db: Session, hermes_id: str) -> tuple[
    models.Hermes,
    list[models.AgentSkill],
    list[models.AgentAkongTool],
    dict[str, models.AkongSkill],
    dict[str, models.AkongTool],
]:
    h = db.get(models.Hermes, hermes_id)
    if not h:
        raise HTTPException(404, f"hermes not found: {hermes_id}")
    if not h.agent_id:
        return h, [], [], {}, {}

    skills = db.execute(
        select(models.AgentSkill).where(models.AgentSkill.agent_id == h.agent_id)
    ).scalars().all()
    tools = db.execute(
        select(models.AgentAkongTool).where(models.AgentAkongTool.agent_id == h.agent_id)
    ).scalars().all()

    skill_ids = [s.skill_id for s in skills]
    tool_ids = [t.tool_id for t in tools]
    skill_rows: dict[str, models.AkongSkill] = {}
    tool_rows: dict[str, models.AkongTool] = {}
    if skill_ids:
        for r in db.execute(
            select(models.AkongSkill).where(models.AkongSkill.id.in_(skill_ids))
        ).scalars().all():
            skill_rows[r.id] = r
    if tool_ids:
        for r in db.execute(
            select(models.AkongTool).where(models.AkongTool.id.in_(tool_ids))
        ).scalars().all():
            tool_rows[r.id] = r

    return h, list(skills), list(tools), skill_rows, tool_rows


def _replace_skill_links(
    db: Session,
    agent_id: str,
    refs: list[schemas.SkillRefBody],
) -> None:
    """全量替换 agent_skills 关联 · 同时确保 skill row 存在 (static 自动 upsert minimal)。"""
    # 删旧
    db.query(models.AgentSkill).filter(models.AgentSkill.agent_id == agent_id).delete()

    for ref in refs:
        if ref.kind == "static":
            if not ref.static_ref:
                raise HTTPException(422, "static SkillRef requires static_ref")
            sid = f"sk_static_{ref.static_ref.replace('::', '_').replace('.', '_').replace('-', '_')}"[:32]
            existing = db.get(models.AkongSkill, sid)
            if not existing:
                db.add(models.AkongSkill(
                    id=sid,
                    name=ref.static_ref.split("::")[-1],
                    sop_markdown="",
                    source="static",
                    static_ref=ref.static_ref,
                ))
                db.flush()
        else:
            if not ref.skill_id:
                raise HTTPException(422, "dynamic SkillRef requires skill_id")
            sid = ref.skill_id
            if not db.get(models.AkongSkill, sid):
                raise HTTPException(404, f"dynamic skill not found: {sid}")

        db.add(models.AgentSkill(
            agent_id=agent_id,
            skill_id=sid,
            source=ref.kind,
            config_json=json.dumps(ref.config, ensure_ascii=False) if ref.config else None,
        ))


def _replace_tool_links(
    db: Session,
    agent_id: str,
    refs: list[schemas.ToolRefBody],
) -> None:
    db.query(models.AgentAkongTool).filter(models.AgentAkongTool.agent_id == agent_id).delete()

    for ref in refs:
        if ref.kind == "static":
            if not ref.static_ref:
                raise HTTPException(422, "static ToolRef requires static_ref")
            tid = f"tl_static_{ref.static_ref.replace('.', '_').replace('-', '_')}"[:32]
            existing = db.get(models.AkongTool, tid)
            if not existing:
                db.add(models.AkongTool(
                    id=tid,
                    name=ref.static_ref,
                    kind="builtin",
                    spec_json="{}",
                    source="static",
                    static_ref=ref.static_ref,
                ))
                db.flush()
        else:
            if not ref.tool_id:
                raise HTTPException(422, "dynamic ToolRef requires tool_id")
            tid = ref.tool_id
            if not db.get(models.AkongTool, tid):
                raise HTTPException(404, f"dynamic tool not found: {tid}")

        db.add(models.AgentAkongTool(
            agent_id=agent_id,
            tool_id=tid,
            source=ref.kind,
            config_json=json.dumps(ref.config, ensure_ascii=False) if ref.config else None,
        ))


# ====================== Hermes ======================


@router.post("/api/hermes", response_model=schemas.HermesPublic, status_code=201)
def create_hermes(
    body: schemas.HermesCreate,
    db: Session = Depends(get_db),
) -> schemas.HermesPublic:
    hid = body.id or _new_id("hm")
    if db.get(models.Hermes, hid):
        raise HTTPException(409, f"hermes id already exists: {hid}")
    if body.agent_id and not db.get(models.Agent, body.agent_id):
        raise HTTPException(404, f"agent not found: {body.agent_id}")
    if body.owner_user_id and not db.get(models.User, body.owner_user_id):
        raise HTTPException(404, f"owner not found: {body.owner_user_id}")

    h = models.Hermes(
        id=hid,
        agent_id=body.agent_id,
        name=body.name,
        soul=body.soul,
        playbook=body.playbook,
        style=body.style,
        static_ref=body.static_ref,
        owner_user_id=body.owner_user_id,
        extra_json=_serialize_extra(body.extra),
    )
    db.add(h)
    db.flush()

    if body.agent_id:
        _replace_skill_links(db, body.agent_id, body.skills)
        _replace_tool_links(db, body.agent_id, body.tools)

    db.commit()
    db.refresh(h)
    h, sk, tl, srs, trs = _load_hermes_with_relations(db, h.id)
    return _hermes_to_public(h, skills=sk, tools=tl, skill_rows=srs, tool_rows=trs)


@router.get("/api/hermes", response_model=list[schemas.HermesPublic])
def list_hermes(
    owner_user_id: str | None = Query(None),
    agent_id: str | None = Query(None),
    static_ref: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[schemas.HermesPublic]:
    stmt = select(models.Hermes)
    if owner_user_id is not None:
        stmt = stmt.where(models.Hermes.owner_user_id == owner_user_id)
    if agent_id is not None:
        stmt = stmt.where(models.Hermes.agent_id == agent_id)
    if static_ref is not None:
        stmt = stmt.where(models.Hermes.static_ref == static_ref)
    stmt = stmt.order_by(models.Hermes.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    out: list[schemas.HermesPublic] = []
    for h in rows:
        h2, sk, tl, srs, trs = _load_hermes_with_relations(db, h.id)
        out.append(_hermes_to_public(h2, skills=sk, tools=tl, skill_rows=srs, tool_rows=trs))
    return out


@router.get("/api/hermes/{hermes_id}", response_model=schemas.HermesPublic)
def get_hermes(hermes_id: str, db: Session = Depends(get_db)) -> schemas.HermesPublic:
    h, sk, tl, srs, trs = _load_hermes_with_relations(db, hermes_id)
    return _hermes_to_public(h, skills=sk, tools=tl, skill_rows=srs, tool_rows=trs)


@router.put("/api/hermes/{hermes_id}", response_model=schemas.HermesPublic)
def update_hermes(
    hermes_id: str,
    body: schemas.HermesUpdate,
    db: Session = Depends(get_db),
) -> schemas.HermesPublic:
    h = db.get(models.Hermes, hermes_id)
    if not h:
        raise HTTPException(404, f"hermes not found: {hermes_id}")

    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        h.name = data["name"]
    if "soul" in data:
        h.soul = data["soul"]
    if "playbook" in data:
        h.playbook = data["playbook"]
    if "style" in data:
        h.style = data["style"]
    if "extra" in data:
        h.extra_json = _serialize_extra(data["extra"])

    if "skills" in data and h.agent_id:
        _replace_skill_links(db, h.agent_id, body.skills or [])
    if "tools" in data and h.agent_id:
        _replace_tool_links(db, h.agent_id, body.tools or [])

    db.commit()
    db.refresh(h)
    h2, sk, tl, srs, trs = _load_hermes_with_relations(db, hermes_id)
    return _hermes_to_public(h2, skills=sk, tools=tl, skill_rows=srs, tool_rows=trs)


@router.delete("/api/hermes/{hermes_id}", status_code=204)
def delete_hermes(hermes_id: str, db: Session = Depends(get_db)) -> None:
    h = db.get(models.Hermes, hermes_id)
    if not h:
        raise HTTPException(404, f"hermes not found: {hermes_id}")
    db.delete(h)
    db.commit()


# ====================== akong_skills ======================


@router.post("/api/skills", response_model=schemas.AkongSkillPublic, status_code=201)
def create_skill(
    body: schemas.AkongSkillCreate,
    db: Session = Depends(get_db),
) -> schemas.AkongSkillPublic:
    sid = body.id or _new_id("sk")
    if db.get(models.AkongSkill, sid):
        raise HTTPException(409, f"skill id already exists: {sid}")
    if body.owner_user_id and not db.get(models.User, body.owner_user_id):
        raise HTTPException(404, f"owner not found: {body.owner_user_id}")

    sk = models.AkongSkill(
        id=sid,
        name=body.name,
        sop_markdown=body.sop_markdown,
        source=body.source,
        static_ref=body.static_ref,
        code_python=body.code_python,
        owner_user_id=body.owner_user_id,
    )
    db.add(sk)
    db.commit()
    db.refresh(sk)
    return schemas.AkongSkillPublic.model_validate(sk)


@router.get("/api/skills", response_model=list[schemas.AkongSkillPublic])
def list_skills(
    owner_user_id: str | None = Query(None),
    source: str | None = Query(None),
    agent_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[schemas.AkongSkillPublic]:
    if agent_id:
        link_ids = db.execute(
            select(models.AgentSkill.skill_id).where(models.AgentSkill.agent_id == agent_id)
        ).scalars().all()
        if not link_ids:
            return []
        rows = db.execute(
            select(models.AkongSkill).where(models.AkongSkill.id.in_(link_ids)).limit(limit)
        ).scalars().all()
        return [schemas.AkongSkillPublic.model_validate(r) for r in rows]

    stmt = select(models.AkongSkill)
    if owner_user_id is not None:
        stmt = stmt.where(models.AkongSkill.owner_user_id == owner_user_id)
    if source is not None:
        stmt = stmt.where(models.AkongSkill.source == source)
    stmt = stmt.order_by(models.AkongSkill.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [schemas.AkongSkillPublic.model_validate(r) for r in rows]


@router.get("/api/skills/{skill_id}", response_model=schemas.AkongSkillPublic)
def get_skill(skill_id: str, db: Session = Depends(get_db)) -> schemas.AkongSkillPublic:
    sk = db.get(models.AkongSkill, skill_id)
    if not sk:
        raise HTTPException(404, f"skill not found: {skill_id}")
    return schemas.AkongSkillPublic.model_validate(sk)


@router.delete("/api/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: str, db: Session = Depends(get_db)) -> None:
    sk = db.get(models.AkongSkill, skill_id)
    if not sk:
        raise HTTPException(404, f"skill not found: {skill_id}")
    db.delete(sk)
    db.commit()


# ====================== akong_tools ======================
# 注: 老 routers/tools.py 占了 /api/tools (platform tools registry) ·
# 本表 (akong_tools · 含 webhook / dynamic_python) 走 /api/akong-tools 区分。


@router.post("/api/akong-tools", response_model=schemas.AkongToolPublic, status_code=201)
def create_akong_tool(
    body: schemas.AkongToolCreate,
    db: Session = Depends(get_db),
) -> schemas.AkongToolPublic:
    tid = body.id or _new_id("tl")
    if db.get(models.AkongTool, tid):
        raise HTTPException(409, f"tool id already exists: {tid}")
    if body.kind not in {"builtin", "webhook", "http_api", "dynamic_python"}:
        raise HTTPException(422, f"invalid kind: {body.kind}")

    spec_str = body.spec_json if isinstance(body.spec_json, str) else json.dumps(body.spec_json, ensure_ascii=False)

    tl = models.AkongTool(
        id=tid,
        name=body.name,
        kind=body.kind,
        spec_json=spec_str,
        static_ref=body.static_ref,
        code_python=body.code_python,
        webhook_url=body.webhook_url,
        source=body.source,
        owner_user_id=body.owner_user_id,
    )
    db.add(tl)
    db.commit()
    db.refresh(tl)
    return schemas.AkongToolPublic.model_validate(tl)


@router.get("/api/akong-tools", response_model=list[schemas.AkongToolPublic])
def list_akong_tools(
    owner_user_id: str | None = Query(None),
    source: str | None = Query(None),
    kind: str | None = Query(None),
    agent_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[schemas.AkongToolPublic]:
    if agent_id:
        link_ids = db.execute(
            select(models.AgentAkongTool.tool_id).where(models.AgentAkongTool.agent_id == agent_id)
        ).scalars().all()
        if not link_ids:
            return []
        rows = db.execute(
            select(models.AkongTool).where(models.AkongTool.id.in_(link_ids)).limit(limit)
        ).scalars().all()
        return [schemas.AkongToolPublic.model_validate(r) for r in rows]

    stmt = select(models.AkongTool)
    if owner_user_id is not None:
        stmt = stmt.where(models.AkongTool.owner_user_id == owner_user_id)
    if source is not None:
        stmt = stmt.where(models.AkongTool.source == source)
    if kind is not None:
        stmt = stmt.where(models.AkongTool.kind == kind)
    stmt = stmt.order_by(models.AkongTool.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [schemas.AkongToolPublic.model_validate(r) for r in rows]


@router.get("/api/akong-tools/{tool_id}", response_model=schemas.AkongToolPublic)
def get_akong_tool(tool_id: str, db: Session = Depends(get_db)) -> schemas.AkongToolPublic:
    tl = db.get(models.AkongTool, tool_id)
    if not tl:
        raise HTTPException(404, f"tool not found: {tool_id}")
    return schemas.AkongToolPublic.model_validate(tl)


@router.delete("/api/akong-tools/{tool_id}", status_code=204)
def delete_akong_tool(tool_id: str, db: Session = Depends(get_db)) -> None:
    tl = db.get(models.AkongTool, tool_id)
    if not tl:
        raise HTTPException(404, f"tool not found: {tool_id}")
    db.delete(tl)
    db.commit()


# ====================== agent ↔ skill / tool 关联 ======================


@router.post("/api/agents/{agent_id}/skills", status_code=201)
def link_skill(
    agent_id: str,
    body: schemas.AgentSkillLink,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not db.get(models.Agent, agent_id):
        raise HTTPException(404, f"agent not found: {agent_id}")
    if not db.get(models.AkongSkill, body.skill_id):
        raise HTTPException(404, f"skill not found: {body.skill_id}")
    if db.get(models.AgentSkill, (agent_id, body.skill_id)):
        raise HTTPException(409, "link already exists")

    db.add(models.AgentSkill(
        agent_id=agent_id,
        skill_id=body.skill_id,
        source=body.source,
        config_json=json.dumps(body.config, ensure_ascii=False) if body.config else None,
    ))
    db.commit()
    return {"agent_id": agent_id, "skill_id": body.skill_id, "linked": True}


@router.delete("/api/agents/{agent_id}/skills/{skill_id}", status_code=204)
def unlink_skill(
    agent_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
) -> None:
    link = db.get(models.AgentSkill, (agent_id, skill_id))
    if not link:
        raise HTTPException(404, "link not found")
    db.delete(link)
    db.commit()


@router.post("/api/agents/{agent_id}/tools-link", status_code=201)
def link_akong_tool(
    agent_id: str,
    body: schemas.AgentToolLink,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not db.get(models.Agent, agent_id):
        raise HTTPException(404, f"agent not found: {agent_id}")
    if not db.get(models.AkongTool, body.tool_id):
        raise HTTPException(404, f"tool not found: {body.tool_id}")
    if db.get(models.AgentAkongTool, (agent_id, body.tool_id)):
        raise HTTPException(409, "link already exists")

    db.add(models.AgentAkongTool(
        agent_id=agent_id,
        tool_id=body.tool_id,
        source=body.source,
        config_json=json.dumps(body.config, ensure_ascii=False) if body.config else None,
    ))
    db.commit()
    return {"agent_id": agent_id, "tool_id": body.tool_id, "linked": True}


@router.delete("/api/agents/{agent_id}/tools-link/{tool_id}", status_code=204)
def unlink_akong_tool(
    agent_id: str,
    tool_id: str,
    db: Session = Depends(get_db),
) -> None:
    link = db.get(models.AgentAkongTool, (agent_id, tool_id))
    if not link:
        raise HTTPException(404, "link not found")
    db.delete(link)
    db.commit()
