from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import messages, notes, reminders, users
from .seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_all(db)
    yield


app = FastAPI(
    title="xhs-clone-api",
    version="0.0.1",
    description="小红书复刻后端 · /api/notes · /api/users",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes.router)
app.include_router(users.router)
app.include_router(messages.router)
app.include_router(reminders.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "env": settings.env, "version": "0.0.1"}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "xhs-clone-api", "docs": "/docs", "health": "/health"}
