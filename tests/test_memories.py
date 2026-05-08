"""agent harness · 长记忆 (agent_memories) CRUD"""


AID = "ag_demo_design"  # seed 自带


def test_create_memory(client):
    r = client.post(
        f"/api/agents/{AID}/memories",
        json={"kind": "learning", "content": "今天 owner 说不接传销单"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["agent_id"] == AID
    assert body["kind"] == "learning"
    assert body["content"].startswith("今天")
    assert body["id"].startswith("mem_")


def test_list_memories(client):
    client.post(f"/api/agents/{AID}/memories", json={"kind": "event", "content": "A"})
    client.post(f"/api/agents/{AID}/memories", json={"kind": "event", "content": "B"})
    client.post(f"/api/agents/{AID}/memories", json={"kind": "learning", "content": "C"})
    r = client.get(f"/api/agents/{AID}/memories")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3
    # 时间倒序 · 最新一条 (C) 在前
    contents = [m["content"] for m in rows]
    assert contents[0] == "C"


def test_filter_by_kind(client):
    client.post(f"/api/agents/{AID}/memories", json={"kind": "event", "content": "ev1"})
    client.post(f"/api/agents/{AID}/memories", json={"kind": "learning", "content": "ln1"})
    r = client.get(f"/api/agents/{AID}/memories?kind=learning")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "learning"


def test_delete_memory(client):
    r = client.post(f"/api/agents/{AID}/memories", json={"kind": "event", "content": "tmp"})
    mid = r.json()["id"]
    rd = client.delete(f"/api/agents/{AID}/memories/{mid}")
    assert rd.status_code == 204
    rows = client.get(f"/api/agents/{AID}/memories").json()
    assert all(m["id"] != mid for m in rows)


def test_create_memory_unknown_agent_404(client):
    r = client.post(
        "/api/agents/ag_does_not_exist/memories",
        json={"kind": "event", "content": "x"},
    )
    assert r.status_code == 404
