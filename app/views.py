import hashlib
import json
import re
import secrets
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import (
    Blueprint,
    render_template,
    request,
    g,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    send_file,
)
from .db import get_db
from .utils import login_required, today, valid_date, now, dump, read_entry
from .catalog import TOPICS, AUTOMATIC, CITIES
from .media import save_uploads
from .jobs import submit

bp = Blueprint("web", __name__)


def entries_for(day):
    return [
        read_entry(r)
        for r in get_db().execute(
            "SELECT * FROM entries WHERE user_id=? AND date=? AND deleted=0 ORDER BY created_at,id",
            (g.user["id"], day),
        )
    ]


def entry_for(eid, deleted=False):
    row = (
        get_db()
        .execute("SELECT * FROM entries WHERE id=? AND user_id=?", (eid, g.user["id"]))
        .fetchone()
    )
    if not row or (row["deleted"] and not deleted):
        abort(404)
    return read_entry(row)


def revision_for(rid):
    row = (
        get_db()
        .execute(
            "SELECT * FROM revisions WHERE id=? AND user_id=?", (rid, g.user["id"])
        )
        .fetchone()
    )
    if not row:
        abort(404)
    r = dict(row)
    r["content"] = json.loads(r["content"])
    return r


def automatic_for(day):
    r = (
        get_db()
        .execute(
            "SELECT automatic FROM day_settings WHERE user_id=? AND date=?",
            (g.user["id"], day),
        )
        .fetchone()
    )
    return json.loads(r[0]) if r else []


@bp.get("/")
def home():
    return render_template("home.html")


@bp.get("/today")
@login_required
def desk():
    day = valid_date(request.args.get("date", today()))
    records = entries_for(day)
    editions = (
        get_db()
        .execute(
            "SELECT id,revision FROM revisions WHERE user_id=? AND date=? ORDER BY revision DESC",
            (g.user["id"], day),
        )
        .fetchall()
    )
    pending = (
        get_db()
        .execute(
            "SELECT id FROM publications WHERE user_id=? AND date=? AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1",
            (g.user["id"], day),
        )
        .fetchone()
    )
    return render_template(
        "desk.html",
        day=day,
        entries=records,
        automatic=AUTOMATIC,
        selected=automatic_for(day),
        editions=editions,
        request_key=uuid.uuid4().hex,
        pending_id=pending["id"] if pending else "",
    )


@bp.post("/day-options")
@login_required
def options():
    day = valid_date(request.form.get("date"))
    selected = [key for key in request.form.getlist("automatic") if key in AUTOMATIC]
    get_db().execute(
        "INSERT INTO day_settings(user_id,date,automatic) VALUES(?,?,?) ON CONFLICT(user_id,date) DO UPDATE SET automatic=excluded.automatic",
        (g.user["id"], day, dump(selected)),
    )
    get_db().commit()
    flash("자동 코너 선택을 저장했어요.", "success")
    return redirect(url_for("web.desk", date=day))


@bp.route("/entries/new/<topic>", methods=["GET", "POST"])
@login_required
def new_entry(topic):
    if topic not in TOPICS:
        abort(404)
    day = valid_date(request.args.get("date", request.form.get("date", today())))
    return entry_form(topic, day, None)


