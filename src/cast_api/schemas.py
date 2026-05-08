from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    avatar: str
    bio: str = ""
    followers: int = 0
    following: int = 0


class NoteSummary(BaseModel):
    """瀑布流卡片用的精简版"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    cover: str
    ratio: float
    likes: int
    author: UserPublic


class NoteDetail(NoteSummary):
    content: str
    images: list[str]
    tags: list[str]
    collects: int
    comments_count: int
    created_at: datetime


class CommentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    likes: int
    created_at: datetime
    author: UserPublic


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    cover: str
    images: list[str] = []
    tags: list[str] = []
    ratio: float = 1.0


class CommentCreate(BaseModel):
    content: str


class FeedResponse(BaseModel):
    items: list[NoteSummary]
    next_cursor: str | None = None


class ToggleResponse(BaseModel):
    active: bool
    count: int


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


# === C2A2C ===

class AgentCreate(BaseModel):
    name: str
    tagline: str = ""
    soul: str = ""
    playbook: str = ""
    style: str = ""
    expertise: str = ""
    avatar: str = ""


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
    """市场页瀑布流 / 角色卡片"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tagline: str
    persona: UserPublic   # 显示头像 / 粉丝
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
