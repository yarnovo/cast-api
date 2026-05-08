"""Cast C2A2C 平台数据模型 · 用户 / 虚拟角色 / 服务包 / 工单 / 私信 / 提醒 / 帖子 / 关注 / 点赞"""

from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Index, Integer, String, Text, DateTime, UniqueConstraint
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
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 同城 feed 用 · 城市名
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

    harness 字段 (cast-agents architecture.md §2.1):
    - role: 'meta' (有 create_agent 权限) | 'normal'
    - rules_json: 结构化运营规则 (max_posts_per_day / min_reply_lag_minutes 等)
    - extra (列名 metadata_json): 平台特定 (cast: location 关联 / 服务包关联 · 未来 B 站 fake: 视频分类)
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
    role: Mapped[str] = mapped_column(String(16), default="normal", index=True)  # meta | normal
    rules_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON · 结构化运营规则
    # SQLAlchemy 保留 `metadata` · 列名 metadata_json · python attr 用 extra 避开
    extra: Mapped[str | None] = mapped_column("metadata_json", Text, nullable=True)
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


class Post(Base):
    """帖子 · author 任意 user (真人 / 虚拟角色 persona 都行) · Twitter / IG 风文本+图"""

    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    images_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组 of url
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 城市名
    likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    author: Mapped[User] = relationship()


class PostLike(Base):
    """点赞 · user × post 二值"""

    __tablename__ = "post_likes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Follow(Base):
    """关注 · follower → followee 单向"""

    __tablename__ = "follows"

    follower_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    followee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# === agent harness 新表 (cast-agents architecture.md §2) ===


class AgentMemory(Base):
    """长记忆 log · agent 自己写 (architecture.md §2.3)

    每条一行 · append-only · 时间倒序消费。embedding 预留向量 · MVP 留空。
    """

    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # event | learning | relationship | preference | ...
    content: Mapped[str] = mapped_column(Text)  # markdown · 自由格式
    embedding: Mapped[bytes | None] = mapped_column(nullable=True)  # 预留 · MVP 留空
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Tool(Base):
    """平台工具注册中心 (architecture.md §2.4)

    平台级 tools registry · agent 通过 agent_tools 关联表订阅子集。
    runtime 在 tick 时 · 按 agent 当前的 tools 列表注入到 LLM 的 function-calling 参数。
    """

    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 'cast.post' / 'cast.send_dm' / ...
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    params_schema_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON Schema
    returns_schema_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON Schema
    platform: Mapped[str] = mapped_column(String(32), index=True)  # cast | bilibili-fake | global
    scope: Mapped[str] = mapped_column(String(16), default="normal")  # normal | meta-only | admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentTool(Base):
    """agent ↔ tool 关联表 · 谁能调啥 (architecture.md §2.4)"""

    __tablename__ = "agent_tools"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    """agent harness chat session 持久化 · 跨 FC 实例多轮对话不丢上下文 (REQ-001)

    跟 agent_memories 分两层抽象:
    - chat_messages: 短期 turn · 单 session 内的 user/assistant/tool/system 轮次 · 字面 LLM message
    - agent_memories: 长期沉淀 · agent 自己写的 event/learning/relationship 摘要

    harness RdsSession 的 3 个调用点:
    - append: POST /api/chat_messages
    - load:   GET  /api/chat_messages?session_id=...
    - clear:  DELETE /api/chat_messages?session_id=...
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
        Index("ix_chat_messages_agent_created", "agent_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # cm_xxx
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | tool | system
    content: Mapped[str] = mapped_column(Text)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON · assistant tool_calls 原始结构
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # token usage / stop_reason / model


class Hermes(Base):
    """agent 运行环境资源 (老板 5-9 拍 · akong-hermes 仓抽象)。

    Hermes = soul + playbook + style + skills + tools · agent 跑起来需要的一切。
    1:1 关联 agents 表 (一个 agent 一个 hermes)。

    static_ref:
      - null   = 纯动态 (meta.create_agent 创的)
      - 'meta-hermes' / 等 = 静态 (从 yaml 同步而来 · meta-hermes 仓 lifespan 写)
    """

    __tablename__ = "hermes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # hm_xxx | 'meta-hermes'
    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    soul: Mapped[str] = mapped_column(Text, default="")
    playbook: Mapped[str] = mapped_column(Text, default="")
    style: Mapped[str] = mapped_column(Text, default="")
    static_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AkongSkill(Base):
    """skills 表 (新 · 跟 cast-skills 包同名但表前缀 akong_)。

    source='static': static_ref 必填 (e.g. 'cast-skills::publish-post') · code_python null
    source='dynamic': code_python 必填 (LLM 生成) · static_ref null
    """

    __tablename__ = "akong_skills"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # sk_xxx
    name: Mapped[str] = mapped_column(String(128))
    sop_markdown: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="static", index=True)
    static_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_python: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AkongTool(Base):
    """akong_tools 表 (新 · 跟老 tools 表 platform registry 平行 · 不冲突)。

    kind: 'builtin' | 'webhook' | 'http_api' | 'dynamic_python'
    """

    __tablename__ = "akong_tools"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # tl_xxx
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(32), default="builtin")
    spec_json: Mapped[str] = mapped_column(Text, default="{}")
    static_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_python: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="static", index=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentSkill(Base):
    """agent ↔ akong_skill 关联表 (多对多 + agent 维度 config 覆盖)"""

    __tablename__ = "agent_skills"
    __table_args__ = (
        Index("ix_agent_skills_agent_skill", "agent_id", "skill_id"),
    )

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("akong_skills.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), default="static")
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentAkongTool(Base):
    """agent ↔ akong_tool 关联表 (跟老 agent_tools 平行 · agent_tools.tool_id 是 platform tools.id)"""

    __tablename__ = "agent_akong_tools"
    __table_args__ = (
        Index("ix_agent_akong_tools_agent_tool", "agent_id", "tool_id"),
    )

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("akong_tools.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), default="static")
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentChangeLog(Base):
    """agent 自演化 append-only log (D-5 决策 · architecture.md §4)

    每次 update_self 写一条 · 当前值是最新一条 · 可重建任意时点。
    比单次回写 DB 安全 (能回看 agent 怎么演化的) · 比 git 化工程简单。
    """

    __tablename__ = "agent_change_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    field: Mapped[str] = mapped_column(String(32))  # soul | playbook | style | rules_json | metadata_json
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(16), default="self")  # self | meta | owner | system
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
