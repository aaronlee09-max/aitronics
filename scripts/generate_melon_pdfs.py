#!/usr/bin/env python3
"""Build A4 Melon TOP100 PDFs and write one-line base64 files for GitHub Pages."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

GREEN = (0.0, 0.588, 0.169)
GREEN_DEEP = (0.0, 0.42, 0.12)
INK = (0.09, 0.19, 0.15)
MUTED = (0.36, 0.45, 0.41)
LINE = (0.84, 0.90, 0.86)
ROW_ALT = (0.95, 0.98, 0.96)
PAPER = (1, 1, 1)
HEADER_BG = (0.0, 0.588, 0.169)

KST = timezone(timedelta(hours=9))


def find_font(candidates):
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def register_fonts():
    here = Path(__file__).resolve().parent
    repo = here.parent if here.name == "scripts" else here
    bak = find_font([
        str(repo / "fonts" / "bakgwangil.ttf"),
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ])
    ydj = find_font([
        str(repo / "fonts" / "yoondongju.ttf"),
        "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf",
        bak,
    ])
    if not bak:
        raise SystemExit("no Korean TTF found")
    pdfmetrics.registerFont(TTFont("Bak", bak))
    pdfmetrics.registerFont(TTFont("Ydj", ydj or bak))
    return {"bakgwangil": "Bak", "yoondongju": "Ydj"}


def ellipsize(c, text, font, size, width):
    text = (text or "").replace("\n", " ").strip()
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    ell = "…"
    while text and pdfmetrics.stringWidth(text + ell, font, size) > width:
        text = text[:-1]
    return (text + ell) if text else ell


def draw_pdf(path, font, tracks, chart_time, generated):
    w, h = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Melon TOP100")
    c.setAuthor("aitronics")
    margin_x = 12 * mm
    header_h = 22 * mm
    footer_h = 10 * mm
    row_h = 6.55 * mm
    table_top = h - header_h - 8 * mm
    usable = table_top - footer_h - 6 * mm
    rows_per = max(1, int(usable // row_h) - 1)
    cols = [
        ("순위", 14 * mm, "c"),
        ("곡명", 58 * mm, "l"),
        ("아티스트", 42 * mm, "l"),
        ("앨범", 52 * mm, "l"),
        ("좋아요", 20 * mm, "r"),
    ]

    def header(page, pages):
        c.setFillColorRGB(*HEADER_BG)
        c.rect(0, h - header_h, w, header_h, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(font, 14)
        c.drawString(margin_x, h - 11 * mm, "Melon 실시간 TOP 100 플레이리스트")
        c.setFont(font, 8)
        c.drawString(margin_x, h - 17.5 * mm, f"A4 인쇄용 · 100곡 · 생성 {generated} · 차트 {chart_time}")
        c.setFillColorRGB(*GREEN_DEEP)
        c.rect(0, 0, w, footer_h, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(font, 8)
        c.drawString(margin_x, 4 * mm, "informatics.run.place")
        c.drawRightString(w - margin_x, 4 * mm, f"{page} / {pages}")

    def table_header(y):
        c.setFillColorRGB(0.93, 0.97, 0.94)
        c.rect(margin_x, y - 1.5 * mm, w - 2 * margin_x, row_h, fill=1, stroke=0)
        c.setFillColorRGB(*MUTED)
        c.setFont(font, 8)
        x = margin_x + 2 * mm
        for title, width, align in cols:
            if align == "c":
                c.drawCentredString(x + width / 2, y + 1.2 * mm, title)
            elif align == "r":
                c.drawRightString(x + width - 1 * mm, y + 1.2 * mm, title)
            else:
                c.drawString(x + 1 * mm, y + 1.2 * mm, title)
            x += width

    pages = (len(tracks) + rows_per - 1) // rows_per
    for p in range(pages):
        header(p + 1, pages)
        y = table_top
        table_header(y)
        y -= row_h
        chunk = tracks[p * rows_per : (p + 1) * rows_per]
        for i, t in enumerate(chunk):
            if i % 2 == 1:
                c.setFillColorRGB(*ROW_ALT)
                c.rect(margin_x, y - 1.5 * mm, w - 2 * margin_x, row_h, fill=1, stroke=0)
            likes = t.get("likes")
            like_s = f"{int(likes):,}" if likes not in (None, "") else ""
            vals = [str(t.get("rank", "")), str(t.get("title") or ""), str(t.get("artist") or ""), str(t.get("album") or ""), like_s]
            x = margin_x + 2 * mm
            for (title, width, align), raw in zip(cols, vals):
                size = 9 if title == "순위" else 8
                c.setFont(font, size)
                c.setFillColorRGB(*INK)
                text = ellipsize(c, raw, font, size, width - 2.4 * mm)
                ty = y + 1.0 * mm
                if align == "c":
                    c.drawCentredString(x + width / 2, ty, text)
                elif align == "r":
                    c.drawRightString(x + width - 1 * mm, ty, text)
                else:
                    c.drawString(x + 1 * mm, ty, text)
                x += width
            y -= row_h
        c.showPage()
    c.save()


def write_b64(pdf_path, b64_path):
    raw = pdf_path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise SystemExit(f"{pdf_path} is not a PDF")
    b64_path.parent.mkdir(parents=True, exist_ok=True)
    b64_path.write_text(base64.b64encode(raw).decode("ascii"), encoding="utf-8")


def main():
    here = Path(__file__).resolve().parent
    repo = here.parent if here.name == "scripts" else here
    chart_path = repo / "chart.json"
    data = json.loads(chart_path.read_text(encoding="utf-8"))
    tracks = data.get("tracks") or []
    if len(tracks) < 50:
        raise SystemExit(f"expected 100 tracks, got {len(tracks)}")
    fonts = register_fonts()
    generated = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    chart_time = data.get("chartTime") or ""
    if chart_time and "KST" not in str(chart_time):
        chart_time = f"{chart_time} KST"
    out_dir = repo / "downloads"
    tmp = Path("/tmp/melon_pdfs")
    tmp.mkdir(exist_ok=True)
    mapping = {
        "bakgwangil": ("Melon_Top100_bakgwangil.pdf", fonts["bakgwangil"]),
        "yoondongju": ("Melon_Top100_yoondongju.pdf", fonts["yoondongju"]),
    }
    for key, (name, font) in mapping.items():
        pdf_path = tmp / name
        draw_pdf(pdf_path, font, tracks, str(chart_time), generated)
        dest = out_dir / f"Melon_Top100_{key}.b64"
        write_b64(pdf_path, dest)
        print(f"wrote {dest} bytes={pdf_path.stat().st_size}")


if __name__ == "__main__":
    main()
