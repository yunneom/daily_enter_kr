"""
YouTube Shorts 자동 업로드 (YouTube Data API v3).

[왜]
멀티플랫폼 신디케이션 = faceless 자동화 계정 최대 수익 레버.
이미 만든 reel.mp4 (1080x1920, ~20s) 를 그대로 YouTube Shorts 로 업로드 →
한국 광고 수익 직접 발생 (YPP: 1K구독 + 90일 1천만뷰). IG 와 별개 수익원.

[인증 — CI 친화적 refresh token 방식]
브라우저 동의는 1회만 (로컬). 이후 CI 는 refresh_token 으로 access_token 자동 발급.
필요 시크릿:
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN
미설정 시 silently skip.

[일회성 셋업]
1. https://console.cloud.google.com → 새 프로젝트
2. "YouTube Data API v3" 사용 설정
3. OAuth 동의 화면 구성 (외부, 테스트 사용자에 본인 이메일)
4. 사용자 인증 정보 → OAuth 클라이언트 ID (데스크톱 앱) → CLIENT_ID/SECRET
5. 로컬에서 `python src/post_youtube.py --auth` 실행 → 브라우저 동의 → refresh_token 출력
6. 3개 값을 GitHub Secrets 에 저장

[제약]
- 업로드 1건 = 1,600 quota units. 기본 일 10,000 → 하루 ~6건 (우리 4건 OK)
- Shorts 인식 조건: 세로 영상 + 길이 3분 이내 + 제목/설명에 #Shorts
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Optional

import requests


OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=multipart&part=snippet,status"
)
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def is_configured() -> bool:
    return bool(
        os.environ.get("YOUTUBE_CLIENT_ID")
        and os.environ.get("YOUTUBE_CLIENT_SECRET")
        and os.environ.get("YOUTUBE_REFRESH_TOKEN")
    )


def _refresh_access_token() -> Optional[str]:
    """refresh_token → 단기 access_token 교환."""
    try:
        resp = requests.post(OAUTH_TOKEN_URL, data={
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }, timeout=20)
        if not resp.ok:
            print(f"  ❌ YouTube 토큰 갱신 실패 HTTP {resp.status_code}: {resp.text[:300]}")
            return None
        return resp.json().get("access_token")
    except Exception as e:
        print(f"  ❌ YouTube 토큰 갱신 예외: {e}")
        return None


def build_youtube_meta(title: str, hint: str, hashtags: List[str],
                       bio_url: str = "https://yunneom.github.io/daily_enter_kr/",
                       disclosure: str = "") -> tuple:
    """YouTube Shorts 제목 + 설명 빌드.

    제목: 토픽 제목 + #Shorts (Shorts 인식 필수)
    설명: 힌트 + 해시태그 + bio + 디스클로저
    """
    yt_title = f"{title} #Shorts"[:100]
    # 해시태그 정규화 (YouTube 는 설명 첫 3개를 제목 위에 표시)
    tag_line = " ".join(h for h in hashtags[:15])
    desc_lines = [
        title,
        "",
        hint,
        "",
        "👉 매일 새로운 밸런스 시리즈 · 구독 + 좋아요!",
        f"📲 추천템·전체 시리즈: {bio_url}",
        "",
        tag_line,
        "#Shorts #밸런스게임 #쇼츠",
    ]
    if disclosure:
        desc_lines += ["", f"({disclosure})"]
    return yt_title, "\n".join(desc_lines)


def upload_short(video_path: Path, title: str, description: str,
                 tags: Optional[List[str]] = None,
                 category_id: str = "24",  # 24 = Entertainment
                 privacy: str = "public") -> Optional[str]:
    """mp4 → YouTube Shorts 업로드. 성공 시 video_id, 실패/미설정 시 None."""
    if not is_configured():
        print("⏭️  YouTube 미설정 (YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN) — 스킵")
        return None
    token = _refresh_access_token()
    if not token:
        return None

    # 태그 정규화 (# 제거, 30개 한도)
    clean_tags = []
    for t in (tags or []):
        t = t.lstrip("#").strip()
        if t and t not in clean_tags:
            clean_tags.append(t)
        if len(clean_tags) >= 30:
            break

    meta = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": clean_tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    try:
        with open(video_path, "rb") as vf:
            video_bytes = vf.read()
        # multipart/related — metadata JSON + video binary
        files = {
            "metadata": ("metadata", json.dumps(meta), "application/json; charset=UTF-8"),
            "video": ("video", video_bytes, "video/*"),
        }
        print(f"[YouTube 1/1] Shorts 업로드 ({len(video_bytes)//1024}KB)...")
        resp = requests.post(
            UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=180,
        )
        if not resp.ok:
            print(f"  ❌ YouTube 업로드 실패 HTTP {resp.status_code}: {resp.text[:300]}")
            return None
        vid = resp.json().get("id")
        if vid:
            print(f"  ✅ YouTube Shorts 게시! https://youtube.com/shorts/{vid}")
        return vid
    except Exception as e:
        print(f"  ❌ YouTube 업로드 예외: {e}")
        return None


def _run_auth_flow():
    """로컬 1회 실행 — 브라우저 동의 → refresh_token 출력.
    YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET 환경변수 필요 (데스크톱 OAuth 클라이언트).
    """
    cid = os.environ.get("YOUTUBE_CLIENT_ID")
    csec = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not (cid and csec):
        print("먼저 YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET 환경변수를 설정하세요.")
        print("(Google Cloud Console → 사용자 인증 정보 → OAuth 클라이언트 ID → 데스크톱 앱)")
        return
    import urllib.parse
    import webbrowser

    redirect = "urn:ietf:wg:oauth:2.0:oob"  # OOB (수동 코드 복붙)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": cid,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        })
    )
    print("\n1) 아래 URL 을 브라우저에서 열고 동의하세요:\n")
    print(auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    code = input("\n2) 표시된 인증 코드를 붙여넣으세요: ").strip()
    resp = requests.post(OAUTH_TOKEN_URL, data={
        "client_id": cid, "client_secret": csec, "code": code,
        "redirect_uri": redirect, "grant_type": "authorization_code",
    }, timeout=20)
    if not resp.ok:
        print(f"실패: {resp.text[:300]}")
        return
    rt = resp.json().get("refresh_token")
    print("\n✅ 성공! 아래 refresh_token 을 GitHub Secrets 의 YOUTUBE_REFRESH_TOKEN 에 저장:\n")
    print(rt)
    print("\n+ YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET 도 같이 Secrets 에 저장하세요.")


if __name__ == "__main__":
    if "--auth" in sys.argv:
        _run_auth_flow()
    else:
        print("YouTube Shorts 업로드 모듈. 인증 셋업: python src/post_youtube.py --auth")
        print(f"현재 설정 상태: {'✅ 설정됨' if is_configured() else '❌ 미설정'}")
