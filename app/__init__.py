import os
import secrets
from pathlib import Path
from flask import Flask, g, session, request, abort, render_template
from dotenv import load_dotenv
from .db import get_db, close_db, init_db
from .catalog import TOPICS


def create_app(test_config=None):
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    instance = Path((test_config or {}).get("INSTANCE_PATH", root / "instance"))
    instance.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, instance_path=str(instance))
    key = os.getenv("SECRET_KEY")
    if not key:
        secret_file = instance / "secret.key"
        if not secret_file.exists():
            try:
                with secret_file.open("x") as f:
                    f.write(secrets.token_hex(32))
                secret_file.chmod(0o600)
            except FileExistsError:
                pass
        key = secret_file.read_text().strip()
    app.config.from_mapping(
        SECRET_KEY=key,
        DATABASE=str(instance / "daynews.sqlite3"),
        UPLOAD_FOLDER=str(instance / "uploads"),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        AI_MODE=os.getenv("AI_MODE", "demo"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        WEATHER_ENABLED=os.getenv("WEATHER_ENABLED", "false").lower() == "true",
        JOBS_INLINE=False,
    )
    if test_config:
        app.config.update(test_config)
    if app.config["AI_MODE"] not in ("demo", "openai"):
        raise ValueError("AI_MODE must be demo or openai. Check your .env file.")
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
        # 이 1차 앱은 단일 프로세스 실행을 전제로 합니다.
        get_db().execute(
            "UPDATE publications SET status='failed',error=? WHERE status IN ('queued','running')",
            ("서버가 재시작되었습니다. 기록을 확인하고 다시 발행해주세요.",),
        )
        get_db().commit()

    @app.before_request
    def security():
        g.user = None
        if session.get("uid"):
            g.user = (
                get_db()
                .execute("SELECT * FROM users WHERE id=?", (session["uid"],))
                .fetchone()
            )
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            value = request.headers.get("X-CSRF-Token") or request.form.get(
                "csrf_token", ""
            )
            if not isinstance(value, str) or not secrets.compare_digest(
                value, session["csrf"]
            ):
                abort(
                    400, description="요청이 만료되었습니다. 페이지를 새로고침해주세요."
                )

    @app.context_processor
    def common():
        from .utils import today

        return dict(
            csrf_token=lambda: session["csrf"],
            topics=TOPICS,
            today=today(),
            ai_mode=app.config["AI_MODE"],
        )

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(422)
    @app.errorhandler(429)
    def known_error(e):
        messages = {
            404: "찾을 수 없는 페이지입니다.",
            413: "사진의 총 용량은 30MB 이하로 선택해주세요.",
        }
        message = messages.get(e.code, e.description)
        if request.path.startswith("/api/"):
            return {"error": {"message": message}}, e.code
        return render_template("error.html", code=e.code, message=message), e.code

    from .auth import bp as auth
    from .views import bp as web

    app.register_blueprint(auth)
    app.register_blueprint(web)
    return app
