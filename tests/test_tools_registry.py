"""agent harness · tools registry + agent_tools 关联"""


AID = "ag_demo_design"  # seed 自带 · 已 grant 4 个 normal tool (post / send_dm / like_post / follow_user)


def test_list_tools_registry(client):
    r = client.get("/api/tools")
    assert r.status_code == 200
    tools = r.json()
    ids = {t["id"] for t in tools}
    assert "cast.post" in ids
    assert "cast.send_dm" in ids
    assert "cast.like_post" in ids
    assert "cast.follow_user" in ids
    assert "cast.create_agent" in ids


def test_list_tools_filter_by_scope(client):
    r = client.get("/api/tools?platform=cast&scope=normal")
    tools = r.json()
    ids = {t["id"] for t in tools}
    assert "cast.create_agent" not in ids  # meta-only 不应在 normal scope
    assert "cast.post" in ids


def test_agent_tools_grant_revoke(client):
    # demo agent 默认 grant 4 个 · 不含 create_agent
    r = client.get(f"/api/agents/{AID}/tools")
    initial_ids = {t["id"] for t in r.json()}
    assert "cast.create_agent" not in initial_ids
    assert len(initial_ids) == 4

    # grant create_agent
    rg = client.post(f"/api/agents/{AID}/tools/cast.create_agent")
    assert rg.status_code == 201

    after_grant = {t["id"] for t in client.get(f"/api/agents/{AID}/tools").json()}
    assert "cast.create_agent" in after_grant
    assert len(after_grant) == 5

    # revoke 回去
    rd = client.delete(f"/api/agents/{AID}/tools/cast.create_agent")
    assert rd.status_code == 204

    after_revoke = {t["id"] for t in client.get(f"/api/agents/{AID}/tools").json()}
    assert "cast.create_agent" not in after_revoke
    assert len(after_revoke) == 4
