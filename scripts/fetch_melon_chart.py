#!/usr/bin/env python3
"""Fetch Melon TOP100 chart and write chart.json for GitHub Pages."""

from __future__ import annotations

import html as html_lib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHART_URL = "https://www.melon.com/chart/index.htm"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def fetch_html() -> str:
    request = urllib.request.Request(
        CHART_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml",
            "Referer": "https://www.melon.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_change(block: str) -> tuple[str, int]:
    if "rank_new" in block:
        return "new", 0
    if "rank_up" in block:
        kind = "up"
    elif "rank_down" in block:
        kind = "down"
    else:
        kind = "same"
    match = re.search(
        r'bullet_icons rank_\w+".*?<span class="none">(\d+)</span>',
        block,
        re.S,
    )
    delta = int(match.group(1)) if match else 0
    return kind, delta


def parse_tracks(html: str) -> list[dict]:
    rows = re.findall(
        r'<tr class="lst(?:50|100)"[^>]*data-song-no="(\d+)"[^>]*>(.*?)</tr>',
        html,
        re.S,
    )
    tracks = []
    for song_id, block in rows:
        rank_m = re.search(r'<span class="rank\s*">\s*(\d+)\s*</span>', block)
        title_m = re.search(r'class="ellipsis rank01".*?<a[^>]*>(.*?)</a>', block, re.S)
        artist_m = re.search(r'class="ellipsis rank02".*?<a[^>]*>(.*?)</a>', block, re.S)
        album_m = re.search(r'class="ellipsis rank03".*?<a[^>]*>(.*?)</a>', block, re.S)
        img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
        change, delta = parse_change(block)
        image = img_m.group(1) if img_m else ""
        image = image.split("/melon/")[0]
        tracks.append(
            {
                "rank": int(rank_m.group(1)) if rank_m else len(tracks) + 1,
                "title": clean(title_m.group(1) if title_m else ""),
                "artist": clean(artist_m.group(1) if artist_m else ""),
                "album": clean(album_m.group(1) if album_m else ""),
                "image": image,
                "songId": song_id,
                "change": change,
                "delta": delta,
                "url": f"https://www.melon.com/song/detail.htm?songId={song_id}",
            }
        )
    return tracks


def parse_chart_time(html: str) -> str:
    match = re.search(r"(20\d{2}\.\d{2}\.\d{2})\s*(\d{1,2}:\d{2})?", html)
    if not match:
        return ""
    return " ".join(part for part in match.groups() if part)


def main() -> None:
    html = fetch_html()
    tracks = parse_tracks(html)
    if len(tracks) < 50:
        raise SystemExit(f"expected at least 50 tracks, got {len(tracks)}")

    payload = {
        "source": "Melon TOP100",
        "sourceUrl": CHART_URL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "chartTime": parse_chart_time(html),
        "count": len(tracks),
        "tracks": tracks,
    }

    out = Path("chart.json")
    previous = None
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = None

    if previous and previous.get("tracks") == tracks and previous.get("chartTime") == payload["chartTime"]:
        payload["updatedAt"] = previous.get("updatedAt", payload["updatedAt"])

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(tracks)} tracks, chartTime={payload['chartTime']})")


if __name__ == "__main__":
    main()
