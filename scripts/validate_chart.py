#!/usr/bin/env python3
"""Conservative CI checks for the generated chart data."""
import json
import re
from pathlib import Path

def load(name):
    p=Path(name)
    if not p.exists(): raise SystemExit(f"missing {name}")
    return json.loads(p.read_text(encoding="utf-8"))

chart=load("chart.json")
tracks=chart.get("tracks") or []
assert tracks, "chart.json has no tracks"

bad_audio_words=("official mv","official music video","music video","special video","performance","dance practice","color coded","lyrics","lyric video","가사","live","fancam","직캠","teaser","trailer","shorts")
for t in tracks:
    aid=t.get("ytAudioId") or ""
    amid=t.get("ytMvId") or ""
    title=(t.get("ytAudioTitle") or "").lower()
    channel=(t.get("ytAudioChannel") or "").lower()
    if aid and aid == amid:
        raise SystemExit(f"audio/mv duplicate: {t.get('title')} -> {aid}")
    if aid and any(w in title for w in bad_audio_words):
        raise SystemExit(f"blocked audio title: {t.get('title')} -> {t.get('ytAudioTitle')}")
    if aid and not title:
        raise SystemExit(f"audio id has no title metadata: {t.get('title')}")
    if aid and not channel:
        raise SystemExit(f"audio id has no channel metadata: {t.get('title')}")
    if aid:
        artist = (t.get("artist") or "").lower()
        channel_compact = re.sub(r"[^a-z0-9가-힣]+", "", channel)
        artist_aliases = [
            re.sub(r"[^a-z0-9가-힣]+", "", part.lower())
            for part in re.split(r"[/|,&]|\\bfeat\\.?\\b|\\bwith\\b", artist)
            if re.sub(r"[^a-z0-9가-힣]+", "", part.lower())
        ]
        if not any(
            channel_compact == alias or
            (channel_compact.endswith("topic") and alias in channel_compact[:-5])
            for alias in artist_aliases
        ):
            raise SystemExit(f"unverified audio channel: {t.get('title')} -> {t.get('ytAudioChannel')}")
    apple = t.get("appleUrl") or ""
    if apple and not re.match(r"^https://music\\.apple\\.com/kr/", apple):
        raise SystemExit(f"non-KR or malformed Apple Music URL: {t.get('title')} -> {apple}")

yt=load("youtube_chart.json")
yt_tracks=yt.get("tracks") or []
assert len(yt_tracks) >= 50, "youtube chart has too few tracks"
ranks=[x.get("rank") for x in yt_tracks]
assert len(ranks)==len(set(ranks)), "duplicate YouTube ranks"
assert ranks==sorted(ranks), "YouTube ranks are not sorted"
print(f"validated Melon {len(tracks)} tracks and YouTube {len(yt_tracks)} tracks")
