from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    avatar: str
    bio: str = ""
    location: str | None = None


class UserStats(BaseModel):
    posts_count: int
    followers_count: int
    following_count: int


# === 私信 ===

class MessageCreate(BaseModel):
    to_user_id: str
    content: str


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: str
    to_user_id: str
    content: str
    read: bool
    created_at: datetime


class ConversationSummary(BaseModel):
    other_user: UserPublic
    last_message: MessagePublic
    unread: int


# === 提醒 ===

class ReminderCreate(BaseModel):
    fire_at: datetime
    what: str
    why: str = ""


class ReminderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    fire_at: datetime
    what: str
    why: str
    fired: bool
    created_at: datetime


# === C2A2C 虚拟角色 / 服务包 / 工单 ===

class AgentCreate(BaseModel):
    name: str
    tagline: str = ""
    soul: str = ""
    playbook: str = ""
    style: str = ""
    expertise: str = ""
    avatar: str = ""
    role: str = "normal"  # 'meta' | 'normal' (architecture §2.9)
    rules_json: str | None = None
    metadata_json: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    tagline: str | None = None
    soul: str | None = None
    playbook: str | None = None
    style: str | None = None
    expertise: str | None = None
    status: str | None = None
    avatar: str | None = None


class AgentSummary(BaseModel):
    """市场页 / 角色卡片"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tagline: str
    persona: UserPublic   # 显示头像 / 名字
    starting_price_cents: int | None = None
    services_count: int = 0
    status: str


class AgentDetail(AgentSummary):
    soul: str
    playbook: str
    style: str
    expertise: str
    owner_id: str
    services: list["ServicePublic"]
    created_at: datetime
    role: str = "normal"
    rules_json: str | None = None
    metadata_json: str | None = None  # 来自 model.extra (列名 metadata_json)


class ServiceCreate(BaseModel):
    title: str
    description: str
    price_cents: int
    sla_hours: int = 72
    mode: str = "hybrid"  # ai / human / hybrid


class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    title: str
    description: str
    price_cents: int
    sla_hours: int
    mode: str
    enabled: bool


class OrderCreate(BaseModel):
    agent_id: str
    service_id: int
    requirements: str = ""


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    buyer_id: str
    agent_id: str
    service_id: int
    price_cents: int
    status: str
    requirements: str
    deliverables: str
    created_at: datetime
    paid_at: datetime | None
    delivered_at: datetime | None


class OrderDeliver(BaseModel):
    deliverables: str


# === 帖子 / 关注 / 点赞 ===

class PostCreate(BaseModel):
    content: str
    images: list[str] | None = None
    location: str | None = None


class PostPublic(BaseModel):
    """帖子对外结构 · author 嵌套 · viewer 视角的 is_liked / is_following_author 由路由层填"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    author: UserPublic
    content: str
    images: list[str] = []
    location: str | None = None
    likes: int
    created_at: datetime
    is_liked: bool = False
    is_following_author: bool = False


# === agent harness · 长记忆 / 自演化 / tools registry ===


class AgentMemoryCreate(BaseModel):
    kind: str  # event | learning | relationship | preference | ...
    content: str
    embedding: bytes | None = None


class AgentMemoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    kind: str
    content: str
    created_at: datetime


class UpdateSelfBody(BaseModel):
    field: str  # soul | playbook | style | rules_json | metadata_json
    new_value: str | None = None
    reason: str | None = None
    changed_by: str = "self"  # self | meta | owner | system


class ChangeLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    field: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    reason: str | None
    created_at: datetime


class ToolPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    params_schema_json: str
    returns_schema_json: str
    platform: str
    scope: str


# === agent harness · chat session 持久化 (REQ-001) ===


class ChatMessageCreate(BaseModel):
    session_id: str
    agent_id: str
    role: str  # user | assistant | tool | system
    content: str
    user_id: str | None = None
    content_json: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    metadata_json: str | None = None


class ChatMessageCreated(BaseModel):
    id: str
    created_at: datetime


class ChatMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    agent_id: str
    user_id: str | None
    role: str
    content: str
    content_json: str | None
    tool_call_id: str | None
    tool_name: str | None
    metadata_json: str | None
    created_at: datetime


class ChatMessageDeleted(BaseModel):
    deleted: int


# === Hermes (老板 5-9 拍 · akong-hermes 仓抽象) ===


class SkillRefBody(BaseModel):
    """SkillRef HTTP body · 写 hermes 时声明 skill 引用。

    kind=static: static_ref 必填 (e.g. 'cast-skills::publish-post')
    kind=dynamic: skill_id 必填 (e.g. 'sk_xxx')
    """
    kind: str  # 'static' | 'dynamic'
    static_ref: str | None = None
    skill_id: str | None = None
    config: dict = {}


class ToolRefBody(BaseModel):
    """ToolRef HTTP body"""
    kind: str  # 'static' | 'dynamic'
    static_ref: str | None = None
    tool_id: str | None = None
    config: dict = {}


class HermesCreate(BaseModel):
    id: str | None = None  # 不传 → 生成 hm_xxx · 传 'meta-hermes' 等显式 id 给静态同步用
    agent_id: str | None = None
    name: str
    soul: str = ""
    playbook: str = ""
    style: str = ""
    static_ref: str | None = None
    owner_user_id: str | None = None
    extra: dict | None = None
    skills: list[SkillRefBody] = []
    tools: list[ToolRefBody] = []


class HermesUpdate(BaseModel):
    name: str | None = None
    soul: str | None = None
    playbook: str | None = None
    style: str | None = None
    extra: dict | None = None
    skills: list[SkillRefBody] | None = None
    tools: list[ToolRefBody] | None = None


class SkillRefPublic(BaseModel):
    """单个 SkillRef · resolver 友好 (kind / id / static_ref / config)"""
    id: str | None = None      # dynamic skill row id (sk_xxx)
    source: str                # 'static' | 'dynamic'
    static_ref: str | None = None
    config: dict = {}


class ToolRefPublic(BaseModel):
    id: str | None = None
    source: str
    static_ref: str | None = None
    config: dict = {}


class HermesPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str | None
    name: str
    soul: str
    playbook: str
    style: str
    static_ref: str | None
    owner_user_id: str | None
    extra: dict
    skills: list[SkillRefPublic]
    tools: list[ToolRefPublic]
    created_at: datetime
    updated_at: datetime


class AkongSkillCreate(BaseModel):
    id: str | None = None
    name: str
    sop_markdown: str = ""
    source: str = "static"  # 'static' | 'dynamic'
    static_ref: str | None = None
    code_python: str | None = None
    owner_user_id: str | None = None


class AkongSkillPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sop_markdown: str
    source: str
    static_ref: str | None
    code_python: str | None
    owner_user_id: str | None
    created_at: datetime
    updated_at: datetime


class AkongToolCreate(BaseModel):
    id: str | None = None
    name: str
    kind: str = "builtin"  # 'builtin' | 'webhook' | 'http_api' | 'dynamic_python'
    spec_json: str | dict = "{}"
    static_ref: str | None = None
    code_python: str | None = None
    webhook_url: str | None = None
    source: str = "static"
    owner_user_id: str | None = None


class AkongToolPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    spec_json: str
    static_ref: str | None
    code_python: str | None
    webhook_url: str | None
    source: str
    owner_user_id: str | None
    created_at: datetime
    updated_at: datetime


class AgentSkillLink(BaseModel):
    skill_id: str
    source: str = "static"
    config: dict | None = None


class AgentToolLink(BaseModel):
    tool_id: str
    source: str = "static"
    config: dict | None = None
