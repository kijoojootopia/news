"""고정된 발행본을 출력합니다. 재다운로드 시 AI를 호출하지 않습니다."""

import io
import html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask import current_app
from .db import get_db
from .catalog import TOPICS

CREAM = "#FAF9EE"
INK = "#292D31"
BLUE = "#526F9C"
LINE = "#CBC8B8"


def font_path(bold=False):
    # Pretendard 원본 glyph의 포맷 변환본. OFL 예약 이름을 사용하지 않습니다.
    return (
        Path(current_app.static_folder)
        / "fonts"
        / ("DaynewsSans-Bold.ttf" if bold else "DaynewsSans-Regular.ttf")
    )


def media_path(mid):
    row = get_db().execute("SELECT filename FROM media WHERE id=?", (mid,)).fetchone()
    return Path(current_app.config["UPLOAD_FOLDER"]) / row["filename"] if row else None


def draw_wrapped(draw, text, font, xy, width, line_height, max_lines=None, fill=INK):
    # 실제 glyph 폭으로 한글 줄바꿈. 표지 요약의 생략만 표시하며 PDF 본문은 생략하지 않습니다.
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for char in paragraph:
            if line and draw.textlength(line + char, font=font) > width:
                lines.append(line)
                line = char
            else:
                line += char
        lines.append(line)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textlength(lines[-1] + "…", font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def art_image(index):
    sheet = Image.open(Path(current_app.static_folder) / "art/stationery.png").convert(
        "RGBA"
    )
    cell = sheet.width // 3
    x = (index % 3) * cell
    y = (index // 3) * cell
    return sheet.crop((x, y, x + cell, y + cell))


def paste_art(canvas, index, box):
    # 원본 에셋 시트에서 해당 타일을 출력 지면에 배치합니다.
    tile = art_image(index)
    tile.thumbnail((box[2], box[3]))
    canvas.paste(
        tile,
        (box[0] + (box[2] - tile.width) // 2, box[1] + (box[3] - tile.height) // 2),
        tile,
    )


def export_png(revision):
    c = revision["content"]
    lead = next(a for a in c["articles"] if a["entry_id"] == c["highlight_id"])
    canvas = Image.new("RGB", (1080, 1920), CREAM)
    draw = ImageDraw.Draw(canvas)

    def f(size, bold=False):
        return ImageFont.truetype(str(font_path(bold)), size)

    draw.rectangle((46, 46, 1034, 1874), outline=LINE, width=2)
    draw.text((80, 85), c["date"] + "   /   PERSONAL EDITION", font=f(22), fill=BLUE)
    paste_art(canvas, 7, (837, 65, 145, 145))
    y = draw_wrapped(
        draw, c["newspaper_name"], f(58, True), (80, 150), 745, 73, max_lines=2
    )
    draw.line((80, y + 10, 1000, y + 10), fill=INK, width=3)
    draw.line((80, y + 18, 1000, y + 18), fill=INK, width=1)
    draw.text((80, y + 42), "오늘의 하이라이트", font=f(24), fill=BLUE)
    y = (
        draw_wrapped(
            draw, c["headline"], f(46, True), (80, y + 95), 920, 62, max_lines=3
        )
        + 25
    )
    image_height = 420
    if lead["photos"] and media_path(lead["photos"][0]):
        with Image.open(media_path(lead["photos"][0])) as im:
            fitted = ImageOps.contain(im.convert("RGB"), (920, image_height))
            canvas.paste(
                fitted,
                (
                    80 + (920 - fitted.width) // 2,
                    y + (image_height - fitted.height) // 2,
                ),
            )
    else:
        paste_art(canvas, TOPICS[lead["topic"]]["art"], (290, y, 500, image_height))
    y += image_height + 25
    draw.text((80, y), lead["reporter"], font=f(22), fill=BLUE)
    y += 44
    # 1면 요약은 본문 일부만, 전체는 PDF와 웹에서 제공합니다.
    available = max(2, min(8, (1560 - y) // 42))
    y = (
        draw_wrapped(
            draw,
            lead["body"].replace("\n\n", " "),
            f(28),
            (80, y),
            920,
            42,
            max_lines=available,
        )
        + 25
    )
    if y < 1575:
        draw.line((80, y, 1000, y), fill=LINE, width=2)
        y += 24
        draw.text((80, y), "오늘의 작은 특종", font=f(26, True), fill=BLUE)
        y += 43
        y = draw_wrapped(draw, c["gossip"], f(24), (80, y), 920, 36, max_lines=2)
    others = [a for a in c["articles"] if a["entry_id"] != c["highlight_id"]][:2]
    teaser_y = max(y + 50, 1310)
    if others and teaser_y + 290 < 1710:
        draw.line((80, teaser_y, 1000, teaser_y), fill=LINE, width=2)
        draw.text(
            (80, teaser_y + 22), "이 신문에 담긴 다른 조각", font=f(23, True), fill=BLUE
        )
        for i, article in enumerate(others):
            x = 80 + i * 475
            paste_art(
                canvas, TOPICS[article["topic"]]["art"], (x, teaser_y + 65, 110, 110)
            )
            draw_wrapped(
                draw,
                article["title"],
                f(24, True),
                (x + 125, teaser_y + 80),
                310,
                35,
                max_lines=3,
            )
        note = next((a["body"] for a in c["automatic"] if a["kind"] == "cookie"), None)
        if note:
            draw_wrapped(
                draw, note, f(23), (80, teaser_y + 225), 920, 34, max_lines=1, fill=BLUE
            )
    draw.line((80, 1745, 1000, 1745), fill=INK, width=2)
    draw.text(
        (80, 1775),
        f"기록 {len(c['articles'])}개  /  발행본 v{revision['revision']}  /  1면 요약",
        font=f(21),
        fill=BLUE,
    )
    draw.text(
        (80, 1820),
        "데모 · 규칙 기반 기사" if c["mode"] == "demo" else "AI 작성 기사",
        font=f(20),
        fill=INK,
    )
    out = io.BytesIO()
    canvas.save(out, "PNG")
    out.seek(0)
    return out


def export_pdf(revision):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        BaseDocTemplate,
        PageTemplate,
        Frame,
        BalancedColumns,
        KeepInFrame,
        Paragraph,
        Spacer,
        Image as RLImage,
        PageBreak,
        NextPageTemplate,
        HRFlowable,
    )

    for name, bold in [("Pretendard", False), ("PretendardBold", True)]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_path(bold))))
    c = revision["content"]
    out = io.BytesIO()
    w, h = A4
    styles = {
        "mast": ParagraphStyle(
            "mast",
            fontName="PretendardBold",
            fontSize=29,
            leading=38,
            alignment=1,
            wordWrap="CJK",
            spaceAfter=14,
        ),
        "headline": ParagraphStyle(
            "headline",
            fontName="PretendardBold",
            fontSize=23,
            leading=31,
            wordWrap="CJK",
            spaceAfter=14,
            keepWithNext=True,
        ),
        "title": ParagraphStyle(
            "title",
            fontName="PretendardBold",
            fontSize=16,
            leading=23,
            wordWrap="CJK",
            spaceAfter=10,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Pretendard",
            fontSize=10.5,
            leading=18,
            wordWrap="CJK",
            spaceAfter=12,
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Pretendard",
            fontSize=8,
            leading=13,
            textColor=colors.HexColor(BLUE),
            spaceAfter=10,
            keepWithNext=True,
        ),
    }

    def p(text, style="body"):
        return Paragraph(html.escape(str(text)).replace("\n", "<br/>"), styles[style])

    def background(canv, doc):
        canv.saveState()
        canv.setFillColor(colors.HexColor(CREAM))
        canv.rect(0, 0, w, h, fill=1, stroke=0)
        canv.setStrokeColor(colors.HexColor(LINE))
        canv.rect(24, 24, w - 48, h - 48, fill=0, stroke=1)
        canv.setFont("Pretendard", 8)
        canv.setFillColor(colors.HexColor(BLUE))
        canv.drawString(
            40,
            39,
            c["date"]
            + f" / v{revision['revision']} / "
            + ("데모 기사" if c["mode"] == "demo" else "AI 기사"),
        )
        canv.drawRightString(w - 40, 39, str(doc.page))
        canv.restoreState()

    full = Frame(
        40,
        63,
        w - 80,
        h - 109,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="full",
    )
    gap = 24
    col = (w - 80 - gap) / 2
    frames = [
        Frame(
            40,
            63,
            w - 80,
            h - 109,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="inside-full",
        ),
    ]
    doc = BaseDocTemplate(
        out, pagesize=A4, title=c["newspaper_name"], author=c["display_name"]
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[full], onPage=background),
            PageTemplate(id="inside", frames=frames, onPage=background),
        ]
    )
    story = [
        p(c["date"] + " / PERSONAL EDITION", "small"),
        p(c["newspaper_name"], "mast"),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(INK)),
        Spacer(1, 15),
    ]
    lead = next(a for a in c["articles"] if a["entry_id"] == c["highlight_id"])

    def article_flowables(a, is_lead=False):
        parts = []
        width = w - 80 if is_lead else col
        parts.append(
            p(
                c["headline"] if is_lead else a["title"],
                "headline" if is_lead else "title",
            )
        )
        parts.append(p(a["reporter"], "small"))
        if not a["photos"]:
            illustration = io.BytesIO()
            art_image(TOPICS[a["topic"]]["art"]).save(illustration, "PNG")
            illustration.seek(0)
            side = 150 if is_lead else 65
            parts.extend(
                [RLImage(illustration, width=side, height=side), Spacer(1, 10)]
            )
        for mid in a["photos"]:
            path = media_path(mid)
            if path and path.exists():
                with Image.open(path) as img:
                    iw, ih = img.size
                factor = min(width / iw, (210 if is_lead else 175) / ih)
                parts.extend(
                    [
                        RLImage(str(path), width=iw * factor, height=ih * factor),
                        Spacer(1, 12),
                    ]
                )
        if not is_lead:
            # 제목·기자명·첫 그림이 서로 다른 칸으로 분리되지 않게 묶습니다.
            opening = min(4, len(parts))
            parts = [KeepInFrame(col, h - 130, parts[:opening], mode="error")] + parts[
                opening:
            ]
        for paragraph in a["body"].split("\n\n"):
            parts.append(p(paragraph))
        parts.append(Spacer(1, 10))
        return parts

    story.extend(article_flowables(lead, True))
    story.extend([p("오늘의 작은 특종", "title"), p(c["gossip"])])
    others = [a for a in c["articles"] if a["entry_id"] != c["highlight_id"]]
    if others or c["automatic"]:
        inside = []
        for a in others:
            inside.extend(article_flowables(a))
        for item in c["automatic"]:
            inside.extend(
                [p(item["title"], "title"), p(item["label"], "small"), p(item["body"])]
            )
            if item.get("source_url"):
                inside.append(p(item["source_url"], "small"))
        story.extend(
            [
                NextPageTemplate("inside"),
                PageBreak(),
                p("오늘을 채운 또 다른 이야기", "title"),
                Spacer(1, 16),
                BalancedColumns(
                    inside,
                    nCols=2,
                    needed=100,
                    innerPadding=12,
                    leftPadding=0,
                    rightPadding=0,
                    topPadding=0,
                    bottomPadding=0,
                    endSlack=0,
                    vLinesStrokeColor=colors.HexColor(LINE),
                    vLinesStrokeWidth=0.5,
                ),
            ]
        )
    doc.build(story)
    out.seek(0)
    return out
