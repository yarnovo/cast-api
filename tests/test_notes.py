def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_notes(client):
    r = client.get("/api/notes")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 20
    item = data["items"][0]
    assert {"id", "title", "cover", "ratio", "likes", "author"} <= item.keys()
    assert {"id", "name", "avatar"} <= item["author"].keys()


def test_list_notes_pagination(client):
    r = client.get("/api/notes?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 5
    assert data["next_cursor"] is not None

    r2 = client.get(f"/api/notes?limit=5&cursor={data['next_cursor']}")
    assert r2.status_code == 200
    page2_ids = {n["id"] for n in r2.json()["items"]}
    page1_ids = {n["id"] for n in data["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_get_note_detail(client):
    r = client.get("/api/notes/n001")
    assert r.status_code == 200
    note = r.json()
    assert note["id"] == "n001"
    assert "content" in note
    assert isinstance(note["images"], list) and len(note["images"]) == 3
    assert isinstance(note["tags"], list)


def test_get_note_404(client):
    r = client.get("/api/notes/nope")
    assert r.status_code == 404


def test_list_comments(client):
    r = client.get("/api/notes/n001/comments")
    assert r.status_code == 200
    comments = r.json()
    assert len(comments) == 5


def test_create_comment(client):
    r = client.post("/api/notes/n001/comments", json={"content": "hello world"})
    assert r.status_code == 201
    c = r.json()
    assert c["content"] == "hello world"

    r2 = client.get("/api/notes/n001/comments")
    assert len(r2.json()) == 6


def test_toggle_like(client):
    r1 = client.post("/api/notes/n001/like")
    assert r1.status_code == 200
    assert r1.json()["active"] is True
    cnt_after = r1.json()["count"]

    r2 = client.post("/api/notes/n001/like")
    assert r2.json()["active"] is False
    assert r2.json()["count"] == cnt_after - 1


def test_toggle_collect(client):
    r1 = client.post("/api/notes/n001/collect")
    assert r1.status_code == 200
    assert r1.json()["active"] is True
    r2 = client.post("/api/notes/n001/collect")
    assert r2.json()["active"] is False


def test_get_user(client):
    r = client.get("/api/users/u01")
    assert r.status_code == 200
    u = r.json()
    assert u["id"] == "u01"
    assert u["name"] == "鹿小姐"


def test_list_user_notes(client):
    r = client.get("/api/users/u01/notes")
    assert r.status_code == 200
    notes = r.json()
    assert all(n["author"]["id"] == "u01" for n in notes)


def test_create_note(client):
    payload = {
        "title": "test new note",
        "content": "hi",
        "cover": "data:image/svg+xml;utf8,<svg/>",
        "images": ["a", "b"],
        "tags": ["#test"],
        "ratio": 1.0,
    }
    r = client.post("/api/notes", json=payload)
    assert r.status_code == 201
    n = r.json()
    assert n["title"] == "test new note"
    assert n["author"]["id"] == "u01"
