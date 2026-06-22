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
    """YouTube Shorts 제목 + 설명 빌드 — 2026 알고리즘 최적화.

    [2026 YouTube Shorts 베스트 프랙티스]
    - 제목에 #Shorts 필수 (Shorts feed 분류 신호)
    - 제목 키워드 (질문/숫자) 가 클릭률 ↑
    - 설명 첫 3줄이 가장 중요 (검색·관련영상 인덱싱)
    - 해시태그는 3개로 집중 — 분산보다 강한 신호. 18개는 오히려 약함
    - 설명 끝에 #Shorts (영상 분류 보조)
    """
    # 제목: "OO #Shorts" → 좀 더 강한 hook 톤 (질문/도발)
    # 너무 강하면 어색하니 기본은 그대로 + #Shorts
    yt_title = f"{title} #Shorts"[:100]

    # 해시태그: 상위 3개만 prominent, 나머지는 끝에서 검색 매칭용
    primary_3 = [h for h in hashtags if h.startswith("#")][:3]
    extra = [h for h in hashtags if h.startswith("#")][3:12]
    primary_line = " ".join(primary_3) if primary_3 else "#밸런스게임 #카드뉴스"
    extra_line = " ".join(extra)

    desc_lines = [
        # 첫 줄 = 가장 강한 신호. 제목 + 핵심 해시태그 3개 (YouTube 가 가장 우선 인덱싱)
        title,
        primary_line,
        "",
        hint,
        "",
        "👉 매일 새로운 밸런스 시리즈! 구독 + 좋아요로 응원해주세요",
        f"📲 추천템·전체 시리즈: {bio_url}",
        "",
    ]
    if extra_line:
        desc_lines += [extra_line, ""]
    # 끝 라인 = 분류 보조 (#Shorts 필수 + 한글 #쇼츠)
    desc_lines.append("#Shorts #쇼츠 #밸런스게임 #shorts")
    if disclosure:
        desc_lines += ["", f"({disclosure})"]
    return yt_title, "\n".join(desc_lines)


# 카테고리 ID 매핑 — 토픽 성격에 맞게 분류해서 추천 풀을 분산
# Entertainment(24)는 BTS/연예인 압도적 경쟁 → 우리 같은 게임/체크리스트는 22/26이 유리
# 24 = Entertainment   (스피너 픽 등 가벼운 엔터테인먼트)
# 22 = People & Blogs  (직장인편/이상형 등 일상 공감)
# 20 = Gaming          (밸런스게임 — 게이밍 풀 진입)
# 26 = Howto & Style   (체크리스트형 매트릭스)
# 17 = Sports          (축구 국대)
_CATEGORY_MAP = {
    # 스타일별 기본
    "spinner": "20",         # Gaming (밸런스게임 풀)
    "powerpick": "22",       # People & Blogs (일상 공감)
    "spot_difference": "20", # Gaming (찾기 챌린지)
    "soccer_squad": "17",    # Sports
    "drawing": "22",         # People & Blogs
    "emblem": "24",           # Entertainment (아이돌)
    "photo": "26",            # Howto & Style (라이프 추천)
}
# 토픽 ID 별 override (스타일 기본보다 우선)
_CATEGORY_OVERRIDE = {
    "soccer_nationalteam_1000eok": "17",  # Sports
    "spot_diff_bear": "20",                # Gaming
    "child_pick_100man": "22",
    "idealtype_10k": "22",
    "job_pick_10k": "22",
    "travel_30man": "19",                  # Travel & Events
}


def youtube_category_for(topic_id: str, style: str = "") -> str:
    """토픽 → YouTube 카테고리 ID."""
    if topic_id in _CATEGORY_OVERRIDE:
        return _CATEGORY_OVERRIDE[topic_id]
    return _CATEGORY_MAP.get(style or "", "24")


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
        kb = len(video_bytes) // 1024
        print(f"[YouTube 1/1] Shorts 업로드 ({kb}KB · cat={category_id} · {privacy})...")
        print(f"  title: {title[:60]}{'...' if len(title)>60 else ''}")
        resp = requests.post(
            UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=180,
        )
        if not resp.ok:
            print(f"  ❌ YouTube 업로드 실패 HTTP {resp.status_code}: {resp.text[:400]}")
            return None
        vid = resp.json().get("id")
        if vid:
            print(f"  ✅ YouTube Shorts 게시! https://youtube.com/shorts/{vid}")
            # 영상 길이 검증 — 60s 넘으면 Shorts 분류 안 됨
            if kb < 50:
                print(f"  ⚠️  영상 용량 {kb}KB 너무 작음 — 정적 이미지 의심. Shorts retention 저조 가능")
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