@bp.route("/entries/<eid>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(eid):
    entry = entry_for(eid)
    return entry_form(entry["topic"], entry["date"], entry)


def entry_form(topic, day, entry):
    schema = TOPICS[topic]
    if request.method == "POST":
        data = {}
        for key, label, kind, required in schema["fields"]:
            value = request.form.get(key, "").strip()
            limit = 2000 if kind == "textarea" else 120
            if (required and not value) or len(value) > limit:
                flash(
                    f"{label}: "
                    + (
                        "필수 입력입니다."
                        if not value
                        else f"{limit}자 이하로 입력해주세요."
                    ),
                    "error",
                )
                return render_template(
                    "entry.html",
                    topic_id=topic,
                    topic=schema,
                    day=day,
                    entry=entry,
                    values=request.form,
                ), 422
            if kind == "url" and value and not re.match(r"^https?://", value):
                flash("링크는 http:// 또는 https://로 시작해야 합니다.", "error")
                return render_template(
                    "entry.html",
                    topic_id=topic,
                    topic=schema,
                    day=day,
                    entry=entry,
                    values=request.form,
                ), 422
            data[key] = value
        version = request.form.get("version", "1")
        if entry and str(entry["version"]) != version:
            abort(
                409,
                description="다른 화면에서 수정되었습니다. 내용을 복사한 뒤 다시 열어주세요.",
            )
        files = [
            f
            for f in request.files.getlist("photos") + request.files.getlist("camera")
            if f.filename
        ]
        kept = [
            p
            for p in (entry["photos"] if entry else [])
            if p not in request.form.getlist("remove_photo")
        ]
        if len(files) + len(kept) > 3:
            abort(422, description="기록 하나에 사진 3장까지 담을 수 있어요.")
        photos = kept + save_uploads(files, g.user["id"])
        db = get_db()
        if entry:
            cur = db.execute(
                "UPDATE entries SET title=?,fields=?,photos=?,version=version+1,updated_at=? WHERE id=? AND user_id=? AND version=? AND deleted=0",
                (
                    data["title"],
                    dump(data),
                    dump(photos),
                    now(),
                    entry["id"],
                    g.user["id"],
                    entry["version"],
                ),
            )
            if not cur.rowcount:
                db.rollback()
                abort(409, description="기록이 변경되었습니다. 다시 열어주세요.")
        else:
            db.execute(
                "INSERT INTO entries(id,user_id,date,topic,title,fields,photos,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    uuid.uuid4().hex,
                    g.user["id"],
                    day,
                    topic,
                    data["title"],
                    dump(data),
                    dump(photos),
                    now(),
                    now(),
                ),
            )
        db.commit()
        flash("오늘의 조각을 저장했어요.", "success")
        return redirect(url_for("web.desk", date=day))
    return render_template(
        "entry.html",
        topic_id=topic,
        topic=schema,
        day=day,
        entry=entry,
        values=entry["fields"] if entry else {},
    )


@bp.post("/entries/<eid>/delete")
@login_required
def delete_entry(eid):
    e = entry_for(eid)
    if request.form.get("version") != str(e["version"]):
        abort(409, description="기록이 변경되었습니다. 새로고침해주세요.")
    cur = get_db().execute(
        "UPDATE entries SET deleted=1,version=version+1,updated_at=? WHERE id=? AND user_id=? AND version=? AND deleted=0",
        (now(), eid, g.user["id"], e["version"]),
    )
    if not cur.rowcount:
        get_db().rollback()
        abort(409, description="기록이 변경되었습니다. 새로고침해주세요.")
    get_db().commit()
    flash("기록을 휴지통으로 옮겼어요. 기존 발행본은 유지됩니다.", "success")
    return redirect(url_for("web.desk", date=e["date"]))


@bp.get("/trash")
@login_required
def trash():
    rows = (
        get_db()
        .execute(
            "SELECT * FROM entries WHERE user_id=? AND deleted=1 ORDER BY updated_at DESC",
            (g.user["id"],),
        )
        .fetchall()
    )
    return render_template("trash.html", entries=[read_entry(r) for r in rows])


@bp.post("/entries/<eid>/restore")
@login_required
def restore_entry(eid):
    e = entry_for(eid, True)
    get_db().execute(
        "UPDATE entries SET deleted=0,version=version+1 WHERE id=? AND user_id=?",
        (eid, g.user["id"]),
    )
    get_db().commit()
    flash("기록을 복원했어요.", "success")
    return redirect(url_for("web.desk", date=e["date"]))


