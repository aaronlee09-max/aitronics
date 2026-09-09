#!/usr/bin/env python3
"""Build the Korea YouTube Music Top Songs tab from YouTube's official chart playlist.

No audio is downloaded. yt-dlp is used only to read public playlist metadata.
The playlist order is treated as the chart rank.
"""
from __future__ import annotations

import json
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Reuse the same strict, direct-link resolvers as the Melon pipeline so both
# chart tabs expose the same streaming-service destinations.
from fetch_melon_chart import apple_url, bugs_url, deezer_url, genie_url, vibe_url

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6jXS_Tv_N9B8Z0HTRVJE0m"
CHART_URL = "https://charts.youtube.com/charts/TopSongs/kr/weekly"


def fetch_playlist():
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download",
        "--no-warnings", "--ignore-errors", PLAYLIST_URL
    ]
    raw = subprocess.check_output(cmd, text=True, timeout=120)
    return json.loads(raw)


def clean_artist(value):
    value = (value or "").strip()
    if value.endswith(" - Topic"):
        value = value[:-8].strip()
    return value


def main():
    data = fetch_playlist()
    entries = data.get("entries") or []
    rows = []
    for rank, entry in enumerate(entries, 1):
        if not entry:
            continue
        title = (entry.get("track") or entry.get("title") or "").strip()
        artist = clean_artist(entry.get("artist") or entry.get("uploader"))
        video_id = entry.get("id") or ""
        if not title or len(video_id) != 11:
            continue
        row = {
            "rank": rank,
            "title": title,
            "artist": artist,
            "album": (entry.get("album") or "").strip(),
            "views": "",
            "videoId": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "ytMusicUrl": f"https://music.youtube.com/watch?v={video_id}",
            "image": entry.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "melonUrl": f"https://www.melon.com/search/total/index.htm?q={urllib.parse.quote(title + ' ' + artist)}",
            "genieUrl": "",
            "bugsUrl": "",
            "appleUrl": "",
            "spotifyUrl": "",
            "vibeUrl": "",
            "deezerUrl": "",
        }
        # Resolve direct streaming links from the same title/artist pair.
        # If a service cannot be verified, keep it empty rather than linking
        # to an unrelated track.
        resolvers = {
            "genieUrl": genie_url,
            "bugsUrl": bugs_url,
            "appleUrl": apple_url,
            "vibeUrl": vibe_url,
            "deezerUrl": deezer_url,
        }
        for key, resolver in resolvers.items():
            try:
                row[key] = resolver(title, artist) or ""
            except Exception:
                row[key] = ""
        rows.append(row)

    if len(rows) < 50:
        raise RuntimeError(f"YouTube Korea playlist returned too few tracks: {len(rows)}")

    previous_path = Path("youtube_chart.json")
    previous = {}
    if previous_path.exists():
        try:
            old = json.loads(previous_path.read_text(encoding="utf-8"))
            previous = {x.get("videoId"): x.get("rank") for x in old.get("tracks", [])}
        except Exception:
            previous = {}

    for row in rows:
        old_rank = previous.get(row["videoId"])
        row["previousRank"] = old_rank
        row["delta"] = (old_rank - row["rank"]) if old_rank is not None else None
        row["change"] = (
            "new" if old_rank is None else
            "up" if row["delta"] > 0 else
            "down" if row["delta"] < 0 else
            "same"
        )

    payload = {
        "source": "YouTube Music Charts · Top Songs KR",
        "chart": "Top Songs",
        "country": "KR",
        "sourceUrl": CHART_URL,
        "playlistUrl": PLAYLIST_URL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "tracks": rows[:100],
    }
    previous_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote youtube_chart.json ({len(rows[:100])} tracks)")


if __name__ == "__main__":
    main()
