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