@bp.get("/media/<mid>")
@login_required
def media(mid):
    row = (
        get_db()
        .execute("SELECT * FROM media WHERE id=? AND user_id=?", (mid, g.user["id"]))
        .fetchone()
    )
    if not row:
        abort(404)
    return send_file(
        Path(current_app.config["UPLOAD_FOLDER"]) / row["filename"],
        mimetype="image/jpeg",
    )


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("display_name", "").strip()
        paper = request.form.get("newspaper_name", "").strip()
        tz = request.form.get("timezone", "Asia/Seoul")
        city = request.form.get("city", "서울")
        team = request.form.get("team", "").strip()
        if (
            not 1 <= len(name) <= 20
            or not 1 <= len(paper) <= 30
            or len(team) > 60
            or city not in CITIES
        ):
            abort(422, description="이름·신문 이름·지역을 확인해주세요.")
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            abort(422, description="유효한 시간대를 선택해주세요.")
        get_db().execute(
            "UPDATE users SET display_name=?,newspaper_name=?,timezone=?,city=?,team=? WHERE id=?",
            (name, paper, tz, city, team, g.user["id"]),
        )
        get_db().commit()
        flash("내 신문 설정을 저장했어요. 기존 발행본은 유지됩니다.", "success")
        return redirect(url_for("web.settings"))
    return render_template("settings.html", cities=CITIES)


@bp.post("/api/v1/publications")
@login_required
def publish():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(422, description="잘못된 발행 요청입니다.")
    day = valid_date(data.get("date"))
    key = request.headers.get("Idempotency-Key", "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", key):
        abort(422, description="발행 키가 올바르지 않습니다.")
    existing = (
        get_db()
        .execute(
            "SELECT id,source FROM publications WHERE user_id=? AND request_key=?",
            (g.user["id"], key),
        )
        .fetchone()
    )
    if existing:
        previous = json.loads(existing["source"])
        if (
            previous["date"] != day
            or previous["highlight_id"] != data.get("highlight_id")
            or previous["request_entries"] != data.get("entry_ids")
            or previous["automatic"] != data.get("automatic", [])
        ):
            abort(
                409, description="다른 발행 내용에 같은 요청 키를 사용할 수 없습니다."
            )
        return {"data": {"id": existing["id"]}}, 202
    records = entries_for(day)
    wanted = data.get("entry_ids")
    if (
        not isinstance(wanted, list)
        or not wanted
        or not all(isinstance(x, str) for x in wanted)
        or len(wanted) != len(set(wanted))
    ):
        abort(422, description="신문에 넣을 기록을 선택해주세요.")
    selected = [e for e in records if e["id"] in wanted]
    if len(selected) != len(wanted):
        abort(422, description="선택한 기록을 찾을 수 없습니다.")
    highlight = data.get("highlight_id")
    if highlight not in wanted:
        abort(422, description="포함된 기록 중 1면 하이라이트를 선택해주세요.")
    auto = data.get("automatic", [])
    if (
        not isinstance(auto, list)
        or not all(isinstance(x, str) and x in AUTOMATIC for x in auto)
        or len(set(auto)) != len(auto)
    ):
        abort(422, description="자동 코너를 확인해주세요.")
    if (
        current_app.config["AI_MODE"] == "openai"
        and not current_app.config["OPENAI_API_KEY"]
    ):
        return {
            "error": {
                "message": "OpenAI API 키가 없습니다. .env를 설정하거나 데모 모드를 사용해주세요."
            }
        }, 503
    source = {
        "date": day,
        "entries": selected,
        "highlight_id": highlight,
        "automatic": auto,
        "request_entries": wanted,
        "display_name": g.user["display_name"],
        "newspaper_name": g.user["newspaper_name"],
        "city": g.user["city"],
        "team": g.user["team"],
        "timezone": g.user["timezone"],
    }
    jid = uuid.uuid4().hex
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    # 동시에 들어온 같은 요청도 하나의 작업을 돌려줍니다.
    duplicate = db.execute(
        "SELECT id,source FROM publications WHERE user_id=? AND request_key=?",
        (g.user["id"], key),
    ).fetchone()
    if duplicate:
        previous = json.loads(duplicate["source"])
        db.rollback()
        if (
            previous["date"] != day
            or previous["highlight_id"] != highlight
            or previous["request_entries"] != wanted
            or previous["automatic"] != auto
        ):
            abort(
                409, description="다른 발행 내용에 같은 요청 키를 사용할 수 없습니다."
            )
        return {"data": {"id": duplicate["id"]}}, 202
    active = db.execute(
        "SELECT id FROM publications WHERE user_id=? AND status IN ('queued','running')",
        (g.user["id"],),
    ).fetchone()
    if active:
        db.rollback()
        abort(
            409,
            description="이미 발행 중인 작업이 있습니다. 잠시 후 대기실에서 확인해주세요.",
        )
    db.execute(
        "INSERT INTO publications(id,user_id,date,request_key,status,source,created_at) VALUES(?,?,?,?,?,?,?)",
        (jid, g.user["id"], day, key, "queued", dump(source), now()),
    )
    db.execute(
        "INSERT INTO day_settings VALUES(?,?,?) ON CONFLICT(user_id,date) DO UPDATE SET automatic=excluded.automatic",
        (g.user["id"], day, dump(auto)),
    )
    db.commit()
    submit(current_app._get_current_object(), jid)
    return {"data": {"id": jid}}, 202


