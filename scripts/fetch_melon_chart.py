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

def score_audio(song, artist, title, channel):
    if not title or AUDIO_NEG.search(title) or not AUDIO_POS.search(title): return -999
    score=0
    if re.search(r"official\s*audio",title,re.I): score+=100
    elif re.search(r"officialaudio",title,re.I): score+=95
    else: score+=65
    if title_match(song,title): score+=40
    if artist_match(artist,title): score+=25
    if artist_match(artist,channel): score+=35
    if OFFICIAL.search(channel): score+=20
    return score if score>=100 else -999

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

def attach_links(tracks, previous, mode):
    prev={f"{x.get('title','')}|{x.get('artist','')}":x for x in (previous or {}).get("tracks",[])}
    full=mode=="full"
    for t in tracks:
        old=prev.get(f"{t['title']}|{t['artist']}",{})
        for k in ("genieUrl","bugsUrl","appleUrl","spotifyUrl","vibeUrl","deezerUrl"): t[k]=old.get(k,"")
        if full or not valid_cached_audio(t,old):
            aid,atitle,ach=pick("audio",t["title"],t["artist"],full)
        else:
            aid,atitle,ach=old.get("ytAudioId",""),old.get("ytAudioTitle",""),old.get("ytAudioChannel","")
        if full or not valid_cached_mv(t,old):
            mid,mtitle,mch=pick("mv",t["title"],t["artist"],full)
        else:
            mid,mtitle,mch=old.get("ytMvId",""),old.get("ytMvTitle",""),old.get("ytMvChannel","")
        if aid and mid and aid==mid: mid,mtitle,mch="","",""
        t["ytAudioId"],t["ytAudioTitle"],t["ytAudioChannel"],t["ytAudioKind"]=aid,atitle,ach,"audio" if aid else ""
        t["ytMvId"],t["ytMvTitle"],t["ytMvChannel"]=mid,mtitle,mch
        t["ytAudioUrl"]=f"https://www.youtube.com/watch?v={aid}" if aid else ""
        t["ytMusicUrl"]=f"https://music.youtube.com/watch?v={aid}" if aid else ""
        t["ytMvUrl"]=f"https://www.youtube.com/watch?v={mid}" if mid else ""
        print(f"{t['rank']:3} {t['title']} audio={aid or '-'} mv={mid or '-'}")
        # Preserve existing streaming links; they are resolved by the existing site data flow.
        
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
