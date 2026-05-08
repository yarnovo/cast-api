"""alembic upgrade/downgrade 双向跑过 chat_messages migration (REQ-001)

跑全部 migration 链 · 验证:
- chat_messages 表 + 4 索引 真存在
- downgrade 一步删表干净
- 再 upgrade 恢复
"""

import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect

REPO = Path(__file__).resolve().parent.parent


def _run(args, db_url: str):
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=REPO,
        env={"DATABASE_URL": db_url, "PATH": __import__("os").environ["PATH"], "HOME": __import__("os").environ["HOME"]},
        capture_output=True,
        text=True,
        check=True,
    )


def test_alembic_upgrade_creates_chat_messages(tmp_path):
    db_path = tmp_path / "alembic.db"
    db_url = f"sqlite:///{db_path}"

    _run(["upgrade", "head"], db_url)

    eng = create_engine(db_url)
    insp = inspect(eng)
    assert "chat_messages" in insp.get_table_names()

    cols = {c["name"] for c in insp.get_columns("chat_messages")}
    expected = {
        "id", "session_id", "agent_id", "user_id", "role", "content",
        "content_json", "tool_call_id", "tool_name", "created_at", "metadata_json",
    }
    assert expected.issubset(cols), f"missing cols: {expected - cols}"

    idx_names = {i["name"] for i in insp.get_indexes("chat_messages")}
    assert "ix_chat_messages_session_created" in idx_names
    assert "ix_chat_messages_agent_created" in idx_names
    eng.dispose()


def test_alembic_downgrade_drops_chat_messages(tmp_path):
    db_path = tmp_path / "alembic_down.db"
    db_url = f"sqlite:///{db_path}"

    _run(["upgrade", "head"], db_url)
    _run(["downgrade", "-1"], db_url)

    eng = create_engine(db_url)
    insp = inspect(eng)
    assert "chat_messages" not in insp.get_table_names()
    # 老表仍在 (没误伤)
    assert "agent_memories" in insp.get_table_names()
    assert "agents" in insp.get_table_names()
    eng.dispose()


def test_alembic_upgrade_after_downgrade_restores(tmp_path):
    db_path = tmp_path / "alembic_cycle.db"
    db_url = f"sqlite:///{db_path}"

    _run(["upgrade", "head"], db_url)
    _run(["downgrade", "-1"], db_url)
    _run(["upgrade", "head"], db_url)

    eng = create_engine(db_url)
    insp = inspect(eng)
    assert "chat_messages" in insp.get_table_names()
    eng.dispose()