@bp.get("/api/v1/publications/<jid>")
@login_required
def job_status(jid):
    row = (
        get_db()
        .execute(
            "SELECT * FROM publications WHERE id=? AND user_id=?", (jid, g.user["id"])
        )
        .fetchone()
    )
    if not row:
        abort(404)
    value = {
        "id": jid,
        "status": row["status"],
        "progress": row["progress"],
        "error": row["error"],
    }
    if row["content"]:
        rid = json.loads(row["content"])["revision_id"]
        value["url"] = url_for("web.edition", rid=rid, reveal=1)
    return {"data": value}


@bp.get("/archive")
@login_required
def archive():
    month = request.args.get("month", "")
    query = request.args.get("q", "").strip()[:100]
    params = [g.user["id"]]
    where = "user_id=?"
    if month:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            abort(422, description="월을 확인해주세요.")
        where += " AND date LIKE ?"
        params.append(month + "%")
    rows = (
        get_db()
        .execute(
            f"SELECT * FROM revisions WHERE {where} ORDER BY date DESC,revision DESC",
            params,
        )
        .fetchall()
    )
    groups = {}
    for row in rows:
        item = dict(row)
        item["content"] = json.loads(item["content"])
        if query and query.casefold() not in dump(item["content"]).casefold():
            continue
        groups.setdefault(row["date"], []).append(item)
    return render_template("archive.html", groups=groups, month=month, query=query)


@bp.get("/editions/<rid>")
@login_required
def edition(rid):
    revision = revision_for(rid)
    shares = (
        get_db()
        .execute(
            "SELECT * FROM shares WHERE revision_id=? AND user_id=? AND revoked=0",
            (rid, g.user["id"]),
        )
        .fetchall()
    )
    return render_template(
        "edition.html",
        revision=revision,
        content=revision["content"],
        public=False,
        shares=shares,
        reveal=request.args.get("reveal") == "1",
    )


