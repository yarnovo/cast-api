from datetime import datetime, timedelta, UTC


def test_send_and_inbox(client):
    r = client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "hi u02"})
    assert r.status_code == 201
    msg = r.json()
    assert msg["from_user_id"] == "u01"
    assert msg["to_user_id"] == "u02"
    assert msg["read"] is False

    r2 = client.get("/api/messages/inbox?user_id=u02")
    assert r2.status_code == 200
    assert any(m["content"] == "hi u02" for m in r2.json())


def test_self_send_400(client):
    r = client.post("/api/messages?user_id=u01", json={"to_user_id": "u01", "content": "x"})
    assert r.status_code == 400


def test_unknown_receiver_404(client):
    r = client.post("/api/messages?user_id=u01", json={"to_user_id": "no_such", "content": "x"})
    assert r.status_code == 404


def test_conversation_with_marks_read(client):
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "1"})
    client.post("/api/messages?user_id=u02", json={"to_user_id": "u01", "content": "2"})
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "3"})

    # u02 看跟 u01 的对话
    r = client.get("/api/messages/with/u01?user_id=u02")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) >= 3
    # 看完后 u02 收到的消息都标已读
    inbox = client.get("/api/messages/inbox?user_id=u02&only_unread=true").json()
    assert all(m["from_user_id"] != "u01" for m in inbox)


def test_conversations_list(client):
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "hi"})
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u03", "content": "hi"})
    r = client.get("/api/messages/conversations?user_id=u01")
    assert r.status_code == 200
    convs = r.json()
    assert {c["other_user"]["id"] for c in convs} >= {"u02", "u03"}


def test_unread_count(client):
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "x"})
    client.post("/api/messages?user_id=u01", json={"to_user_id": "u02", "content": "y"})
    r = client.get("/api/messages/unread-count?user_id=u02")
    assert r.json()["unread"] >= 2


def test_create_reminder(client):
    fire = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    r = client.post("/api/reminders?user_id=u01", json={"fire_at": fire, "what": "早安笔记", "why": "聊咖啡"})
    assert r.status_code == 201
    assert r.json()["what"] == "早安笔记"

    r2 = client.get("/api/reminders?user_id=u01")
    assert any(rm["what"] == "早安笔记" for rm in r2.json())


def test_due_reminders(client):
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    future = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    client.post("/api/reminders?user_id=u01", json={"fire_at": past, "what": "已过"})
    client.post("/api/reminders?user_id=u01", json={"fire_at": future, "what": "未来"})
    r = client.get("/api/reminders/due")
    due_whats = [rm["what"] for rm in r.json()]
    assert "已过" in due_whats
    assert "未来" not in due_whats


def test_fire_and_delete(client):
    fire = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    r = client.post("/api/reminders?user_id=u01", json={"fire_at": fire, "what": "test"})
    rid = r.json()["id"]

    r2 = client.post(f"/api/reminders/{rid}/fire")
    assert r2.json()["fired"] is True

    r3 = client.delete(f"/api/reminders/{rid}")
    assert r3.status_code == 204
