"""
Threads 자동 게시 (Meta Graph API, 2024년 말 출시).

[흐름]
1. POST /{threads-user-id}/threads (media_type=TEXT, text=...)
2. (옵션) 이미지 첨부 시 media_type=IMAGE_URL + image_url=...
3. publish: POST /{threads-user-id}/threads_publish (creation_id)

[제약]
- 250 posts/24h per Threads profile
- 텍스트 최대 500자
- 이미지/링크 포함 가능
- 비디오 게시는 v2 API에서 지원 (별도 처리)

[환경변수]
- THREADS_USER_ID
- THREADS_ACCESS_TOKEN (Threads 별도 토큰. Meta 앱의 'Threads API' 권한 필요)

미설정 시 silently False 반환.
"""

import os
import time
from typing import Optional, List
import requests


THREADS_API_VERSION = "v1.0"
THREADS_API_BASE = f"https://graph.threads.net/{THREADS_API_VERSION}"


def is_configured() -> bool:
    return bool(os.environ.get("THREADS_USER_ID") and os.environ.get("THREADS_ACCESS_TOKEN"))


def _create_text_container(user_id: str, token: str, text: str,
                           image_url: Optional[str] = None) -> Optional[str]:
    url = f"{THREADS_API_BASE}/{user_id}/threads"
    params = {
        "media_type": "IMAGE" if image_url else "TEXT",
        "text": text[:495],
        "access_token": token,
    }
    if image_url:
        params["image_url"] = image_url
    resp = requests.post(url, params=params, timeout=20)
    if not resp.ok:
        print(f"  ❌ Threads create_container 실패 HTTP {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json().get("id")


def _wait_container_ready(container_id: str, token: str, timeout: int = 30) -> bool:
    """Threads 컨테이너는 보통 빠르게 준비됨 (텍스트 위주)."""
    url = f"{THREADS_API_BASE}/{container_id}"
    elapsed = 0
    while elapsed < timeout:
        resp = requests.get(url, params={"fields": "status,error_message",
                                         "access_token": token}, timeout=10)
        if resp.ok:
            data = resp.json()
            if data.get("status") == "FINISHED":
                return True
            if data.get("status") == "ERROR":
                print(f"  ❌ Threads container ERROR: {data.get('error_message', '?')}")
                return False
        time.sleep(2)
        elapsed += 2
    return False


def _publish_container(user_id: str, token: str, container_id: str) -> Optional[str]:
    url = f"{THREADS_API_BASE}/{user_id}/threads_publish"
    resp = requests.post(url, params={"creation_id": container_id, "access_token": token}, timeout=20)
    if not resp.ok:
        print(f"  ❌ Threads publish 실패 HTTP {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json().get("id")


def build_thread_text(top_titles: List[str], date_str: str,
                      label_short: str = "K-연예",
                      reel_link: Optional[str] = None) -> str:
    """Threads 용 텍스트 — IG 캡션 대비 짧고 토픽태그(#) 가능."""
    n_show = min(5, len(top_titles))
    head = top_titles[:n_show]
    lines = [
        f"📰 오늘의 {label_short} 핫이슈 — {date_str}",
        "",
    ]
    for i, t in enumerate(head, 1):
        lines.append(f"{i}. {t}")
    lines.append("")
    if reel_link:
        lines.append(f"전체 영상: {reel_link}")
        lines.append("")
    # Threads 는 hashtag 보단 topic tag 식으로 1-3개만
    lines.append("#케이팝 #연예뉴스 #릴스")
    text = "\n".join(lines)
    if len(text) > 495:
        # 일부 항목 줄여서 다시
        lines = lines[:2] + lines[2:2+3] + ["", "전체는 IG @daily_enter_kr", "", "#케이팝"]
        text = "\n".join(lines)
    return text


def post_thread(top_titles: List[str], date_str: str,
                label_short: str = "K-연예",
                reel_link: Optional[str] = None) -> Optional[str]:
    """Threads 에 게시. 미설정/실패 시 None 반환 (silent)."""
    if not is_configured():
        print("⏭️  Threads 미설정 (THREADS_USER_ID/ACCESS_TOKEN) — 스킵")
        return None
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]

    text = build_thread_text(top_titles, date_str, label_short, reel_link)
    print(f"[Threads 1/3] 컨테이너 생성 ({len(text)}자)...")
    cid = _create_text_container(user_id, token, text)
    if not cid:
        return None

    print(f"  ✓ container_id: {cid}")
    print("[Threads 2/3] 준비 대기...")
    if not _wait_container_ready(cid, token):
        return None

    print("[Threads 3/3] 게시...")
    media_id = _publish_container(user_id, token, cid)
    if media_id:
        print(f"  ✅ Threads 게시 완료! Media ID: {media_id}")
    return media_id


if __name__ == "__main__":
    sample = ["아이브 새 앨범 티저 공개", "박찬욱 신작 칸영화제 출품",
              "지드래곤 월드투어 8개 도시 추가"]
    print(build_thread_text(sample, "2026-06-05", reel_link="https://www.instagram.com/reel/sample"))
