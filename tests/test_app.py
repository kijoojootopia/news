import io
import json
import re
import pytest
from PIL import Image
from app import create_app
from app.db import get_db

DAY = "2026-09-16"


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "INSTANCE_PATH": str(tmp_path),
            "JOBS_INLINE": True,
            "AI_MODE": "demo",
            "WEATHER_ENABLED": False,
        }
    )


@pytest.fixture
def client(app):
    c = app.test_client()
    signup(c)
    return c


def token(c):
    c.get("/")
    with c.session_transaction() as s:
        return s["csrf"]


def signup(c, name="jisu"):
    r = c.post(
        "/signup",
        data={
            "csrf_token": token(c),
            "username": name,
            "password": "test-password",
            "display_name": "지수",
        },
    )
    assert r.status_code == 302


def add(c, app, topic="food", photo=False, **changes):
    data = {
        "csrf_token": token(c),
        "title": "작은 카페",
        "memo": "커피를 마시며 잠깐 쉬었다.",
        "artist": "테스트 아티스트",
        **changes,
    }
    if photo:
        stream = io.BytesIO()
        Image.new("RGB", (360, 480), "#9bb7ce").save(stream, "PNG")
        stream.seek(0)
        data["photos"] = (stream, "sample.png")
    r = c.post("/entries/new/" + topic + "?date=" + DAY, data=data)
    assert r.status_code == 302
    with app.app_context():
        return dict(
            get_db()
            .execute("SELECT * FROM entries ORDER BY rowid DESC LIMIT 1")
            .fetchone()
        )


def publish(c, ids, key="test-publication-1", highlight=None):
    return c.post(
        "/api/v1/publications",
        json={
            "date": DAY,
            "entry_ids": ids,
            "highlight_id": highlight or ids[0],
            "automatic": ["cookie", "weather"],
        },
        headers={"X-CSRF-Token": token(c), "Idempotency-Key": key},
    )


def result(c, response):
    assert response.status_code == 202
    r = c.get("/api/v1/publications/" + response.json["data"]["id"])
    assert r.json["data"]["status"] == "succeeded", r.json
    return r.json["data"]["url"].split("?")[0]


