#!/usr/bin/env python3
"""Fetch Melon TOP100 and attach official song / YouTube Official Audio links."""

from __future__ import annotations

import argparse
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
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
AUDIO_GOOD = re.compile(r"official\s*audio|\[audio\]|\(audio\)|audio version|official lyric audio", re.I)
MV_GOOD = re.compile(r"official\s*m\.?v|official\s*music\s*video|뮤직\s*비디오|music\s*video", re.I)
AUDIO_BAD = re.compile(r"official\s*m\.?v|music\s*video|뮤직\s*비디오|special video|performance|dance practice|color coded|lyrics|가사|live|fancam|직캠", re.I)
MV_BAD = re.compile(r"official\s*audio|color coded|lyrics|가사|dance practice|fancam", re.I)
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
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def norm(text):
    text = re.sub(r"\([^)]*\)", " ", text or "")
    return re.sub(r"[^a-z0-9가-힣]+", "", text.lower())


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
    kind = "up" if "rank_up" in block else "down" if "rank_down" in block else "same"
    match = re.search(r'bullet_icons rank_\w+".*?<span class="none">(\d+)</span>', block, re.S)
    return kind, int(match.group(1)) if match else 0


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
            "ytAudioTitle": "", "ytMvTitle": "", "ytAudioKind": "",
            "genieUrl": "", "bugsUrl": "", "appleUrl": "", "spotifyUrl": "", "vibeUrl": "", "deezerUrl": "",
        })
    return tracks


def parse_chart_time(html):
    match = re.search(r"(20\d{2}\.\d{2}\.\d{2})\s*(\d{1,2}:\d{2})?", html)
    return " ".join(part for part in match.groups() if part) if match else ""


def previous_map(previous):
    mapping = {}
    for track in (previous or {}).get("tracks") or []:
        mapping[f"{track.get('title', '')}|{track.get('artist', '')}"] = track
    return mapping


