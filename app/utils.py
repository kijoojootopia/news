import json
from functools import wraps
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from flask import g, redirect, url_for, request, abort


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today():
    return (
        datetime.now(ZoneInfo(g.user["timezone"] if g.get("user") else "Asia/Seoul"))
        .date()
        .isoformat()
    )


def valid_date(value):
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (ValueError, TypeError):
        abort(422, description="날짜를 YYYY-MM-DD 형식으로 입력해주세요.")
    return value


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return {"error": {"message": "로그인 후 이용해주세요."}}, 401
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def read_entry(row):
    value = dict(row)
    value["fields"] = json.loads(value["fields"])
    value["photos"] = json.loads(value["photos"])
    return value