def test_complete_flow_and_exports(app, client):
    add(client, app, photo=True)
    add(client, app, "book", title="한 권의 책")
    with app.app_context():
        ids = [r[0] for r in get_db().execute("SELECT id FROM entries")]
    url = result(client, publish(client, ids))
    for path in [
        "/today?date=" + DAY,
        "/archive",
        "/settings",
        "/trash",
        url,
        url + "/edit",
    ]:
        assert client.get(path).status_code == 200
    png = client.get(url + "/export/png")
    assert png.status_code == 200
    assert Image.open(io.BytesIO(png.data)).size == (1080, 1920)
    pdf = client.get(url + "/export/pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    assert "작은 카페" in client.get(url).get_data(as_text=True)


def test_csrf_and_account_boundaries(app, client):
    e = add(client, app, photo=True)
    url = result(client, publish(client, [e["id"]]))
    mid = json.loads(e["photos"])[0]
    other = app.test_client()
    signup(other, "someone_else")
    for path in [f"/entries/{e['id']}/edit", f"/media/{mid}", url, url + "/export/pdf"]:
        assert other.get(path).status_code == 404
    assert (
        client.post("/entries/" + e["id"] + "/delete", data={"version": 1}).status_code
        == 400
    )
    assert (
        other.post(
            "/entries/" + e["id"] + "/delete",
            data={"csrf_token": token(other), "version": 1},
        ).status_code
        == 404
    )


def test_version_conflict_and_restore(app, client):
    e = add(client, app)
    data = {
        "csrf_token": token(client),
        "title": "수정한 카페",
        "memo": "수정된 기록",
        "version": 1,
    }
    assert client.post("/entries/" + e["id"] + "/edit", data=data).status_code == 302
    assert client.post("/entries/" + e["id"] + "/edit", data=data).status_code == 409
    assert (
        client.post(
            "/entries/" + e["id"] + "/delete",
            data={"csrf_token": token(client), "version": 2},
        ).status_code
        == 302
    )
    assert client.get("/entries/" + e["id"] + "/edit").status_code == 404
    assert (
        client.post(
            "/entries/" + e["id"] + "/restore", data={"csrf_token": token(client)}
        ).status_code
        == 302
    )
    assert client.get("/entries/" + e["id"] + "/edit").status_code == 200


def test_duplicate_publish_and_snapshot(app, client):
    e = add(client, app)
    first = publish(client, [e["id"]])
    url = result(client, first)
    assert publish(client, [e["id"]]).json["data"]["id"] == first.json["data"]["id"]
    assert (
        client.post(
            "/entries/" + e["id"] + "/delete",
            data={"csrf_token": token(client), "version": 1},
        ).status_code
        == 302
    )
    assert client.get(url).status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 1


def test_share_scope_and_revocation(app, client):
    e = add(client, app, photo=True)
    url = result(client, publish(client, [e["id"]]))
    foreign = add(client, app, "daily", photo=True, title="공유하지 않은 기록")
    page = client.post(url + "/share", data={"csrf_token": token(client)}).get_data(
        as_text=True
    )
    shared = re.search(r'value="(http://localhost/s/[^"]+)"', page)[1].replace(
        "http://localhost", ""
    )
    guest = app.test_client()
    assert guest.get(shared).status_code == 200
    assert guest.get(shared + "/media/" + json.loads(e["photos"])[0]).status_code == 200
    assert (
        guest.get(shared + "/media/" + json.loads(foreign["photos"])[0]).status_code
        == 404
    )
    assert "기사 수정" not in guest.get(shared).get_data(as_text=True)
    with app.app_context():
        sid = get_db().execute("SELECT id FROM shares").fetchone()[0]
    client.post("/shares/" + sid + "/revoke", data={"csrf_token": token(client)})
    assert guest.get(shared).status_code == 404


def test_edit_revision_keeps_old(app, client):
    e = add(client, app)
    url = result(client, publish(client, [e["id"]]))
    res = client.post(
        url + "/edit",
        data={
            "csrf_token": token(client),
            "headline": "새 제목",
            "gossip": "새로운 한 줄",
            "title_0": "수정 기사",
            "body_0": "직접 수정한 본문",
        },
    )
    assert res.status_code == 302
    assert "직접 수정한 본문" in client.get(res.location).get_data(as_text=True)
    assert "직접 수정한 본문" not in client.get(url).get_data(as_text=True)
    assert (
        client.post(
            url + "/edit",
            data={
                "csrf_token": token(client),
                "headline": "충돌",
                "gossip": "",
                "title_0": "제목",
                "body_0": "본문",
            },
        ).status_code
        == 409
    )


def test_invalid_upload_and_topic(app, client):
    assert client.get("/entries/new/unknown").status_code == 404
    res = client.post(
        "/entries/new/food?date=" + DAY,
        data={
            "csrf_token": token(client),
            "title": "사진",
            "memo": "메모",
            "photos": (io.BytesIO(b"<script>bad</script>"), "fake.png"),
        },
    )
    assert res.status_code == 422
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0


def test_highlight_must_be_included(app, client):
    e = add(client, app)
    assert publish(client, [e["id"]], highlight="not-owned").status_code == 422
    assert publish(client, ["not-owned"]).status_code == 422


def test_failure_keeps_original(app, client, monkeypatch):
    from app import jobs
    from app.news import GenerationError

    def fail(*a, **kw):
        raise GenerationError("일시적인 공급자 오류")

    monkeypatch.setattr(jobs, "generate", fail)
    e = add(client, app)
    r = publish(client, [e["id"]])
    data = client.get("/api/v1/publications/" + r.json["data"]["id"]).json["data"]
    assert data["status"] == "failed"
    assert client.get("/entries/" + e["id"] + "/edit").status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 0


def test_changed_source_blocks_publication(app, client, monkeypatch):
    from app import jobs

    original = jobs.generate

    def change(source, config, progress):
        content = original(source, config, progress)
        get_db().execute("UPDATE entries SET version=version+1")
        get_db().commit()
        return content

    monkeypatch.setattr(jobs, "generate", change)
    e = add(client, app)
    r = publish(client, [e["id"]])
    assert (
        client.get("/api/v1/publications/" + r.json["data"]["id"]).json["data"][
            "status"
        ]
        == "failed"
    )


def test_persistence_after_logout(app, client):
    e = add(client, app)
    client.post("/logout", data={"csrf_token": token(client)})
    assert client.get("/today").status_code == 302
    r = client.post(
        "/login",
        data={
            "csrf_token": token(client),
            "username": "jisu",
            "password": "test-password",
        },
    )
    assert r.status_code == 302
    assert client.get("/entries/" + e["id"] + "/edit").status_code == 200


def test_long_article_pdf_and_escape(app, client):
    e = add(
        client,
        app,
        memo="긴 문장을 기록합니다. " * 100,
        title="<script>alert(1)</script>",
    )
    url = result(client, publish(client, [e["id"]]))
    assert "<script>alert(1)</script>" not in client.get(url).get_data(as_text=True)
    assert client.get(url + "/export/pdf").data.startswith(b"%PDF")


def test_openai_mode_with_mock_provider(app, client, monkeypatch):
    from app import news

    calls = []

    def reply(request, timeout):
        calls.append(json.loads(request.data))
        article = {
            "title": "카페에서 쉬어간 지수",
            "body": "지수는 카페에서 커피를 마시며 잠깐 쉬었다.",
        }
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(article, ensure_ascii=False)
                            }
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr(news.urllib.request, "urlopen", reply)
    app.config.update(AI_MODE="openai", OPENAI_API_KEY="mock-key-never-sent")
    e = add(client, app)
    url = result(client, publish(client, [e["id"]]))
    assert "카페에서 쉬어간 지수" in client.get(url).get_data(as_text=True)
    assert len(calls) == 2
    assert "단신 기자" in calls[1]["messages"][0]["content"]
    assert "temperature_2m" not in str(calls)  # 날씨 연동은 기본적으로 꺼져 있습니다.
    with app.app_context():
        content = json.loads(
            get_db().execute("SELECT content FROM revisions").fetchone()[0]
        )
        assert content["mode"] == "openai"


def test_provider_failure_does_not_fall_back_to_demo(app, client, monkeypatch):
    from app import news

    def fail(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(news.urllib.request, "urlopen", fail)
    app.config.update(AI_MODE="openai", OPENAI_API_KEY="mock-key-never-sent")
    e = add(client, app)
    response = publish(client, [e["id"]])
    job = client.get("/api/v1/publications/" + response.json["data"]["id"]).json["data"]
    assert job["status"] == "failed" and "API 키" in job["error"]
    assert client.get("/entries/" + e["id"] + "/edit").status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 0
