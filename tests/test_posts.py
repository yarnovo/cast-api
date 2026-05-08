"""帖子: create / get / delete / like 切换"""


def _create_post(client, author="u01", content="hello world", **kwargs):
    body = {"content": content}
    body.update(kwargs)
    r = client.post(f"/api/posts?author_id={author}", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_post_basic(client):
    p = _create_post(client, "u01", "今天天气真好", images=["https://x/1.png"], location="上海")
    assert p["author"]["id"] == "u01"
    assert p["content"] == "今天天气真好"
    assert p["images"] == ["https://x/1.png"]
    assert p["location"] == "上海"
    assert p["likes"] == 0
    assert p["is_liked"] is False  # 自己刚发的还没点


def test_create_empty_400(client):
    r = client.post("/api/posts?author_id=u01", json={"content": "  "})
    assert r.status_code == 400


def test_create_unknown_author_404(client):
    r = client.post("/api/posts?author_id=nope", json={"content": "x"})
    assert r.status_code == 404


def test_get_post(client):
    p = _create_post(client, "u01", "hello")
    r = client.get(f"/api/posts/{p['id']}?viewer_id=u02")
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "hello"
    assert body["is_liked"] is False
    assert body["is_following_author"] is False


def test_get_unknown_post_404(client):
    r = client.get("/api/posts/p_no_such")
    assert r.status_code == 404


def test_delete_post_only_author(client):
    p = _create_post(client, "u01")
    # 别人不能删
    r = client.delete(f"/api/posts/{p['id']}?author_id=u02")
    assert r.status_code == 403
    # 自己删 ok
    r2 = client.delete(f"/api/posts/{p['id']}?author_id=u01")
    assert r2.status_code == 204
    # 再 get 404
    assert client.get(f"/api/posts/{p['id']}").status_code == 404


def test_like_toggle(client):
    p = _create_post(client, "u01", "like me")
    # u02 点赞
    r = client.post(f"/api/posts/{p['id']}/like?user_id=u02")
    assert r.status_code == 200
    body = r.json()
    assert body["likes"] == 1
    assert body["is_liked"] is True
    # 再点 = 取消
    r2 = client.post(f"/api/posts/{p['id']}/like?user_id=u02")
    assert r2.json()["likes"] == 0
    assert r2.json()["is_liked"] is False


def test_like_unknown_post_404(client):
    r = client.post("/api/posts/p_no/like?user_id=u01")
    assert r.status_code == 404


def test_delete_post_clears_likes(client):
    p = _create_post(client, "u01", "x")
    client.post(f"/api/posts/{p['id']}/like?user_id=u02")
    client.post(f"/api/posts/{p['id']}/like?user_id=u03")
    r = client.delete(f"/api/posts/{p['id']}?author_id=u01")
    assert r.status_code == 204
