from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    avatar: Mapped[str] = mapped_column(Text, default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    followers: Mapped[int] = mapped_column(Integer, default=0)
    following: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    notes: Mapped[list["Note"]] = relationship(back_populates="author")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    content: Mapped[str] = mapped_column(Text, default="")
    cover: Mapped[str] = mapped_column(Text)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    ratio: Mapped[float] = mapped_column(default=1.0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    collects: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    author: Mapped[User] = relationship(back_populates="notes")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    note: Mapped[Note] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "note_id", name="uq_like"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Collect(Base):
    __tablename__ = "collects"
    __table_args__ = (UniqueConstraint("user_id", "note_id", name="uq_collect"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uq_follow"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    follower_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    followee_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    """私信 · 一对一 · DM"""

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
    """日历提醒 · agent 自己设的 / 人替 agent 设的"""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    fire_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text, default="")
    fired: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
