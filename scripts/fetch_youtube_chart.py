#!/usr/bin/env python3
"""Fetch South Korea YouTube Music weekly Top Songs chart.

The chart page is backed by YouTube's public music-analytics browse endpoint.
This stores only chart metadata; playback still uses YouTube's own pages.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://charts.youtube.com/youtubei/v1/browse"
API_KEY = "AIzaSyCzEW7JUJdSql0-2V4tHUb6laYm4iAE_dM"
CHART_URL = "https://charts.youtube.com/charts/TopSongs/kr/weekly"

BODY = {
    "browseId": "FEmusic_analytics_charts_home",
    "context": {
        "capabilities": {},
        "client": {
            "clientName": "WEB_MUSIC_ANALYTICS",
            "clientVersion": "0.2",
            "experimentIds": [],
            "experimentsToken": "",
            "gl": "KR",
            "hl": "ko",
            "theme": "MUSIC",
        },
        "request": {"internalExperimentFlags": []},
    },
    "query": "chart_params_type=WEEK&perspective=CHART&flags=viral_video_chart&selected_chart=TRACKS&chart_params_id=weekly:0:0:kr",
}

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def request_json():
    url = API_URL + "?" + urllib.parse.urlencode({"alt": "json", "key": API_KEY})
    req = urllib.request.Request(url, data=json.dumps(BODY).encode(), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def find_track_view_groups(obj):
    found = []

    def walk(node):
        if isinstance(node, dict):
            tv = node.get("trackViews")
            if isinstance(tv, list) and tv:
                found.append(tv)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(obj)
    return found


def text_value(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "simpleText", "runs"):
            if key == "runs" and isinstance(value.get(key), list):
                return "".join(str(x.get("text", "")) for x in value[key]).strip()
            if isinstance(value.get(key), str):
                return value[key].strip()
    return ""


def image_url(item):
    thumb = item.get("thumbnail") or {}
    thumbs = thumb.get("thumbnails") or []
    if thumbs:
        return thumbs[-1].get("url", "")
    return ""


def video_id(item):
    # TopSongs uses encryptedVideoId in the charts response. Keep a normal id
    # only when it looks like a YouTube video id.
    candidate = item.get("encryptedVideoId") or item.get("videoId") or item.get("id") or ""
    return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate) else ""


def parse_items(data):
    groups = find_track_view_groups(data)
    if not groups:
        raise RuntimeError("YouTube chart response did not contain trackViews")

    # The requested Top Songs group is normally the first group with at least
    # 50 entries. Fall back to the largest group if YouTube changes ordering.
    groups.sort(key=len, reverse=True)
    rows = groups[0]

    result = []
    for index, item in enumerate(rows, 1):
        title = text_value(item.get("title") or item.get("name"))
        artists = item.get("artists") or []
        artist_names = [text_value(a.get("name")) for a in artists if isinstance(a, dict)]
        artist_names = [x for x in artist_names if x]
        views = item.get("views") or item.get("viewCount") or item.get("playCount")
        if isinstance(views, dict):
            views = text_value(views)
        rank = item.get("rank") or index
        try:
            rank = int(rank)
        except (TypeError, ValueError):
            rank = index

        vid = video_id(item)
        result.append({
            "rank": rank,
            "title": title,
            "artist": ", ".join(artist_names),
            "views": views if views is not None else "",
            "videoId": vid,
            "url": f"https://www.youtube.com/watch?v={vid}" if vid else "",
            "image": image_url(item),
        })

    result = [x for x in result if x["title"]]
    if len(result) < 20:
        raise RuntimeError(f"YouTube chart returned too few tracks: {len(result)}")
    return result


def main():
    data = request_json()
    tracks = parse_items(data)
    payload = {
        "source": "YouTube Music Charts",
        "chart": "Top Songs",
        "country": "KR",
        "sourceUrl": CHART_URL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(tracks),
        "tracks": tracks,
    }
    Path("youtube_chart.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote youtube_chart.json ({len(tracks)} tracks)")


if __name__ == "__main__":
    main()
