"""社交关系: follow 切换 / followers / following / stats"""


def test_follow_toggle(client):
    r = client.post("/api/follow?follower_id=u01&followee_id=u02")
    assert r.status_code == 200
    assert r.json()["is_following"] is True
    # 再调 = 取关
    r2 = client.post("/api/follow?follower_id=u01&followee_id=u02")
    assert r2.json()["is_following"] is False


def test_follow_self_400(client):
    r = client.post("/api/follow?follower_id=u01&followee_id=u01")
    assert r.status_code == 400


def test_follow_unknown_404(client):
    r = client.post("/api/follow?follower_id=u01&followee_id=nope")
    assert r.status_code == 404


def test_followers_and_following(client):
    client.post("/api/follow?follower_id=u01&followee_id=u02")
    client.post("/api/follow?follower_id=u03&followee_id=u02")

    # u02 的粉丝
    r = client.get("/api/users/u02/followers")
    ids = {u["id"] for u in r.json()}
    assert ids >= {"u01", "u03"}

    # u01 关注的人
    r2 = client.get("/api/users/u01/following")
    assert any(u["id"] == "u02" for u in r2.json())


def test_user_stats(client):
    # 发 2 帖
    client.post("/api/posts?author_id=u01", json={"content": "p1"})
    client.post("/api/posts?author_id=u01", json={"content": "p2"})
    # u02 / u03 关注 u01 · u01 关注 u04
    client.post("/api/follow?follower_id=u02&followee_id=u01")
    client.post("/api/follow?follower_id=u03&followee_id=u01")
    client.post("/api/follow?follower_id=u01&followee_id=u04")

    r = client.get("/api/users/u01/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["posts_count"] == 2
    assert s["followers_count"] == 2
    assert s["following_count"] == 1


def test_user_posts_endpoint(client):
    client.post("/api/posts?author_id=u01", json={"content": "first"})
    client.post("/api/posts?author_id=u01", json={"content": "second"})
    r = client.get("/api/users/u01/posts?viewer_id=u02")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) >= 2
    # 时间倒序 · second 在前
    contents = [p["content"] for p in posts if p["content"] in {"first", "second"}]
    assert contents.index("second") < contents.index("first")
