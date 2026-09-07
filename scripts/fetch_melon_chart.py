#!/usr/bin/env python3
"""Fetch Melon TOP100 and conservatively select YouTube Official Audio/MV candidates."""

from __future__ import annotations
import argparse, html as html_lib, json, re, shutil, subprocess, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHART_URL = "https://www.melon.com/chart/index.htm"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
YID = re.compile(r"^[A-Za-z0-9_-]{11}$")
AUDIO_POS = re.compile(r"official\s*audio|officialaudio|\[audio\]|\(audio\)|audio\s*version", re.I)
AUDIO_NEG = re.compile(r"official\s*m\.?v|official\s*music\s*video|music\s*video|뮤직\s*비디오|special\s*video|performance(?:\s*video)?|dance\s*practice|color\s*coded|lyrics?|lyric\s*video|가사|live|fancam|직캠|teaser|trailer|shorts", re.I)
MV_POS = re.compile(r"official\s*m\.?v|official\s*music\s*video", re.I)
MV_NEG = re.compile(r"official\s*audio|audio|special\s*video|performance|dance\s*practice|color\s*coded|lyrics?|가사|live|fancam|직캠|teaser|trailer|shorts", re.I)
OFFICIAL = re.compile(r"official|vevo|smtown|jyp|yg|hybe|ador|source music|pledis|belift|koz|starship|cube|rbw|kq|wakeone", re.I)

def clean(s):
    s = html_lib.unescape(re.sub(r"<[^>]+>", "", s or ""))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

def norm(s):
    return re.sub(r"[^a-z0-9가-힣]+", "", (s or "").lower())

def get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
        return r.read()

def fetch_html():
    return get(CHART_URL, 30).decode("utf-8", "replace")

def parse_change(block):
    if "rank_new" in block: return "new", 0
    kind = "up" if "rank_up" in block else "down" if "rank_down" in block else "same"
    m = re.search(r'bullet_icons rank_\w+".*?<span class="none">(\d+)</span>', block, re.S)
    return kind, int(m.group(1)) if m else 0

def parse_tracks(html):
    rows = re.findall(r'<tr class="lst(?:50|100)"[^>]*data-song-no="(\d+)"[^>]*>(.*?)</tr>', html, re.S)
    out = []
    for sid, b in rows:
        rm = re.search(r'<span class="rank\s*">\s*(\d+)\s*</span>', b)
        tm = re.search(r'class="ellipsis rank01".*?<a[^>]*>(.*?)</a>', b, re.S)
        am = re.search(r'class="ellipsis rank02".*?<a[^>]*>(.*?)</a>', b, re.S)
        bm = re.search(r'class="ellipsis rank03".*?<a[^>]*>(.*?)</a>', b, re.S)
        im = re.search(r'<img[^>]+src="([^"]+)"', b)
        change, delta = parse_change(b)
        out.append({
            "rank": int(rm.group(1)) if rm else len(out)+1,
            "title": clean(tm.group(1) if tm else ""),
            "artist": clean(am.group(1) if am else ""),
            "album": clean(bm.group(1) if bm else ""),
            "image": (im.group(1) if im else "").split("/melon/")[0],
            "songId": sid, "change": change, "delta": delta,
            "url": f"https://www.melon.com/song/detail.htm?songId={sid}",
            "ytMvId":"","ytAudioId":"","ytMvUrl":"","ytAudioUrl":"","ytMusicUrl":"",
            "ytAudioTitle":"","ytAudioChannel":"","ytAudioKind":"",
            "ytMvTitle":"","ytMvChannel":"",
            "genieUrl":"","bugsUrl":"","appleUrl":"","spotifyUrl":"","vibeUrl":"","deezerUrl":""
        })
    return out

def youtube_search(query, n=10):
    exe = shutil.which("yt-dlp")
    if not exe: return []
    try:
        p = subprocess.run([exe,"--skip-download","--no-playlist","--flat-playlist","--print","%(id)s\t%(title)s\t%(channel)s",f"ytsearch{n}:{query}"], capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired):
        return []
    out=[]
    for line in p.stdout.splitlines():
        a=line.split("\t")
        if len(a)>=2 and YID.match(a[0].strip()):
            out.append({"id":a[0].strip(),"title":a[1].strip(),"channel":a[2].strip() if len(a)>2 else ""})
    return out

def artist_match(artist, text):
    b=norm(text)
    for part in re.split(r"[/|,&]|\bfeat\.?\b|\bwith\b", artist or "", flags=re.I):
        h=re.sub(r"[^가-힣]","",part)
        e=re.sub(r"[^a-z0-9]","",part.lower())
        if (len(h)>=2 and h in b) or (len(e)>=3 and e in b): return True
    return False

def title_match(song, text):
    a,b=norm(song),norm(text)
    return bool(a) and a in b

