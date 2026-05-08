from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import agents, chat_messages, hermes, messages, orders, posts, reminders, social, tools, users
from .seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP: 启动时建表 + seed 示范虚拟角色 · prod 走 alembic upgrade head
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_all(db)
    yield


app = FastAPI(
    title="cast-api",
    version="0.1.0",
    description="Cast C2A2C 虚拟角色平台后端 · 用户创建虚拟角色 → 虚拟角色接服务订单 → AI/真人/混合交付",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(messages.router)
app.include_router(reminders.router)
app.include_router(agents.router)
app.include_router(orders.router)
app.include_router(posts.router)
app.include_router(social.router)
app.include_router(tools.router)
app.include_router(chat_messages.router)
app.include_router(hermes.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "env": settings.env, "version": "0.1.0"}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "cast-api", "docs": "/docs", "health": "/health"}