@bp.route("/editions/<rid>/edit", methods=["GET", "POST"])
@login_required
def edit_edition(rid):
    revision = revision_for(rid)
    content = revision["content"]
    if request.method == "POST":
        headline = request.form.get("headline", "").strip()
        gossip = request.form.get("gossip", "").strip()
        if not headline or len(headline) > 120 or len(gossip) > 600:
            abort(422, description="제목 또는 짧은 기사의 길이를 확인해주세요.")
        for i, article in enumerate(content["articles"]):
            title = request.form.get(f"title_{i}", "").strip()
            body = request.form.get(f"body_{i}", "").strip()
            if not title or len(title) > 120 or not body or len(body) > 10000:
                abort(422, description="기사 제목과 본문을 확인해주세요.")
            article.update(title=title, body=body)
        content.update(headline=headline, gossip=gossip, edited=True)
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        latest = db.execute(
            "SELECT MAX(revision) FROM revisions WHERE user_id=? AND date=?",
            (g.user["id"], revision["date"]),
        ).fetchone()[0]
        if latest != revision["revision"]:
            db.rollback()
            abort(
                409,
                description="더 최신 발행본이 있습니다. 최신 버전을 열어 수정해주세요.",
            )
        newid = uuid.uuid4().hex
        db.execute(
            "INSERT INTO revisions VALUES(?,?,?,?,?,?)",
            (newid, g.user["id"], revision["date"], latest + 1, dump(content), now()),
        )
        db.commit()
        return redirect(url_for("web.edition", rid=newid, reveal=1))
    return render_template("edit_edition.html", revision=revision, content=content)


@bp.get("/editions/<rid>/export/<kind>")
@login_required
def export(rid, kind):
    if kind not in ("png", "pdf"):
        abort(404)
    revision = revision_for(rid)
    from .exporting import export_png, export_pdf

    stream = export_png(revision) if kind == "png" else export_pdf(revision)
    return send_file(
        stream,
        mimetype="image/png" if kind == "png" else "application/pdf",
        as_attachment=True,
        download_name=f"daynews-{revision['date']}-v{revision['revision']}.{kind}",
    )


@bp.post("/editions/<rid>/share")
@login_required
def create_share(rid):
    revision_for(rid)
    token = secrets.token_urlsafe(32)
    sid = uuid.uuid4().hex
    get_db().execute(
        "INSERT INTO shares(id,user_id,revision_id,token_hash,created_at) VALUES(?,?,?,?,?)",
        (sid, g.user["id"], rid, hashlib.sha256(token.encode()).hexdigest(), now()),
    )
    get_db().commit()
    return render_template(
        "share_created.html",
        rid=rid,
        share_url=url_for("web.shared", token=token, _external=True),
    )


@bp.post("/shares/<sid>/revoke")
@login_required
def revoke_share(sid):
    s = (
        get_db()
        .execute("SELECT * FROM shares WHERE id=? AND user_id=?", (sid, g.user["id"]))
        .fetchone()
    )
    if not s:
        abort(404)
    get_db().execute("UPDATE shares SET revoked=1 WHERE id=?", (sid,))
    get_db().commit()
    flash("공유 링크를 해제했어요.", "success")
    return redirect(url_for("web.edition", rid=s["revision_id"]))


def shared_revision(token):
    if len(token) > 100:
        abort(404)
    row = (
        get_db()
        .execute(
            "SELECT r.* FROM shares s JOIN revisions r ON s.revision_id=r.id WHERE s.token_hash=? AND s.revoked=0",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
        .fetchone()
    )
    if not row:
        abort(404)
    r = dict(row)
    r["content"] = json.loads(r["content"])
    return r


@bp.get("/s/<token>")
def shared(token):
    r = shared_revision(token)
    return render_template(
        "edition.html",
        revision=r,
        content=r["content"],
        public=True,
        share_token=token,
        reveal=False,
    )


@bp.get("/s/<token>/media/<mid>")
def shared_media(token, mid):
    r = shared_revision(token)
    if not any(mid in a["photos"] for a in r["content"]["articles"]):
        abort(404)
    row = (
        get_db()
        .execute("SELECT * FROM media WHERE id=? AND user_id=?", (mid, r["user_id"]))
        .fetchone()
    )
    if not row:
        abort(404)
    return send_file(
        Path(current_app.config["UPLOAD_FOLDER"]) / row["filename"],
        mimetype="image/jpeg",
    )
