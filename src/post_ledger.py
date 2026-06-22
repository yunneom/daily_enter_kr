"""
게시 원장(ledger) — 매트릭스/스피너 게시마다 플랫폼별 ID 매핑을 누적.

[왜 필요한가]
publish_matrix.py 는 게시 결과로 topic_id · ig_media_id · youtube_id · threads_id 를
반환하지만 어디에도 저장하지 않았음 → IG 인사이트(insights.json, media_id 키)와
YouTube 인사이트(insights_youtube.json, video_id 키)를 "같은 콘텐츠"로 조인할
방법이 없었음. 이 원장이 그 조인 키를 제공:

  topic_id ─┬─ ig_media_id   → insights.json (IG reach/shares/saved)
            └─ youtube_id    → insights_youtube.json (YT views/retention) [2주 뒤 #1]

[저장 형식] post_ledger.json
{
  "version": 1,
  "entries": [
    {
      "posted_at": "2026-06-22T09:03:00+09:00",
      "topic_id": "brand_rep_girlgroup",
      "title": "걸그룹 개인 브랜드평판 TOP30",
      "style": "brand_chart",
      "seed": 1234,
      "ig_media_id": "1801...",
      "youtube_id": "abcD",        # 없으면 null
      "threads_id": "1789...",     # 없으면 null
      "bgm": "abc_song.mp3"        # 어떤 음원이 깔렸는지 (abc 송 A/B 추적)
    }
  ]
}

[보존] 최근 120일. 크로스플랫폼 분석/음원 A/B 의 기반.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent
KST = timezone(timedelta(hours=9))
LEDGER_RETENTION_DAYS = 120


def _ledger_path() -> Path:
    """채널별 ledger 경로. LEDGER_PATH 환경변수 또는 기본 post_ledger.json."""
    custom = os.environ.get("LEDGER_PATH")
    if custom:
        return PROJECT_ROOT / custom
    return PROJECT_ROOT / "post_ledger.json"


def load_ledger() -> dict:
    path = _ledger_path()
    if not path.exists():
        return {"version": 1, "entries": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️  post_ledger.json 파싱 실패, 빈 원장으로 시작: {e}")
        return {"version": 1, "entries": []}


def save_ledger(data: dict):
    cutoff = (datetime.now(KST) - timedelta(days=LEDGER_RETENTION_DAYS)).isoformat()
    data["entries"] = [
        e for e in data.get("entries", [])
        if e.get("posted_at", "") >= cutoff
    ]
    _ledger_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_results(results: List[Dict], bgm: Optional[str] = None) -> int:
    """publish_one() 결과 리스트를 원장에 누적. 성공(ok=True)한 게시만 기록.

    Args:
        results: publish_one 반환 dict 리스트.
                 각 항목 키: topic_id, ok, media_id, youtube_id, threads_id, (title/style 는 별도 주입)
        bgm: 이번 실행에 사용된 BGM 파일명 (음원 A/B 추적용).

    Returns: 기록한 엔트리 수.
    """
    data = load_ledger()
    now_iso = datetime.now(KST).isoformat()
    added = 0
    for r in results:
        if not r.get("ok"):
            continue
        if not r.get("media_id"):
            continue  # IG 게시 실패면 조인 키 없음 — 스킵
        entry = {
            "posted_at": now_iso,
            "topic_id": r.get("topic_id"),
            "title": r.get("title", ""),
            "style": r.get("style", ""),
            "seed": r.get("seed"),
            "ig_media_id": r.get("media_id"),
            "youtube_id": r.get("youtube_id"),
            "threads_id": r.get("threads_id"),
            "bgm": r.get("bgm") or bgm,  # 게시별 bgm 우선, 없으면 배치 폴백
        }
        data["entries"].append(entry)
        added += 1
    save_ledger(data)
    return added


def index_by_ig_media(data: dict = None) -> Dict[str, Dict]:
    """ig_media_id → ledger entry 매핑 (인사이트 조인용)."""
    data = data or load_ledger()
    return {e["ig_media_id"]: e for e in data.get("entries", []) if e.get("ig_media_id")}


def index_by_youtube(data: dict = None) -> Dict[str, Dict]:
    """youtube_id → ledger entry 매핑."""
    data = data or load_ledger()
    return {e["youtube_id"]: e for e in data.get("entries", []) if e.get("youtube_id")}


if __name__ == "__main__":
    # 간단 점검 — 현재 원장 요약
    data = load_ledger()
    entries = data.get("entries", [])
    print(f"post_ledger.json — {len(entries)}개 엔트리")
    yt = sum(1 for e in entries if e.get("youtube_id"))
    th = sum(1 for e in entries if e.get("threads_id"))
    print(f"  YouTube 매핑: {yt} · Threads 매핑: {th}")
    by_bgm = {}
    for e in entries:
        by_bgm[e.get("bgm")] = by_bgm.get(e.get("bgm"), 0) + 1
    if by_bgm:
        print("  BGM 분포:")
        for k, v in sorted(by_bgm.items(), key=lambda x: -x[1]):
            print(f"    {k}: {v}건")
