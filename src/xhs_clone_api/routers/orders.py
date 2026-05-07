"""工单 · buyer 付费给 agent · 真交付走真 owner 或 AI 自动"""

from datetime import datetime, timedelta, UTC
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _new_id() -> str:
    return f"ord_{token_urlsafe(10)}"


@router.post("", response_model=schemas.OrderPublic, status_code=201)
def create_order(
    body: schemas.OrderCreate,
    buyer_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.OrderPublic:
    if not db.get(models.User, buyer_id):
        raise HTTPException(404, "buyer not found")
    agent = db.get(models.Agent, body.agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    svc = db.get(models.Service, body.service_id)
    if not svc or svc.agent_id != body.agent_id or not svc.enabled:
        raise HTTPException(404, "service not found / not for this agent")
    if buyer_id == agent.owner_id:
        raise HTTPException(400, "cannot order from your own agent")

    deadline = datetime.now(UTC) + timedelta(hours=svc.sla_hours)
    order = models.Order(
        id=_new_id(),
        buyer_id=buyer_id,
        agent_id=body.agent_id,
        service_id=body.service_id,
        price_cents=svc.price_cents,
        status="pending",
        requirements=body.requirements,
        deadline_at=deadline,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return schemas.OrderPublic.model_validate(order)


@router.post("/{order_id}/pay", response_model=schemas.OrderPublic)
def mark_paid(order_id: str, db: Session = Depends(get_db)) -> schemas.OrderPublic:
    """MVP · 直接标已付款 (真支付沙箱后接)"""
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    if o.status != "pending":
        raise HTTPException(400, f"order status={o.status} cannot pay")
    o.status = "paid"
    o.paid_at = datetime.now(UTC)
    db.commit()
    db.refresh(o)
    return schemas.OrderPublic.model_validate(o)


@router.post("/{order_id}/accept", response_model=schemas.OrderPublic)
def accept_order(
    order_id: str,
    actor_id: str = Query(..., description="agent owner OR agent xhs_user_id (AI 代接)"),
    db: Session = Depends(get_db),
) -> schemas.OrderPublic:
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    agent = db.get(models.Agent, o.agent_id)
    if actor_id not in {agent.owner_id, agent.xhs_user_id}:
        raise HTTPException(403, "only owner or agent itself can accept")
    if o.status != "paid":
        raise HTTPException(400, f"order status={o.status} cannot accept")
    o.status = "accepted"
    db.commit()
    db.refresh(o)
    return schemas.OrderPublic.model_validate(o)


@router.post("/{order_id}/deliver", response_model=schemas.OrderPublic)
def deliver_order(
    order_id: str,
    body: schemas.OrderDeliver,
    actor_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.OrderPublic:
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    agent = db.get(models.Agent, o.agent_id)
    if actor_id not in {agent.owner_id, agent.xhs_user_id}:
        raise HTTPException(403, "only owner or agent can deliver")
    if o.status not in {"accepted", "in_progress"}:
        raise HTTPException(400, f"order status={o.status} cannot deliver")
    o.deliverables = body.deliverables
    o.status = "delivered"
    o.delivered_at = datetime.now(UTC)
    db.commit()
    db.refresh(o)
    return schemas.OrderPublic.model_validate(o)


@router.post("/{order_id}/complete", response_model=schemas.OrderPublic)
def complete_order(
    order_id: str,
    buyer_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.OrderPublic:
    """buyer 验收 · 资金放款给 owner (MVP 还没真支付 · 只标 status)"""
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    if o.buyer_id != buyer_id:
        raise HTTPException(403, "only buyer can complete")
    if o.status != "delivered":
        raise HTTPException(400, f"order status={o.status} cannot complete")
    o.status = "completed"
    o.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(o)
    return schemas.OrderPublic.model_validate(o)


@router.post("/{order_id}/cancel", response_model=schemas.OrderPublic)
def cancel_order(
    order_id: str,
    actor_id: str = Query(...),
    db: Session = Depends(get_db),
) -> schemas.OrderPublic:
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    agent = db.get(models.Agent, o.agent_id)
    if actor_id not in {o.buyer_id, agent.owner_id, agent.xhs_user_id}:
        raise HTTPException(403, "not allowed to cancel")
    if o.status in {"delivered", "completed", "cancelled", "refunded"}:
        raise HTTPException(400, f"cannot cancel from status={o.status}")
    o.status = "cancelled"
    db.commit()
    db.refresh(o)
    return schemas.OrderPublic.model_validate(o)


@router.get("/mine", response_model=list[schemas.OrderPublic])
def my_orders(
    user_id: str = Query(..., description="作为 buyer 我的订单"),
    db: Session = Depends(get_db),
) -> list[schemas.OrderPublic]:
    rows = db.execute(
        select(models.Order)
        .where(models.Order.buyer_id == user_id)
        .order_by(models.Order.created_at.desc())
    ).scalars().all()
    return [schemas.OrderPublic.model_validate(o) for o in rows]


@router.get("/inbox", response_model=list[schemas.OrderPublic])
def agent_inbox(
    owner_id: str = Query(..., description="作为 agent owner 我的待办订单"),
    db: Session = Depends(get_db),
) -> list[schemas.OrderPublic]:
    rows = db.execute(
        select(models.Order)
        .join(models.Agent, models.Order.agent_id == models.Agent.id)
        .where(models.Agent.owner_id == owner_id)
        .order_by(models.Order.created_at.desc())
    ).scalars().all()
    return [schemas.OrderPublic.model_validate(o) for o in rows]


@router.get("/{order_id}", response_model=schemas.OrderPublic)
def get_order(order_id: str, db: Session = Depends(get_db)) -> schemas.OrderPublic:
    o = db.get(models.Order, order_id)
    if not o:
        raise HTTPException(404, "order not found")
    return schemas.OrderPublic.model_validate(o)
