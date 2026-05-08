"""Cast C2A2C 平台数据模型 · 用户 / 虚拟角色 / 服务包 / 工单 / 私信 / 提醒"""

from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """平台用户 · 真人 owner / 真人 buyer / 虚拟角色 persona 都用同一张表"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    avatar: Mapped[str] = mapped_column(Text, default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    """私信 · 一对一 DM · 虚拟角色给 owner 发 · buyer 给虚拟角色发 · owner 给 buyer 发"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    sender: Mapped[User] = relationship(foreign_keys=[from_user_id])
    receiver: Mapped[User] = relationship(foreign_keys=[to_user_id])


class Reminder(Base):
    """日历提醒 · 虚拟角色自己设的 / 真人替虚拟角色设的"""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    fire_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text, default="")
    fired: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Agent(Base):
    """C2A2C 虚拟角色 · 真人 owner 创建 · 真人的专业服务代言人

    persona_user_id: 虚拟角色在平台上也是一个 user (有 avatar / 名字) · 用这个 id 发私信 / 发布服务。
    """

    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("persona_user_id", name="uq_agent_persona_user"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    persona_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    tagline: Mapped[str] = mapped_column(String(140), default="")
    soul: Mapped[str] = mapped_column(Text, default="")
    playbook: Mapped[str] = mapped_column(Text, default="")
    style: Mapped[str] = mapped_column(Text, default="")
    expertise: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / paused / draft
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    persona: Mapped[User] = relationship(foreign_keys=[persona_user_id])
    services: Mapped[list["Service"]] = relationship(back_populates="agent", cascade="all, delete-orphan")


class Service(Base):
    """虚拟角色提供的服务包 · 一个 LOGO 设计 / 一份 PPT / 一次咨询"""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    price_cents: Mapped[int] = mapped_column(Integer)  # 分 · 99 元 = 9900
    sla_hours: Mapped[int] = mapped_column(Integer, default=72)
    mode: Mapped[str] = mapped_column(String(16), default="hybrid")  # ai / human / hybrid
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    agent: Mapped[Agent] = relationship(back_populates="services")


class Order(Base):
    """工单 · buyer 付费给虚拟角色让他干活 · 真交付走真 owner / AI 自动 / 混合"""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    price_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending / paid / accepted / in_progress / delivered / completed / cancelled / refunded
    requirements: Mapped[str] = mapped_column(Text, default="")
    deliverables: Mapped[str] = mapped_column(Text, default="")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    buyer: Mapped[User] = relationship()
    agent: Mapped[Agent] = relationship()
    service: Mapped[Service] = relationship()
