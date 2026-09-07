#!/usr/bin/env python3
"""Fetch Melon TOP100 and attach direct official streaming / YouTube links."""

from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHART_URL = "https://www.melon.com/chart/index.htm"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def http_get(url, timeout=15):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_html():
    request = urllib.request.Request(CHART_URL, headers={**HEADERS, "Referer": "https://www.melon.com/"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_change(block):
    if "rank_new" in block:
        return "new", 0
    if "rank_up" in block:
        kind = "up"
    elif "rank_down" in block:
        kind = "down"
    else:
        kind = "same"
    match = re.search(r'bullet_icons rank_\w+".*?<span class="none">(\d+)</span>', block, re.S)
    delta = int(match.group(1)) if match else 0
    return kind, delta


def parse_tracks(html):
    rows = re.findall(r'<tr class="lst(?:50|100)"[^>]*data-song-no="(\d+)"[^>]*>(.*?)</tr>', html, re.S)
    tracks = []
    for song_id, block in rows:
        rank_m = re.search(r'<span class="rank\s*">\s*(\d+)\s*</span>', block)
        title_m = re.search(r'class="ellipsis rank01".*?<a[^>]*>(.*?)</a>', block, re.S)
        artist_m = re.search(r'class="ellipsis rank02".*?<a[^>]*>(.*?)</a>', block, re.S)
        album_m = re.search(r'class="ellipsis rank03".*?<a[^>]*>(.*?)</a>', block, re.S)
        img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
        change, delta = parse_change(block)
        image = (img_m.group(1) if img_m else "").split("/melon/")[0]
        tracks.append({
            "rank": int(rank_m.group(1)) if rank_m else len(tracks) + 1,
            "title": clean(title_m.group(1) if title_m else ""),
            "artist": clean(artist_m.group(1) if artist_m else ""),
            "album": clean(album_m.group(1) if album_m else ""),
            "image": image,
            "songId": song_id,
            "change": change,
            "delta": delta,
            "url": f"https://www.melon.com/song/detail.htm?songId={song_id}",
            "ytMvId": "", "ytAudioId": "", "ytMvUrl": "", "ytAudioUrl": "", "ytMusicUrl": "",
            "genieUrl": "", "bugsUrl": "", "appleUrl": "", "spotifyUrl": "", "vibeUrl": "", "deezerUrl": "",
        })
    return tracks


def parse_chart_time(html):
    match = re.search(r"(20\d{2}\.\d{2}\.\d{2})\s*(\d{1,2}:\d{2})?", html)
    if not match:
        return ""
    return " ".join(part for part in match.groups() if part)


def previous_map(previous):
    mapping = {}
    if not previous:
        return mapping
    for track in previous.get("tracks") or []:
        mapping[f"{track.get('title', '')}|{track.get('artist', '')}"] = track
    return mapping


def youtube_id(query):
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return ""
    try:
        result = subprocess.run(
            [yt_dlp, "--skip-download", "--no-playlist", "--flat-playlist", "--print", "id", f"ytsearch1:{query}"],
            check=False, capture_output=True, text=True, timeout=40,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    lines = (result.stdout or "").strip().splitlines()
    video_id = lines[0].strip() if lines else ""
    return video_id if YOUTUBE_ID_RE.match(video_id) else ""


def apple_url(title, artist):
    for term in (f"{artist} {title}", f"{title} {artist}", title):
        query = urllib.parse.quote(term)
        raw = http_get(f"https://itunes.apple.com/search?term={query}&entity=song&country=us&limit=5")
        data = json.loads(raw)
        for item in data.get("results") or []:
            url = item.get("trackViewUrl") or ""
            if url:
                return url.split("&uo=")[0]
    return ""


def vibe_url(title, artist):
    query = urllib.parse.quote(f"{title} {artist}")
    raw = http_get(f"https://apis.naver.com/vibeWeb/musicapiweb/v3/search/track?query={query}&start=1&display=1")
    data = json.loads(raw)
    tracks = (((data.get("response") or {}).get("result") or {}).get("tracks")) or []
    if tracks:
        return f"https://vibe.naver.com/track/{tracks[0]['trackId']}"
    return ""


def genie_url(title, artist):
    query = urllib.parse.quote(f"{title} {artist}")
    html = http_get(f"https://www.genie.co.kr/search/searchSong?query={query}").decode("utf-8", "replace")
    match = re.search(r"fnPlaySong\(['\"](\d+)", html)
    return f"https://www.genie.co.kr/detail/songInfo?xgnm={match.group(1)}" if match else ""


def bugs_url(title, artist):
    query = urllib.parse.quote(f"{title} {artist}")
    html = http_get(f"https://music.bugs.co.kr/search/track?q={query}").decode("utf-8", "replace")
    match = re.search(r"/track/(\d+)", html)
    return f"https://music.bugs.co.kr/track/{match.group(1)}" if match else ""


def deezer_url(title, artist):
    query = urllib.parse.quote(f"{title} {artist}")
    raw = http_get(f"https://api.deezer.com/search?q={query}&limit=1")
    data = json.loads(raw)
    items = data.get("data") or []
    return (items[0].get("link") or "") if items else ""


def attach_links(tracks, previous):
    cached = previous_map(previous)
    for track in tracks:
        old = cached.get(f"{track['title']}|{track['artist']}", {})
        for key in ("ytMvId", "ytAudioId", "genieUrl", "bugsUrl", "appleUrl", "spotifyUrl", "vibeUrl", "deezerUrl"):
            track[key] = old.get(key) or ""
        if not track["ytAudioId"]:
            track["ytAudioId"] = youtube_id(f"{track['title']} {track['artist']} Official Audio")
        if not track["ytMvId"]:
            track["ytMvId"] = youtube_id(f"{track['title']} {track['artist']} Official MV")
        resolvers = {
            "genieUrl": genie_url,
            "bugsUrl": bugs_url,
            "appleUrl": apple_url,
            "vibeUrl": vibe_url,
            "deezerUrl": deezer_url,
        }
        for key, fn in resolvers.items():
            if not track[key]:
                try:
                    track[key] = fn(track["title"], track["artist"])
                except Exception:
                    track[key] = ""
        if track["ytMvId"]:
            track["ytMvUrl"] = f"https://www.youtube.com/watch?v={track['ytMvId']}"
        if track["ytAudioId"]:
            track["ytAudioUrl"] = f"https://www.youtube.com/watch?v={track['ytAudioId']}"
            track["ytMusicUrl"] = f"https://music.youtube.com/watch?v={track['ytAudioId']}"
        print(f"{track['rank']:3} {track['title']} audio={track['ytAudioId'] or '-'}")


def main():
    html = fetch_html()
    tracks = parse_tracks(html)
    if len(tracks) < 50:
        raise SystemExit(f"expected at least 50 tracks, got {len(tracks)}")
    out = Path("chart.json")
    previous = None
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = None
    attach_links(tracks, previous)
    payload = {
        "source": "Melon TOP100",
        "sourceUrl": CHART_URL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "chartTime": parse_chart_time(html),
        "count": len(tracks),
        "tracks": tracks,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(tracks)} tracks, chartTime={payload['chartTime']})")


if __name__ == "__main__":
    main()
