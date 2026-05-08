"""hermes / akong_skills / akong_tools / agent_link endpoints 集成测试 (老板 5-9 拍)。"""

from __future__ import annotations


SEED_OWNER = "u01"  # seed_demo_users 第一个 · 测试 fixture 已 seed


def _create_user(client, uid: str = SEED_OWNER, name: str = "测试用户") -> str:
    """直插 user · 没有 POST /api/users · 用 SQLA 直接插。"""
    from cast_api import models
    from cast_api.db import get_db

    if uid == SEED_OWNER:
        return uid  # seed 已建

    overrides = client.app.dependency_overrides
    db_factory = overrides[get_db]
    gen = db_factory()
    db = next(gen)
    try:
        if not db.get(models.User, uid):
            db.add(models.User(id=uid, name=name))
            db.commit()
    finally:
        try:
            next(gen, None)
        except StopIteration:
            pass
    return uid


def _create_agent(client, owner_id: str, name: str = "test-agent") -> str:
    r = client.post(
        f"/api/agents?owner_id={owner_id}",
        json={"name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ====================== /api/hermes ======================


def test_create_hermes_minimal(client) -> None:
    uid = _create_user(client, "u_h1", "owner1")
    r = client.post("/api/hermes", json={"name": "test-hermes", "owner_user_id": uid})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"].startswith("hm_")
    assert body["name"] == "test-hermes"
    assert body["owner_user_id"] == uid
    assert body["skills"] == []
    assert body["tools"] == []


def test_create_hermes_explicit_id_for_static_sync(client) -> None:
    """meta-hermes 用 static_ref='meta-hermes' + id='meta-hermes' 自识别"""
    r = client.post("/api/hermes", json={
        "id": "meta-hermes",
        "name": "阿空小造",
        "soul": "我是阿空小造",
        "playbook": "聊 + create_agent",
        "style": "短句",
        "static_ref": "meta-hermes",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == "meta-hermes"
    assert body["static_ref"] == "meta-hermes"


def test_create_hermes_with_skills_and_tools(client) -> None:
    uid = _create_user(client, "u_h2", "owner2")
    aid = _create_agent(client, uid, "agent2")
    r = client.post("/api/hermes", json={
        "name": "agent2-hermes",
        "agent_id": aid,
        "owner_user_id": uid,
        "skills": [
            {"kind": "static", "static_ref": "cast-skills::publish-post"},
        ],
        "tools": [
            {"kind": "static", "static_ref": "cast.send_dm"},
            {"kind": "static", "static_ref": "meta.create_agent", "config": {"max": 5}},
        ],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["skills"]) == 1
    assert body["skills"][0]["source"] == "static"
    assert body["skills"][0]["static_ref"] == "cast-skills::publish-post"
    assert len(body["tools"]) == 2
    assert body["tools"][1]["config"] == {"max": 5}


def test_get_hermes(client) -> None:
    uid = _create_user(client, "u_h3", "owner3")
    r = client.post("/api/hermes", json={"name": "h3", "owner_user_id": uid})
    hid = r.json()["id"]
    r = client.get(f"/api/hermes/{hid}")
    assert r.status_code == 200
    assert r.json()["name"] == "h3"


def test_get_hermes_404(client) -> None:
    r = client.get("/api/hermes/hm_nope")
    assert r.status_code == 404


def test_list_hermes_by_owner(client) -> None:
    uid = _create_user(client, "u_h4", "owner4")
    client.post("/api/hermes", json={"name": "a", "owner_user_id": uid})
    client.post("/api/hermes", json={"name": "b", "owner_user_id": uid})
    client.post("/api/hermes", json={"name": "c", "owner_user_id": "u01"})  # 别人的 (seed user)
    r = client.get(f"/api/hermes?owner_user_id={uid}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    names = {h["name"] for h in items}
    assert names == {"a", "b"}


def test_list_hermes_by_agent_id(client) -> None:
    uid = _create_user(client, "u_h5", "owner5")
    aid = _create_agent(client, uid, "agent5")
    client.post("/api/hermes", json={
        "name": "h5", "agent_id": aid, "owner_user_id": uid,
    })
    r = client.get(f"/api/hermes?agent_id={aid}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["agent_id"] == aid


def test_update_hermes_fields(client) -> None:
    uid = _create_user(client, "u_h6", "owner6")
    r = client.post("/api/hermes", json={"name": "h6", "owner_user_id": uid, "soul": "old"})
    hid = r.json()["id"]
    r = client.put(f"/api/hermes/{hid}", json={"soul": "new", "name": "h6-new"})
    assert r.status_code == 200
    body = r.json()
    assert body["soul"] == "new"
    assert body["name"] == "h6-new"


def test_delete_hermes(client) -> None:
    uid = _create_user(client, "u_h7", "owner7")
    r = client.post("/api/hermes", json={"name": "h7", "owner_user_id": uid})
    hid = r.json()["id"]
    r = client.delete(f"/api/hermes/{hid}")
    assert r.status_code == 204
    r = client.get(f"/api/hermes/{hid}")
    assert r.status_code == 404


# ====================== /api/skills ======================


def test_create_dynamic_skill_with_code(client) -> None:
    uid = _create_user(client, "u_s1", "owner_s1")
    r = client.post("/api/skills", json={
        "name": "custom-skill",
        "sop_markdown": "# Custom\nstep 1: ...",
        "source": "dynamic",
        "code_python": "def run(ctx): return 'ok'",
        "owner_user_id": uid,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"].startswith("sk_")
    assert body["source"] == "dynamic"
    assert body["code_python"] == "def run(ctx): return 'ok'"


def test_get_skill(client) -> None:
    r = client.post("/api/skills", json={"name": "s1"})
    sid = r.json()["id"]
    r = client.get(f"/api/skills/{sid}")
    assert r.status_code == 200
    assert r.json()["name"] == "s1"


def test_list_skills_by_source(client) -> None:
    client.post("/api/skills", json={"name": "static-1", "source": "static"})
    client.post("/api/skills", json={"name": "dyn-1", "source": "dynamic", "code_python": "pass"})
    r = client.get("/api/skills?source=dynamic")
    items = r.json()
    assert all(s["source"] == "dynamic" for s in items)
    assert any(s["name"] == "dyn-1" for s in items)


# ====================== /api/akong-tools ======================


def test_create_dynamic_python_tool(client) -> None:
    r = client.post("/api/akong-tools", json={
        "name": "calc",
        "kind": "dynamic_python",
        "spec_json": '{"type":"object","properties":{"x":{"type":"number"}}}',
        "code_python": "def run(x): return x * 2",
        "source": "dynamic",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "dynamic_python"
    assert body["code_python"] == "def run(x): return x * 2"


def test_create_webhook_tool(client) -> None:
    r = client.post("/api/akong-tools", json={
        "name": "zap_webhook",
        "kind": "webhook",
        "webhook_url": "https://hooks.zapier.com/abc",
        "source": "dynamic",
    })
    assert r.status_code == 201
    assert r.json()["webhook_url"] == "https://hooks.zapier.com/abc"


def test_invalid_tool_kind_rejected(client) -> None:
    r = client.post("/api/akong-tools", json={"name": "bad", "kind": "weird"})
    assert r.status_code == 422


def test_list_akong_tools_by_kind(client) -> None:
    client.post("/api/akong-tools", json={"name": "a", "kind": "builtin"})
    client.post("/api/akong-tools", json={"name": "b", "kind": "webhook", "webhook_url": "x"})
    r = client.get("/api/akong-tools?kind=webhook")
    items = r.json()
    assert all(t["kind"] == "webhook" for t in items)


# ====================== agent ↔ skill / tool 关联 ======================


def test_link_skill_to_agent(client) -> None:
    uid = _create_user(client, "u_link", "owner_link")
    aid = _create_agent(client, uid, "agent_link")
    sk = client.post("/api/skills", json={"name": "linkable"}).json()
    r = client.post(f"/api/agents/{aid}/skills", json={"skill_id": sk["id"], "source": "static"})
    assert r.status_code == 201
    # list skills by agent
    r = client.get(f"/api/skills?agent_id={aid}")
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == sk["id"]


def test_unlink_skill(client) -> None:
    uid = _create_user(client, "u_unlink", "owner_unlink")
    aid = _create_agent(client, uid, "agent_unlink")
    sk = client.post("/api/skills", json={"name": "unlinkable"}).json()
    client.post(f"/api/agents/{aid}/skills", json={"skill_id": sk["id"]})
    r = client.delete(f"/api/agents/{aid}/skills/{sk['id']}")
    assert r.status_code == 204


def test_link_akong_tool_to_agent(client) -> None:
    uid = _create_user(client, "u_tlink", "owner_tlink")
    aid = _create_agent(client, uid, "agent_tlink")
    tl = client.post("/api/akong-tools", json={"name": "linkable_t", "kind": "builtin"}).json()
    r = client.post(f"/api/agents/{aid}/tools-link", json={"tool_id": tl["id"]})
    assert r.status_code == 201
    r = client.get(f"/api/akong-tools?agent_id={aid}")
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == tl["id"]


def test_create_hermes_with_dynamic_skill_ref(client) -> None:
    """dynamic SkillRef 必须指向已存在的 skill row · 否则 404"""
    uid = _create_user(client, "u_dyn", "owner_dyn")
    aid = _create_agent(client, uid, "agent_dyn")
    sk = client.post("/api/skills", json={
        "name": "dyn1", "source": "dynamic", "code_python": "pass",
    }).json()
    r = client.post("/api/hermes", json={
        "name": "with-dyn-skill",
        "agent_id": aid,
        "skills": [{"kind": "dynamic", "skill_id": sk["id"]}],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["skills"][0]["source"] == "dynamic"
    assert body["skills"][0]["id"] == sk["id"]


def test_create_hermes_dynamic_skill_not_found(client) -> None:
    uid = _create_user(client, "u_404", "owner_404")
    aid = _create_agent(client, uid, "agent_404")
    r = client.post("/api/hermes", json={
        "name": "bad",
        "agent_id": aid,
        "skills": [{"kind": "dynamic", "skill_id": "sk_nonexistent"}],
    })
    assert r.status_code == 404
