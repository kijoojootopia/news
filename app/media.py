import uuid
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import current_app, abort
from .db import get_db
from .utils import now


def save_uploads(files, user_id):
    results = []
    paths = []
    try:
        for file in files:
            raw = file.read(10 * 1024 * 1024 + 1)
            if len(raw) > 10 * 1024 * 1024:
                raise ValueError("각 사진은 10MB 이하로 선택해주세요.")
            import io

            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("JPG, PNG, WEBP 사진만 사용할 수 있습니다.")
                if original.width * original.height > 24_000_000:
                    raise ValueError("사진은 2400만 화소 이하로 선택해주세요.")
                img = ImageOps.exif_transpose(original).convert("RGB")
                img.thumbnail((2200, 2200))
                mid = uuid.uuid4().hex
                filename = mid + ".jpg"
                path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
                img.save(path, "JPEG", quality=90)
                paths.append(path)
            get_db().execute(
                "INSERT INTO media VALUES(?,?,?,?)", (mid, user_id, filename, now())
            )
            results.append(mid)
    except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        for p in paths:
            p.unlink(missing_ok=True)
        get_db().rollback()
        abort(
            422,
            description="사진을 확인해주세요. JPG/PNG/WEBP, 장당 10MB·2400만 화소까지 지원합니다.",
        )
    return results