def youtube_search(query, n=6):
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return []
    try:
        result = subprocess.run(
            [yt_dlp, "--skip-download", "--no-playlist", "--flat-playlist",
             "--print", "%(id)s\t%(title)s\t%(channel)s", f"ytsearch{n}:{query}"],
            check=False, capture_output=True, text=True, timeout=45,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    rows = []
    for line in (result.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and YOUTUBE_ID_RE.match(parts[0].strip()):
            rows.append({"id": parts[0].strip(), "title": parts[1].strip(), "channel": parts[2].strip() if len(parts) > 2 else ""})
    return rows


def artist_ok(artist, blob):
    blob_n = norm(blob)
    ok = False
    for part in re.split(r"[/|,&]|feat\.?", artist or "", flags=re.I):
        hangul = re.sub(r"[^가-힣]", "", part)
        ascii_ = re.sub(r"[^a-z0-9]", "", part.lower())
        if len(hangul) >= 2 and hangul in blob_n:
            ok = True
        if len(ascii_) >= 3 and ascii_ in blob_n:
            ok = True
    return ok


def good_audio(song, artist, yt_title, channel=""):
    if not yt_title or AUDIO_BAD.search(yt_title) or not AUDIO_GOOD.search(yt_title):
        return False
    blob = f"{yt_title} {channel}"
    if not artist_ok(artist, blob):
        return False
    if norm(song) in norm(yt_title):
        return True
    return "jxs_bp" in (channel or "").lower()


def good_mv(song, artist, yt_title, channel=""):
    if not yt_title or MV_BAD.search(yt_title) or not MV_GOOD.search(yt_title):
        return False
    if norm(song) not in norm(yt_title):
        return False
    return artist_ok(artist, f"{yt_title} {channel}")


def pick_youtube(kind, title, artist, extra=False):
    queries = [f"{title} {artist} Official Audio" if kind == "audio" else f"{title} {artist} Official MV"]
    if extra:
        queries.append(f"{artist} {title} Official Audio" if kind == "audio" else f"{artist} {title} Official MV")
    best = None
    for query in queries:
        for row in youtube_search(query):
            if kind == "audio" and not good_audio(title, artist, row["title"], row["channel"]):
                continue
            if kind == "mv" and not good_mv(title, artist, row["title"], row["channel"]):
                continue
            best = row
            break
        if best:
            break
    return (best["id"], best["title"]) if best else ("", "")


def apple_url(title, artist):
    for term in (f"{artist} {title}", f"{title} {artist}", title):
        raw = http_get(f"https://itunes.apple.com/search?term={urllib.parse.quote(term)}&entity=song&country=us&limit=5")
        for item in json.loads(raw).get("results") or []:
            url = item.get("trackViewUrl") or ""
            if url:
                return url.split("&uo=")[0]
    return ""


def vibe_url(title, artist):
    raw = http_get(
        "https://apis.naver.com/vibeWeb/musicapiweb/v3/search/track?query="
        + urllib.parse.quote(f"{title} {artist}") + "&start=1&display=1"
    )
    tracks = (((json.loads(raw).get("response") or {}).get("result") or {}).get("tracks")) or []
    return f"https://vibe.naver.com/track/{tracks[0]['trackId']}" if tracks else ""


def genie_url(title, artist):
    html = http_get("https://www.genie.co.kr/search/searchSong?query=" + urllib.parse.quote(f"{title} {artist}")).decode("utf-8", "replace")
    match = re.search(r"fnPlaySong\(['\"](\d+)", html)
    return f"https://www.genie.co.kr/detail/songInfo?xgnm={match.group(1)}" if match else ""


def bugs_url(title, artist):
    html = http_get("https://music.bugs.co.kr/search/track?q=" + urllib.parse.quote(f"{title} {artist}")).decode("utf-8", "replace")
    match = re.search(r"/track/(\d+)", html)
    return f"https://music.bugs.co.kr/track/{match.group(1)}" if match else ""


def deezer_url(title, artist):
    raw = http_get("https://api.deezer.com/search?q=" + urllib.parse.quote(f"{title} {artist}") + "&limit=1")
    items = json.loads(raw).get("data") or []
    return (items[0].get("link") or "") if items else ""


def attach_links(tracks, previous, mode="quick"):
    cached = previous_map(previous)
    extra = mode == "full"
    for track in tracks:
        old = cached.get(f"{track['title']}|{track['artist']}", {})
        for key in ("genieUrl", "bugsUrl", "appleUrl", "spotifyUrl", "vibeUrl", "deezerUrl"):
            track[key] = old.get(key) or ""
        old_audio, old_audio_title = old.get("ytAudioId") or "", old.get("ytAudioTitle") or ""
        old_mv, old_mv_title = old.get("ytMvId") or "", old.get("ytMvTitle") or ""
        if old_audio and good_audio(track["title"], track["artist"], old_audio_title):
            track["ytAudioId"], track["ytAudioTitle"], track["ytAudioKind"] = old_audio, old_audio_title, "audio"
        else:
            track["ytAudioId"], track["ytAudioTitle"] = pick_youtube("audio", track["title"], track["artist"], extra=extra)
            track["ytAudioKind"] = "audio" if track["ytAudioId"] else ""
        if old_mv and good_mv(track["title"], track["artist"], old_mv_title):
            track["ytMvId"], track["ytMvTitle"] = old_mv, old_mv_title
        else:
            track["ytMvId"], track["ytMvTitle"] = pick_youtube("mv", track["title"], track["artist"], extra=extra)
        resolvers = {"genieUrl": genie_url, "bugsUrl": bugs_url, "appleUrl": apple_url, "vibeUrl": vibe_url, "deezerUrl": deezer_url}
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
        print(f"{track['rank']:3} {track['title']} audio={track['ytAudioId'] or '-'} mv={track['ytMvId'] or '-'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    args = parser.parse_args()
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
    attach_links(tracks, previous, mode=args.mode)
    payload = {
        "source": "Melon TOP100",
        "sourceUrl": CHART_URL,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "chartTime": parse_chart_time(html),
        "count": len(tracks),
        "mode": args.mode,
        "tracks": tracks,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audio = sum(1 for t in tracks if t.get("ytAudioId"))
    print(f"wrote {out} ({len(tracks)} tracks, audio={audio}, mode={args.mode})")


if __name__ == "__main__":
    main()
