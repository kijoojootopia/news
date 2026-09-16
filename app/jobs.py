import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from .db import get_db
from .utils import dump, now
from .news import generate, GenerationError

# 로컬 1차 버전. 별도 Redis 설치가 필요 없습니다.
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="daynews")


def submit(app, job_id):
    if app.config["JOBS_INLINE"]:
        run_job(app, job_id)
    else:
        _pool.submit(run_job, app, job_id)


def run_job(app, job_id):
    with app.app_context():
        db = get_db()
        job = db.execute("SELECT * FROM publications WHERE id=?", (job_id,)).fetchone()
        if not job or job["status"] != "queued":
            return
        try:
            db.execute(
                "UPDATE publications SET status='running',progress=5 WHERE id=?",
                (job_id,),
            )
            db.commit()
            source = json.loads(job["source"])

            def progress(n):
                db.execute("UPDATE publications SET progress=? WHERE id=?", (n, job_id))
                db.commit()

            content = generate(source, app.config, progress)
            # 생성 도중 원본이 바뀌면 발행을 중단해 오래된 결과가 최신으로 보이지 않게 합니다.
            db.execute("BEGIN IMMEDIATE")
            for entry in source["entries"]:
                row = db.execute(
                    "SELECT version,deleted FROM entries WHERE id=? AND user_id=?",
                    (entry["id"], job["user_id"]),
                ).fetchone()
                if not row or row["deleted"] or row["version"] != entry["version"]:
                    raise GenerationError(
                        "생성 중 원본이 변경되었습니다. 대기실에서 다시 발행해주세요."
                    )
            number = db.execute(
                "SELECT COALESCE(MAX(revision),0)+1 FROM revisions WHERE user_id=? AND date=?",
                (job["user_id"], job["date"]),
            ).fetchone()[0]
            rid = uuid.uuid4().hex
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?)",
                (rid, job["user_id"], job["date"], number, dump(content), now()),
            )
            db.execute(
                "UPDATE publications SET status='succeeded',progress=100,content=? WHERE id=?",
                (dump({"revision_id": rid}), job_id),
            )
            db.commit()
        except Exception as e:
            db.rollback()
            message = (
                str(e)
                if isinstance(e, GenerationError)
                else "발행 중 오류가 발생했습니다. 원본은 보존되어 있습니다. 다시 시도해주세요."
            )
            if not isinstance(e, GenerationError):
                app.logger.exception("Publication failed: %s", job_id)
            db.execute(
                "UPDATE publications SET status='failed',error=? WHERE id=?",
                (message, job_id),
            )
            db.commit()