def channel_is_artist_or_topic(artist, channel):
    """
    YouTube Music commonly exposes auto-generated official releases as
    "<Artist> - Topic". Also accept a channel whose name is the artist/group
    itself. A random uploader saying "Official Audio" is NOT sufficient.
    """
    ch = norm(channel)
    ar = norm(artist)
    if not ch or not ar:
        return False
    if ch == ar:
        return True
    if ch.endswith("topic") and ar in ch[:-5]:
        return True
    # Handle punctuation/spacing differences in "<Artist> - Topic".
    return bool(re.search(r"topic$", channel or "", re.I) and ar in ch)

def score_audio(song, artist, title, channel):
    if not title or AUDIO_NEG.search(title) or not AUDIO_POS.search(title): return -999

    # Channel provenance is mandatory for Audio. This prevents a third-party
    # uploader from being accepted merely because its title contains
    # "Official Audio".
    artist_or_topic = channel_is_artist_or_topic(artist, channel)
    label_channel = bool(OFFICIAL.search(channel or ""))
    if not artist_or_topic and not label_channel:
        return -999

    score=0
    if re.search(r"official\s*audio",title,re.I): score+=100
    elif re.search(r"officialaudio",title,re.I): score+=95
    elif re.search(r"\[audio\]|\(audio\)|audio\s*version",title,re.I): score+=65

    if title_match(song,title): score+=40
    if artist_match(artist,title): score+=25
    if artist_or_topic: score+=70
    elif artist_match(artist,channel): score+=25
    if label_channel: score+=20

    # For a true artist/Topic channel, an explicit Audio marker is enough.
    return score if score>=135 else -999

def score_mv(song, artist, title, channel):
    # A different song must never become the MV just because it is from
    # the same artist and is an Official MV.
    if not title or MV_NEG.search(title) or not MV_POS.search(title): return -999
    if not title_match(song, title): return -999
    score=80
    if re.search(r"official\s*music\s*video",title,re.I): score+=20
    score+=40
    if artist_match(artist,title): score+=25
    if artist_match(artist,channel): score+=30
    if OFFICIAL.search(channel): score+=20
    return score if score>=120 else -999

def pick(kind, song, artist, full):
    qs = ([f"{song} {artist} Official Audio", f"{artist} {song} Official Audio"] if kind=="audio"
          else [f"{song} {artist} Official MV", f"{artist} {song} Official MV"])
    candidates={}
    for q in (qs if full else qs[:1]):
        for row in youtube_search(q,10): candidates[row["id"]]=row
    scored=[]
    fn=score_audio if kind=="audio" else score_mv
    for row in candidates.values():
        s=fn(song,artist,row["title"],row["channel"])
        if s>=0: scored.append((s,row))
    if not scored: return "", "", ""
    scored.sort(key=lambda x:(-x[0], x[1]["id"]))
    r=scored[0][1]
    return r["id"],r["title"],r["channel"]

def valid_cached_audio(t, old):
    return bool(old.get("ytAudioId") and score_audio(t["title"],t["artist"],old.get("ytAudioTitle",""),old.get("ytAudioChannel",""))>=100)

def valid_cached_mv(t, old):
    return bool(old.get("ytMvId") and score_mv(t["title"],t["artist"],old.get("ytMvTitle",""),old.get("ytMvChannel",""))>=120)


def apple_url(title, artist):
    for term in (f"{artist} {title}", f"{title} {artist}", title):
        try:
            raw = get(f"https://itunes.apple.com/search?term={urllib.parse.quote(term)}&entity=song&country=us&limit=5")
            data = json.loads(raw)
            target = norm(title)
            a = norm(artist)
            ranked = []
            for item in data.get("results") or []:
                it = norm(item.get("trackName",""))
                ia = norm(item.get("artistName",""))
                if target and target in it:
                    ranked.append((2 if a and a in ia else 0, item.get("trackViewUrl","")))
            for _, url in sorted(ranked, reverse=True):
                if url: return url.split("&uo=")[0]
        except Exception:
            continue
    return ""

def vibe_url(title, artist):
    try:
        raw = get(f"https://apis.naver.com/vibeWeb/musicapiweb/v3/search/track?query={urllib.parse.quote(title + ' ' + artist)}&start=1&display=5")
        data = json.loads(raw)
        tracks = (((data.get("response") or {}).get("result") or {}).get("tracks")) or []
        target, art = norm(title), norm(artist)
        best = None
        for item in tracks:
            name = norm(item.get("trackTitle","") or item.get("title",""))
            an = norm(" ".join(x.get("artistName","") for x in (item.get("artists") or [])))
            score = (50 if target and target in name else 0) + (50 if art and art in an else 0)
            if best is None or score > best[0]:
                best = (score, item)
        if best and best[0] >= 50:
            tid = best[1].get("trackId")
            if tid: return f"https://vibe.naver.com/track/{tid}"
    except Exception:
        pass
    return ""

def genie_url(title, artist):
    try:
        html = get(f"https://www.genie.co.kr/search/searchSong?query={urllib.parse.quote(title + ' ' + artist)}").decode("utf-8","replace")
        ids = re.findall(r"fnPlaySong\(['\"](\d+)", html)
        return f"https://www.genie.co.kr/detail/songInfo?xgnm={ids[0]}" if ids else ""
    except Exception:
        return ""

