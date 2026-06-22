"""
음원 메타데이터 생성 — abc 송 A~O 의 YouTube/IG/배급사 업로드용 텍스트 일괄 생성.

[입력] data/music_tracks.json  (data/music_tracks.example.json 형식)
[출력] docs/music/<code>_<title>.md  (곡별 복붙용 메타 묶음)

각 곡마다:
  - YouTube 제목 + 설명 + 태그 (풀버전 영상 업로드용)
  - IG(@sunnyandgigi) Reels 캡션 (재업로드용 + 원본오디오 부트스트랩)
  - 배급사(DistroKid/Amuse) 메타 필드 (발매용 — 곡명/장르/ISRC 자리)
  - daily_enter_kr 연동 크레딧 (MUSIC_* 시크릿 값)

곡 정보는 사람이 채우고, 이 스크립트는 일관된 포맷으로 펼쳐줄 뿐.
SEO 키워드/해시태그는 genre/mood/theme 에서 자동 파생.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRACKS_PATH = ROOT / "data" / "music_tracks.json"
OUT_DIR = ROOT / "docs" / "music"


def _hashtags(track: dict, artist: str) -> list:
    """곡 정보(장르/무드/테마/사용자 지정 태그)에서만 파생 — 장르 하드코딩 없음.
    track 에 "hashtags" 배열을 직접 주면 그것을 최우선 사용."""
    # 사용자가 명시한 태그 우선
    explicit = [t if t.startswith("#") else f"#{t}" for t in track.get("hashtags", [])]
    genre = (track.get("genre") or "").strip()
    genretag = [f"#{genre.replace(' ', '').replace('/', '')}"] if genre else []
    moodtags = [f"#{m}" for m in track.get("mood", [])]
    titletag = []
    title = (track.get("title") or "").strip()
    if title:
        titletag = [f"#{title.replace(' ', '')}"]
    artisttag = ["#" + artist.replace(" ", "").replace("&", "")]
    seen, out = set(), []
    for t in explicit + titletag + genretag + moodtags + artisttag:
        if t and t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return out[:15]


def _youtube_meta(track: dict, artist: str) -> dict:
    title = track.get("title", "")
    tags = _hashtags(track, artist)
    yt_title = f"{title} | {artist} 오리지널 동요"
    desc = "\n".join([
        f"{artist} 의 오리지널 곡 '{title}'",
        track.get("theme", ""),
        "",
        f"🎵 작사·작곡: {artist}",
        f"장르: {track.get('genre','')} · {track.get('language','한국어')}",
        "",
        "🔔 구독하고 새 곡 받아보세요",
        "",
        " ".join(tags[:5]),
    ])
    return {"title": yt_title[:100], "description": desc, "tags": tags}


def _ig_caption(track: dict, artist: str, handle_yt: str) -> str:
    title = track.get("title", "")
    tags = _hashtags(track, artist)
    return "\n".join([
        f"🎵 {title} — {artist} 오리지널",
        track.get("theme", ""),
        "",
        f"풀버전 ▶ 프로필 링크 ({handle_yt})",
        "이 음원 자유롭게 사용하세요 💛",
        "",
        " ".join(tags[:12]),
    ])


def _distributor_fields(track: dict, artist: str) -> dict:
    return {
        "곡명 (Track Title)": track.get("title", ""),
        "아티스트 (Primary Artist)": artist,
        "장르 (Genre)": track.get("genre", ""),
        "언어 (Language)": track.get("language", "Korean"),
        "작사 (Songwriter)": artist,
        "작곡 (Composer)": artist,
        "ISRC": "(배급사 자동 생성)",
        "발매 형태": "EP 묶음 권장 (3곡/월)",
        "커버 아트": "3000×3000 PNG (텍스트 30% 이하)",
        "마스터 파일": "WAV 또는 320kbps MP3",
    }


def _render_md(track: dict, artist: str, handle_ig: str, handle_yt: str) -> str:
    code = track.get("code", "?")
    title = track.get("title", "")
    yt = _youtube_meta(track, artist)
    ig = _ig_caption(track, artist, handle_yt)
    dist = _distributor_fields(track, artist)
    yt_url = track.get("yt_url", "") or "(업로드 후 채우기)"

    dist_rows = "\n".join(f"| {k} | {v} |" for k, v in dist.items())
    tag_line = " ".join(yt["tags"])

    return f"""# {code}. {title} — 메타데이터 묶음

> {artist} · 복붙용. 곡 정보: {track.get('genre','')} / {', '.join(track.get('mood',[]))}

## 1) YouTube (@{handle_yt.lstrip('@')}) 풀버전 업로드

**제목**
```
{yt['title']}
```

**설명**
```
{yt['description']}
```

**태그**
```
{tag_line}
```

## 2) Instagram ({handle_ig}) Reels 재업로드 + 원본오디오 부트스트랩

**캡션**
```
{ig}
```

> 게시 후 음원 아이콘 탭 → "{handle_ig} · 원본 오디오" 라벨 확인.
> 이게 daily_enter_kr 자동 게시의 fingerprint 매칭 시드가 됨.

## 3) 배급사(DistroKid/Amuse) 발매 메타

| 필드 | 값 |
|---|---|
{dist_rows}

## 4) daily_enter_kr 연동 (GitHub Secrets)

이 곡을 daily_enter_kr BGM 으로 쓸 때 설정:
```
MUSIC_YT_URL   = {yt_url}
MUSIC_TITLE    = {title}
MUSIC_HANDLE   = {handle_ig}
```
→ 캡션·댓글·YT설명에 자동으로 "🎵 배경음악: {title} — {handle_ig} · 풀버전 ▶ 링크" 노출.
"""


def main() -> int:
    if not TRACKS_PATH.exists():
        print(f"❌ {TRACKS_PATH} 없음.")
        print(f"   data/music_tracks.example.json 을 data/music_tracks.json 으로 복사 후 곡 정보 채우세요.")
        return 1
    data = json.loads(TRACKS_PATH.read_text(encoding="utf-8"))
    artist = data.get("artist", "Sunny & Gigi")
    handle_ig = data.get("artist_handle_ig", "@sunnyandgigi.official")
    handle_yt = data.get("artist_handle_yt", "@sunnyandgigi")
    tracks = data.get("tracks", [])
    if not tracks:
        print("❌ tracks 비어있음")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for t in tracks:
        code = t.get("code", "X")
        title = (t.get("title", "track") or "track").replace("/", "-").replace(" ", "_")
        out = OUT_DIR / f"{code}_{title}.md"
        out.write_text(_render_md(t, artist, handle_ig, handle_yt), encoding="utf-8")
        print(f"  ✓ {out.relative_to(ROOT)}")
    print(f"\n✅ {len(tracks)}곡 메타데이터 생성 → {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
