"""
인스타 게시물 인사이트 스냅샷 수집 — 매 워크플로우 실행 후 호출.

각 실행마다 최근 14개 게시물의 like_count, comments_count를 캡쳐.
insights.json에 누적 (시계열). A/B 분석 / 카피 효과 측정의 기반.

[필요 환경변수]
- INSTAGRAM_USER_ID
- INSTAGRAM_ACCESS_TOKEN (instagram_basic 권한 필요. 보통 기본 포함)

[저장 형식]
{
  "version": 1,
  "snapshots": [
    {
      "snapshot_at": "2026-05-24T10:50:00+09:00",
      "posts": [
        {
          "media_id": "180...",
          "permalink": "https://www.instagram.com/p/...",
          "timestamp": "2026-05-24T01:46:00+0000",
          "caption_excerpt": "오늘의 K-연예...",
          "like_count": 50,
          "comments_count": 5,
          "age_hours": 2.5
        }
      ]
    }
  ]
}

스냅샷은 최근 90일치 유지.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests


GRAPH_API_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"
MEDIA_FETCH_LIMIT = 14         # 최근 N개 게시물 조회
SNAPSHOT_RETENTION_DAYS = 90
CAPTION_EXCERPT_CHARS = 80


def _insights_path() -> Path:
    """채널별 insights 파일 경로. INSIGHTS_PATH 환경변수 또는 기본 insights.json."""
    custom = os.environ.get("INSIGHTS_PATH")
    if custom:
        return Path(__file__).parent / custom
    return Path(__file__).parent / "insights.json"


INSIGHTS_PATH = _insights_path()  # 하위 호환 (런타임에 다시 계산은 _insights_path() 사용)

KST = timezone(timedelta(hours=9))


def load_insights() -> dict:
    path = _insights_path()
    if not path.exists():
        return {"version": 1, "snapshots": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️  {path.name} 파싱 실패, 빈 상태로 시작: {e}")
        return {"version": 1, "snapshots": []}


def save_insights(data: dict):
    cutoff = (datetime.now(KST) - timedelta(days=SNAPSHOT_RETENTION_DAYS)).isoformat()
    data["snapshots"] = [s for s in data["snapshots"] if s.get("snapshot_at", "") >= cutoff]
    _insights_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_recent_media(ig_user_id: str, token: str, limit: int = MEDIA_FETCH_LIMIT):
    """최근 N개 미디어 + 기본 메트릭 조회."""
    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    params = {
        "fields": "id,permalink,timestamp,caption,like_count,comments_count,media_type",
        "limit": limit,
        "access_token": token,
    }
    resp = requests.get(url, params=params, timeout=30)
    if not resp.ok:
        print(f"❌ /media 호출 실패: HTTP {resp.status_code}")
        print(f"   응답: {resp.text[:500]}")
        return None
    return resp.json().get("data", [])


def main():
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")

    if not (ig_user_id and token):
        print("⚠️  INSTAGRAM_USER_ID / INSTAGRAM_ACCESS_TOKEN 미설정 → 인사이트 수집 스킵")
        return 0

    media = fetch_recent_media(ig_user_id, token)
    if media is None:
        return 1
    if not media:
        print("⚠️  최근 게시물이 없습니다.")
        return 0

    now = datetime.now(KST)
    snapshot_posts = []
    for m in media:
        ts = m.get("timestamp")  # ISO 8601 with Z or +0000
        age_hours = None
        if ts:
            try:
                posted_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_hours = round((now - posted_at).total_seconds() / 3600, 1)
            except Exception:
                pass

        snapshot_posts.append({
            "media_id": m.get("id"),
            "permalink": m.get("permalink"),
            "timestamp": ts,
            "caption_excerpt": (m.get("caption") or "")[:CAPTION_EXCERPT_CHARS],
            "media_type": m.get("media_type"),
            "like_count": m.get("like_count"),
            "comments_count": m.get("comments_count"),
            "age_hours": age_hours,
        })

    data = load_insights()
    data["snapshots"].append({
        "snapshot_at": now.isoformat(),
        "posts": snapshot_posts,
    })
    save_insights(data)

    print(f"✓ 인사이트 스냅샷 저장 — {len(snapshot_posts)}개 게시물")
    for p in snapshot_posts[:5]:
        likes = p["like_count"] if p["like_count"] is not None else "-"
        comments = p["comments_count"] if p["comments_count"] is not None else "-"
        print(f"  {p['media_id'][-6:]}: ❤{likes} 💬{comments}  ({p['age_hours']}h)  {p['caption_excerpt'][:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
