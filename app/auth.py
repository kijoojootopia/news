import re
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db
from .utils import now

bp = Blueprint("auth", __name__)
_attempts = defaultdict(deque)
_lock = Lock()


def limit_attempts():
    key = request.remote_addr or "local"
    with _lock:
        cutoff = time.monotonic() - 300
        queue = _attempts[key]
        while queue and queue[0] < cutoff:
            queue.popleft()
        if len(queue) >= 20:
            abort(429, description="잠시 후 다시 로그인해주세요.")
        queue.append(time.monotonic())


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        limit_attempts()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        display = request.form.get("display_name", "").strip()
        if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
            flash("아이디는 영문 소문자·숫자·밑줄 3~30자로 입력해주세요.", "error")
        elif not 8 <= len(password) <= 128 or not 1 <= len(display) <= 20:
            flash("비밀번호는 8~128자, 이름은 1~20자로 입력해주세요.", "error")
        elif (
            get_db()
            .execute("SELECT id FROM users WHERE username=?", (username,))
            .fetchone()
        ):
            flash("이미 사용 중인 아이디입니다.", "error")
        else:
            import sqlite3

            try:
                cursor = get_db().execute(
                    "INSERT INTO users(username,password_hash,display_name,newspaper_name,created_at) VALUES(?,?,?,?,?)",
                    (
                        username,
                        generate_password_hash(password),
                        display,
                        display + "의 하루신문",
                        now(),
                    ),
                )
                get_db().commit()
            except sqlite3.IntegrityError:
                get_db().rollback()
                flash("이미 사용 중인 아이디입니다.", "error")
            else:
                session.clear()
                session["uid"] = cursor.lastrowid
                session["csrf"] = secrets.token_urlsafe(32)
                return redirect(url_for("web.desk"))
    return render_template("auth.html", signup=True)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        limit_attempts()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = (
            get_db()
            .execute("SELECT * FROM users WHERE username=?", (username,))
            .fetchone()
        )
        if (
            user
            and len(password) <= 128
            and check_password_hash(user["password_hash"], password)
        ):
            session.clear()
            session["uid"] = user["id"]
            session["csrf"] = secrets.token_urlsafe(32)
            return redirect(url_for("web.desk"))
        flash("아이디 또는 비밀번호를 확인해주세요.", "error")
    return render_template("auth.html", signup=False)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.home"))
