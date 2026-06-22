"""
인스타 게시물 인사이트 스냅샷 수집 — 매 워크플로우 실행 후 호출.

각 실행마다 최근 14개 게시물의 like_count, comments_count를 캡쳐.
insights.json에 누적 (시계열). A/B 분석 / 카피 효과 측정의 기반.

[필요 환경변수]
- INSTAGRAM_USER_ID
- INSTAGRAM_ACCESS_TOKEN (instagram_basic 권한 필요. 보통 기본 포함)

[저장 형식]
{
  "version": 2,
  "snapshots": [
    {
      "snapshot_at": "2026-05-24T10:50:00+09:00",
      "posts": [
        {
          "media_id": "180...",
          "permalink": "https://www.instagram.com/p/...",
          "media_type": "VIDEO" | "CAROUSEL_ALBUM" | "IMAGE",
          "caption_excerpt": "...",
          "like_count": 50, "comments_count": 5,
          // Reels 전용 (media_type=VIDEO 일 때만 — v2 부터 추가)
          "plays": 124, "reach": 98, "saved": 3, "shares": 7,
          "total_interactions": 65,
          "age_hours": 2.5
        }
      ]
    }
  ]
}

[버전 2 (2026-06-05)] Reels 전환 후 plays/reach/saved/shares 등 reels insights 메트릭 추가.
shares 는 알고리즘 신호 중 상위. saved 도 retention 강한 신호. 시계열로 누적 분석 가능.

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


# Reels (media_type=VIDEO) 만 대상으로 하는 추가 메트릭.
# 캐러셀/이미지는 다른 메트릭 셋이라 별도 처리 — 우리는 Reels-only 운영이라 VIDEO 만 다룸.
REELS_INSIGHT_METRICS = ["plays", "reach", "saved", "shares", "total_interactions"]


# ─── 계정 단위 인사이트 (abc 송 퍼널 프록시) ───
# [정직한 한계] IG Graph API 는 "오디오 페이지 클릭 수"를 노출하지 않음.
# 따라서 abc 송이 트래픽을 만드는지는 다음 계정 단위 신호로 간접 측정:
#   profile_views  — 음원/게시물 → 프로필 방문 (오디오 라벨 탭의 주 도착지)
#   website_clicks — 프로필 bio 링크(=YT) 클릭. 퍼널의 최종 도착
#   reach          — 전체 도달 (분모)
#   accounts_engaged / follower_count — 보조
# 이 일별 추세를 abc 송 도입 전/후로 비교하면 음원 효과를 근사할 수 있음.
ACCOUNT_METRICS_TOTAL = ["reach", "profile_views", "website_clicks",
                         "accounts_engaged"]
ACCOUNT_METRICS_PLAIN = ["follower_count"]


def fetch_account_insights(ig_user_id: str, token: str) -> dict:
    """계정 단위 일별 인사이트. 메트릭별 grace — 일부 막혀도 나머지 수집.

    2025+ Graph API 변경으로 일부 메트릭은 metric_type=total_value 필요.
    두 호출 형태(total_value / plain)로 나눠 시도하고, 실패한 메트릭은 조용히 스킵.
    """
    out = {}
    base = f"{GRAPH_BASE}/{ig_user_id}/insights"

    # 1) total_value 형식 (reach/profile_views/website_clicks/accounts_engaged)
    try:
        resp = requests.get(base, params={
            "metric": ",".join(ACCOUNT_METRICS_TOTAL),
            "metric_type": "total_value",
            "period": "day",
            "access_token": token,
        }, timeout=20)
        if resp.ok:
            for item in resp.json().get("data", []):
                name = item.get("name")
                tv = item.get("total_value") or {}
                if name and "value" in tv:
                    out[name] = tv["value"]
    except Exception:
        pass

    # 2) plain 형식 (follower_count — values 배열)
    try:
        resp = requests.get(base, params={
            "metric": ",".join(ACCOUNT_METRICS_PLAIN),
            "period": "day",
            "access_token": token,
        }, timeout=20)
        if resp.ok:
            for item in resp.json().get("data", []):
                name = item.get("name")
                vals = item.get("values", [])
                if name and vals:
                    out[name] = vals[-1].get("value")
    except Exception:
        pass

    return out


def fetch_reels_insights(media_id: str, token: str) -> dict:
    """단일 Reels 의 plays/reach/saved/shares 등 인사이트.
    실패해도 빈 dict 반환 — 일부 메트릭만 막혀있는 경우도 있어서 게시별 grace.
    """
    url = f"{GRAPH_BASE}/{media_id}/insights"
    params = {"metric": ",".join(REELS_INSIGHT_METRICS), "access_token": token}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if not resp.ok:
            return {}
        data = resp.json().get("data", [])
        out = {}
        for item in data:
            name = item.get("name")
            vals = item.get("values", [])
            if name and vals:
                out[name] = vals[0].get("value")
        return out
    except Exception:
        return {}


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

        post_data = {
            "media_id": m.get("id"),
            "permalink": m.get("permalink"),
            "timestamp": ts,
            "caption_excerpt": (m.get("caption") or "")[:CAPTION_EXCERPT_CHARS],
            "media_type": m.get("media_type"),
            "like_count": m.get("like_count"),
            "comments_count": m.get("comments_count"),
            "age_hours": age_hours,
        }

        # Reels 만 추가 인사이트 호출. 캐러셀/이미지는 metric 셋이 달라 skip (Reels-only 운영).
        if m.get("media_type") == "VIDEO":
            reels_insights = fetch_reels_insights(m["id"], token)
            post_data.update(reels_insights)  # plays/reach/saved/shares/total_interactions

        snapshot_posts.append(post_data)

    # 계정 단위 인사이트 (abc 송 퍼널 프록시 — profile_views/website_clicks 등)
    account = fetch_account_insights(ig_user_id, token)

    data = load_insights()
    # 버전 마이그레이션: v2 → v3 (계정 단위 인사이트 추가). 기존 스냅샷은 그대로 둠.
    data["version"] = 3
    data["snapshots"].append({
        "snapshot_at": now.isoformat(),
        "account": account,
        "posts": snapshot_posts,
    })
    save_insights(data)

    if account:
        print(f"✓ 계정 인사이트 — 👤프로필조회 {account.get('profile_views','-')} "
              f"🔗bio클릭 {account.get('website_clicks','-')} "
              f"📡reach {account.get('reach','-')} "
              f"팔로워 {account.get('follower_count','-')}")
    else:
        print("⚠️  계정 인사이트 비어있음 (권한/메트릭 변경 가능 — 게시별 인사이트는 정상)")
    print(f"✓ 인사이트 스냅샷 저장 — {len(snapshot_posts)}개 게시물")
    for p in snapshot_posts[:5]:
        likes = p["like_count"] if p["like_count"] is not None else "-"
        comments = p["comments_count"] if p["comments_count"] is not None else "-"
        # Reels 가 있으면 reach/shares 까지 표기 (알고리즘 핵심 신호)
        extras = ""
        if "plays" in p:
            extras = f" ▶{p.get('plays', '-')} 👤{p.get('reach', '-')} 🔖{p.get('saved', '-')} 🔁{p.get('shares', '-')}"
        print(f"  {p['media_id'][-6:]}: ❤{likes} 💬{comments}{extras}  ({p['age_hours']}h)  {p['caption_excerpt'][:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