def bugs_url(title, artist):
    try:
        html = get(f"https://music.bugs.co.kr/search/track?q={urllib.parse.quote(title + ' ' + artist)}").decode("utf-8","replace")
        ids = re.findall(r"/track/(\d+)", html)
        return f"https://music.bugs.co.kr/track/{ids[0]}" if ids else ""
    except Exception:
        return ""

def deezer_url(title, artist):
    try:
        raw = get(f"https://api.deezer.com/search?q={urllib.parse.quote(title + ' ' + artist)}&limit=5")
        data = json.loads(raw)
        target, art = norm(title), norm(artist)
        best = None
        for item in data.get("data") or []:
            score = (60 if target and target in norm(item.get("title","")) else 0) + (40 if art and art in norm((item.get("artist") or {}).get("name","")) else 0)
            if best is None or score > best[0]: best = (score, item)
        if best and best[0] >= 60:
            return best[1].get("link") or ""
    except Exception:
        pass
    return ""

def attach_links(tracks, previous, mode):
    prev={f"{x.get('title','')}|{x.get('artist','')}":x for x in (previous or {}).get("tracks",[])}
    full=mode=="full"
    for t in tracks:
        old=prev.get(f"{t['title']}|{t['artist']}",{})

        # Full mode deliberately rematches every service and every YouTube candidate.
        # Quick mode reuses only validated YouTube cache and existing direct service URLs.
        if full:
            aid,atitle,ach=pick("audio",t["title"],t["artist"],True)
            mid,mtitle,mch=pick("mv",t["title"],t["artist"],True)
        elif valid_cached_audio(t,old):
            aid,atitle,ach=old.get("ytAudioId",""),old.get("ytAudioTitle",""),old.get("ytAudioChannel","")
            mid,mtitle,mch=(old.get("ytMvId",""),old.get("ytMvTitle",""),old.get("ytMvChannel","")) if valid_cached_mv(t,old) else pick("mv",t["title"],t["artist"],False)
        else:
            aid,atitle,ach=pick("audio",t["title"],t["artist"],False)
            mid,mtitle,mch=pick("mv",t["title"],t["artist"],False)

        if aid and mid and aid==mid:
            mid,mtitle,mch="","",""

        t["ytAudioId"],t["ytAudioTitle"],t["ytAudioChannel"],t["ytAudioKind"]=aid,atitle,ach,"audio" if aid else ""
        t["ytMvId"],t["ytMvTitle"],t["ytMvChannel"]=mid,mtitle,mch
        t["ytAudioUrl"]=f"https://www.youtube.com/watch?v={aid}" if aid else ""
        t["ytMusicUrl"]=f"https://music.youtube.com/watch?v={aid}" if aid else ""
        t["ytMvUrl"]=f"https://www.youtube.com/watch?v={mid}" if mid else ""

        if full:
            # Re-resolve all direct streaming destinations instead of carrying
            # forward stale/mismatched cache entries.
            resolvers = {
                "genieUrl": genie_url, "bugsUrl": bugs_url,
                "appleUrl": apple_url, "vibeUrl": vibe_url, "deezerUrl": deezer_url,
            }
            for key, fn in resolvers.items():
                try:
                    t[key] = fn(t["title"], t["artist"]) or ""
                except Exception:
                    t[key] = ""
            # Spotify has no public unauthenticated track-ID resolver here;
            # preserve an existing direct URL, otherwise leave it empty.
            t["spotifyUrl"] = old.get("spotifyUrl","") or ""
        else:
            for key in ("genieUrl","bugsUrl","appleUrl","spotifyUrl","vibeUrl","deezerUrl"):
                t[key]=old.get(key,"") or ""

        print(f"{t['rank']:3} {t['title']} audio={aid or '-'} mv={mid or '-'} "
              f"genie={'Y' if t['genieUrl'] else '-'} bugs={'Y' if t['bugsUrl'] else '-'} "
              f"apple={'Y' if t['appleUrl'] else '-'} vibe={'Y' if t['vibeUrl'] else '-'} "
              f"deezer={'Y' if t['deezerUrl'] else '-'}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=("quick","full"),default="quick"); a=ap.parse_args()
    html=fetch_html(); tracks=parse_tracks(html)
    if len(tracks)<50: raise SystemExit(f"expected at least 50 tracks, got {len(tracks)}")
    out=Path("chart.json"); previous=None
    if out.exists():
        try: previous=json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError: pass
    attach_links(tracks,previous,a.mode)
    payload={"source":"Melon TOP100","sourceUrl":CHART_URL,"updatedAt":datetime.now(timezone.utc).isoformat(),"chartTime":re.search(r"(20\d{2}\.\d{2}\.\d{2})",html).group(1) if re.search(r"(20\d{2}\.\d{2}\.\d{2})",html) else "","count":len(tracks),"mode":a.mode,"tracks":tracks}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"wrote {out} ({len(tracks)} tracks, audio={sum(bool(x['ytAudioId']) for x in tracks)}, mode={a.mode})")

if __name__=="__main__": main()
