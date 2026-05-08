"""agent harness · update_self · append-only change_log + 字段更新同事务 (D-5)"""


AID = "ag_demo_design"  # seed 自带 · soul/playbook 已有内容


def test_update_self_writes_changelog(client):
    # 取当前 soul 当 old_value baseline
    detail = client.get(f"/api/agents/{AID}").json()
    old_soul = detail["soul"]

    new_soul = "我是设计师老王 v2 · 经过自演化。"
    r = client.post(
        f"/api/agents/{AID}/update-self",
        json={"field": "soul", "new_value": new_soul, "reason": "client 反馈调老王人设"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["soul"] == new_soul

    # change_log 应有一条新 entry
    rc = client.get(f"/api/agents/{AID}/changes")
    assert rc.status_code == 200
    logs = rc.json()
    assert len(logs) >= 1
    latest = logs[0]  # 时间倒序
    assert latest["field"] == "soul"
    assert latest["old_value"] == old_soul
    assert latest["new_value"] == new_soul
    assert latest["changed_by"] == "self"
    assert latest["reason"] == "client 反馈调老王人设"


def test_update_self_invalid_field_400(client):
    # name / status 等不在 _UPDATABLE_FIELDS 白名单 · 必须 400
    r = client.post(
        f"/api/agents/{AID}/update-self",
        json={"field": "name", "new_value": "黑客改名"},
    )
    assert r.status_code == 400


def test_update_self_unknown_agent_404(client):
    r = client.post(
        "/api/agents/ag_no_such/update-self",
        json={"field": "soul", "new_value": "x"},
    )
    assert r.status_code == 404
