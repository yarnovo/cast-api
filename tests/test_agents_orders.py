"""C2A2C: agents + services + orders 全链路"""


def _create_agent(client, owner="u01"):
    r = client.post(
        f"/api/agents?owner_id={owner}",
        json={
            "name": "小王",
            "tagline": "LOGO 设计 · 上海 · 5 年经验",
            "soul": "我是设计师老王",
            "playbook": "工作日 9-18 接单",
            "style": "极简 / 莫兰迪",
            "expertise": "LOGO / 海报 / VI",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_service(client, agent_id, owner="u01"):
    r = client.post(
        f"/api/agents/{agent_id}/services?owner_id={owner}",
        json={
            "title": "LOGO 草图 · 1 稿 + 1 改",
            "description": "24h 内出 1 个 LOGO 草图 · 含一次小改",
            "price_cents": 9900,
            "sla_hours": 24,
            "mode": "hybrid",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_agent_and_market_visible(client):
    a = _create_agent(client)
    assert a["name"] == "小王"
    assert a["persona"]["id"].startswith("u_ag_")

    r = client.get("/api/agents")
    market = r.json()
    assert any(x["id"] == a["id"] for x in market)


def test_market_search(client):
    a = _create_agent(client)
    r = client.get("/api/agents?q=LOGO")
    assert any(x["id"] == a["id"] for x in r.json())


def test_my_agents(client):
    a = _create_agent(client, owner="u01")
    r = client.get("/api/agents/mine?owner_id=u01")
    assert any(x["id"] == a["id"] for x in r.json())
    r2 = client.get("/api/agents/mine?owner_id=u02")
    assert not any(x["id"] == a["id"] for x in r2.json())


def test_add_service_and_starting_price(client):
    a = _create_agent(client)
    s = _add_service(client, a["id"])
    assert s["price_cents"] == 9900

    detail = client.get(f"/api/agents/{a['id']}").json()
    assert detail["starting_price_cents"] == 9900
    assert detail["services_count"] == 1


def test_update_agent_only_owner(client):
    a = _create_agent(client, owner="u01")
    r = client.patch(f"/api/agents/{a['id']}?owner_id=u02", json={"name": "x"})
    assert r.status_code == 403

    r2 = client.patch(f"/api/agents/{a['id']}?owner_id=u01", json={"tagline": "改了"})
    assert r2.status_code == 200
    assert r2.json()["tagline"] == "改了"


def test_order_full_flow(client):
    # u01 是设计师 owner · u02 是买家
    a = _create_agent(client, owner="u01")
    s = _add_service(client, a["id"], owner="u01")

    # u02 下单
    r = client.post(
        f"/api/orders?buyer_id=u02",
        json={"agent_id": a["id"], "service_id": s["id"], "requirements": "想要莫兰迪色 + 极简风"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["price_cents"] == 9900

    # 不能给自己下单
    r_self = client.post(
        f"/api/orders?buyer_id=u01",
        json={"agent_id": a["id"], "service_id": s["id"]},
    )
    assert r_self.status_code == 400

    # 付款 (MVP mock)
    r2 = client.post(f"/api/orders/{order['id']}/pay")
    assert r2.json()["status"] == "paid"

    # owner 接单
    r3 = client.post(f"/api/orders/{order['id']}/accept?actor_id=u01")
    assert r3.json()["status"] == "accepted"

    # 别的人不能接
    r3b = client.post(f"/api/orders/{order['id']}/accept?actor_id=u99")
    assert r3b.status_code == 404 or r3b.status_code == 403

    # 交付
    r4 = client.post(
        f"/api/orders/{order['id']}/deliver?actor_id=u01",
        json={"deliverables": "https://example.com/logo.png"},
    )
    assert r4.json()["status"] == "delivered"

    # buyer 验收完成
    r5 = client.post(f"/api/orders/{order['id']}/complete?buyer_id=u02")
    assert r5.json()["status"] == "completed"

    # buyer 看自己的订单
    r6 = client.get("/api/orders/mine?user_id=u02")
    assert any(o["id"] == order["id"] for o in r6.json())

    # owner 看 inbox
    r7 = client.get("/api/orders/inbox?owner_id=u01")
    assert any(o["id"] == order["id"] for o in r7.json())


def test_cancel_pending(client):
    a = _create_agent(client, owner="u01")
    s = _add_service(client, a["id"])
    r = client.post(
        f"/api/orders?buyer_id=u02",
        json={"agent_id": a["id"], "service_id": s["id"]},
    )
    oid = r.json()["id"]
    rc = client.post(f"/api/orders/{oid}/cancel?actor_id=u02")
    assert rc.json()["status"] == "cancelled"


def test_delete_service(client):
    a = _create_agent(client)
    s = _add_service(client, a["id"])
    rd = client.delete(f"/api/agents/{a['id']}/services/{s['id']}?owner_id=u01")
    assert rd.status_code == 204
    detail = client.get(f"/api/agents/{a['id']}").json()
    assert detail["services_count"] == 0


def test_create_agent_with_id_override(client):
    """builtin sync 路径 · 显式指定 agent_id · 第二次 POST 同 id 返 409"""
    body = {
        "name": "阿空小造",
        "tagline": "帮你造 agent",
        "soul": "meta",
        "playbook": "引导真人",
        "style": "短句",
        "expertise": "造 agent",
    }
    r = client.post(
        "/api/agents?owner_id=u01&id_override=ag_builtin_meta-xiaozao",
        json=body,
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["id"] == "ag_builtin_meta-xiaozao"

    # 再 POST 同 id → 409
    r2 = client.post(
        "/api/agents?owner_id=u01&id_override=ag_builtin_meta-xiaozao",
        json=body,
    )
    assert r2.status_code == 409

    # GET 现行 · 拿到刚 sync 的 agent
    r3 = client.get("/api/agents/ag_builtin_meta-xiaozao")
    assert r3.status_code == 200
    assert r3.json()["name"] == "阿空小造"
