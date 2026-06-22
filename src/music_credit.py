"""
음악 크레딧 — abc 송(@sunnyandgigi) 트래픽 유도용 텍스트 블록 생성.

[왜 이 모듈이 필요한가 — 정직한 기술적 사실]
IG Reels Content Publishing API (Graph API) 는 "오디오 라이브러리 음원 선택"을
지원하지 않는다. video_url(mp4) 만 받고, 음원은 mp4 안에 합성(embed)된 트랙만 쓰인다.
즉 daily_enter_kr 자동 게시가 IG 오디오 라이브러리에서 "@sunnyandgigi 원본 오디오"를
직접 골라 붙이는 것은 API 로는 불가능.

→ 두 경로로 abc 송을 노출:
  1) [확실] mp4 에 abc.mp3 를 합성 → 영상에 음악이 깔림. 캡션/댓글/YT설명에
     "🎵 배경음악: 곡명 — @sunnyandgigi · 풀버전 ▶ YT링크" 텍스트 크레딧.
     이 텍스트 경로는 IG 내부 매칭과 무관하게 100% 작동.
  2) [보너스/불확실] IG 가 같은 오디오 fingerprint 를 @sunnyandgigi 원본오디오와
     자동 매칭하면 음원 라벨도 귀속됨. 보장 안 됨 — 게시 후 육안 확인 필요.

이 모듈은 1) 의 텍스트 크레딧을 캡션/댓글/YT설명용으로 생성한다.
환경변수 미설정 시 모두 빈 문자열 → 기존 동작 그대로 (하위호환).

[환경변수]
  MUSIC_YT_URL   — 풀버전 YouTube 링크 (예: https://youtu.be/abcd). 미설정 시 전체 off.
  MUSIC_TITLE    — 곡명 (예: "ABC송"). 기본 "오리지널 트랙".
  MUSIC_HANDLE   — 음악 계정 핸들 (예: "@sunnyandgigi"). 기본 빈.
"""

import os


def _cfg():
    url = (os.environ.get("MUSIC_YT_URL") or "").strip()
    title = (os.environ.get("MUSIC_TITLE") or "오리지널 트랙").strip()
    handle = (os.environ.get("MUSIC_HANDLE") or "").strip()
    return url, title, handle


def is_configured() -> bool:
    """MUSIC_YT_URL 이 있어야 크레딧 노출. 없으면 전체 skip."""
    url, _, _ = _cfg()
    return bool(url)


def caption_music_block() -> str:
    """IG 캡션용 음악 크레딧 블록 (여러 줄). 미설정 시 빈 문자열."""
    url, title, handle = _cfg()
    if not url:
        return ""
    who = f" — {handle}" if handle else ""
    return f"🎵 배경음악: {title}{who}\n   풀버전 ▶ {url}"


def comment_music_line() -> str:
    """IG 자동 댓글용 한 줄. 미설정 시 빈 문자열."""
    url, title, handle = _cfg()
    if not url:
        return ""
    who = f" {handle}" if handle else ""
    return f"🎵 BGM '{title}'{who} 풀버전 ▶ {url}"


def youtube_music_block() -> str:
    """YouTube 설명용 음악 크레딧 블록. YT 는 외부 링크 클릭 가능 → 가장 강한 경로.
    미설정 시 빈 문자열."""
    url, title, handle = _cfg()
    if not url:
        return ""
    who = f" — {handle}" if handle else ""
    return f"🎵 배경음악: {title}{who}\n▶ 풀버전: {url}"


if __name__ == "__main__":
    print("configured:", is_configured())
    print("--- caption ---"); print(caption_music_block())
    print("--- comment ---"); print(comment_music_line())
    print("--- youtube ---"); print(youtube_music_block())
