"""agent harness · chat session 持久化 (REQ-001)

3 endpoint:
- POST   /api/chat_messages         (RdsSession.append)
- GET    /api/chat_messages?...     (RdsSession.load)
- DELETE /api/chat_messages?...     (RdsSession.clear)
"""

import time

AID = "ag_demo_design"  # seed 自带
UID = "u01"             # seed 自带真人 user


def _append(client, session_id: str, role: str, content: str, **extra):
    body = {"session_id": session_id, "agent_id": AID, "role": role, "content": content}
    body.update(extra)
    r = client.post("/api/chat_messages", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_append_user_message(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_test_1",
            "agent_id": AID,
            "user_id": UID,
            "role": "user",
            "content": "你好",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"].startswith("cm_")
    assert "created_at" in body


def test_append_assistant_with_tool_calls(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_tc",
            "agent_id": AID,
            "role": "assistant",
            "content": "调一下 search",
            "content_json": '[{"id":"call_1","name":"search","args":{"q":"x"}}]',
            "metadata_json": '{"model":"gpt-4o","stop_reason":"tool_calls"}',
        },
    )
    assert r.status_code == 201, r.text


def test_append_tool_result(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_tc",
            "agent_id": AID,
            "role": "tool",
            "content": "result body",
            "tool_call_id": "call_1",
            "tool_name": "search",
        },
    )
    assert r.status_code == 201, r.text


def test_append_invalid_role_400(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_x",
            "agent_id": AID,
            "role": "ghost",
            "content": "x",
        },
    )
    assert r.status_code == 400


def test_append_unknown_agent_404(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_x",
            "agent_id": "ag_does_not_exist",
            "role": "user",
            "content": "x",
        },
    )
    assert r.status_code == 404


def test_append_unknown_user_404(client):
    r = client.post(
        "/api/chat_messages",
        json={
            "session_id": "s_x",
            "agent_id": AID,
            "user_id": "u_nope",
            "role": "user",
            "content": "x",
        },
    )
    assert r.status_code == 404


def test_load_session_in_order(client):
    sid = "s_load"
    # 顺序写 5 条 · 中间稍 sleep 让 created_at 可区分
    for i, role in enumerate(["user", "assistant", "user", "assistant", "user"]):
        _append(client, sid, role, f"msg-{i}")
        time.sleep(0.001)

    r = client.get(f"/api/chat_messages?session_id={sid}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 5
    # asc by created_at
    contents = [m["content"] for m in rows]
    assert contents == [f"msg-{i}" for i in range(5)]


def test_load_session_isolation(client):
    _append(client, "s_a", "user", "in-a")
    _append(client, "s_b", "user", "in-b")
    rows = client.get("/api/chat_messages?session_id=s_a").json()
    assert len(rows) == 1
    assert rows[0]["content"] == "in-a"


def test_load_limit(client):
    sid = "s_limit"
    for i in range(10):
        _append(client, sid, "user", f"m{i}")
        time.sleep(0.001)
    r = client.get(f"/api/chat_messages?session_id={sid}&limit=3")
    rows = r.json()
    # 取最新 3 条按 asc 返
    assert len(rows) == 3
    assert [m["content"] for m in rows] == ["m7", "m8", "m9"]


def test_load_limit_max_500(client):
    r = client.get("/api/chat_messages?session_id=s_x&limit=999")
    assert r.status_code == 422  # validation


def test_load_before_cursor(client):
    sid = "s_cursor"
    ids = []
    for i in range(6):
        out = _append(client, sid, "user", f"m{i}")
        ids.append(out["id"])
        time.sleep(0.001)
    # 拉 ids[3] 之前的 (m0/m1/m2)
    r = client.get(f"/api/chat_messages?session_id={sid}&before={ids[3]}")
    rows = r.json()
    assert [m["content"] for m in rows] == ["m0", "m1", "m2"]


def test_load_before_cursor_unknown_404(client):
    r = client.get("/api/chat_messages?session_id=s_x&before=cm_does_not_exist")
    assert r.status_code == 404


def test_load_empty_session(client):
    r = client.get("/api/chat_messages?session_id=s_never_used")
    assert r.status_code == 200
    assert r.json() == []


def test_clear_session(client):
    sid = "s_clear"
    for i in range(3):
        _append(client, sid, "user", f"m{i}")
    r = client.delete(f"/api/chat_messages?session_id={sid}")
    assert r.status_code == 200
    assert r.json()["deleted"] == 3
    # 二次 clear 幂等 · 0
    r2 = client.delete(f"/api/chat_messages?session_id={sid}")
    assert r2.json()["deleted"] == 0
    # load 空
    rows = client.get(f"/api/chat_messages?session_id={sid}").json()
    assert rows == []


def test_clear_does_not_affect_other_session(client):
    _append(client, "s_keep", "user", "stay")
    _append(client, "s_drop", "user", "go")
    client.delete("/api/chat_messages?session_id=s_drop")
    rows = client.get("/api/chat_messages?session_id=s_keep").json()
    assert len(rows) == 1
    assert rows[0]["content"] == "stay"


def test_round_trip_payload_fields(client):
    out = _append(
        client,
        "s_rt",
        "assistant",
        "with tool calls",
        content_json='[{"id":"c1","name":"x"}]',
        metadata_json='{"model":"m1"}',
    )
    rows = client.get("/api/chat_messages?session_id=s_rt").json()
    assert len(rows) == 1
    m = rows[0]
    assert m["id"] == out["id"]
    assert m["role"] == "assistant"
    assert m["content"] == "with tool calls"
    assert m["content_json"] == '[{"id":"c1","name":"x"}]'
    assert m["metadata_json"] == '{"model":"m1"}'
    assert m["user_id"] is None
    assert m["tool_call_id"] is None
    assert m["tool_name"] is None
