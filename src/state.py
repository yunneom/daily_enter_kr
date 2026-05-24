"""
운영 state 관리 — 중복 게시 방지, 실행 이력 추적.

state.json 구조 (프로젝트 루트에 저장, git에 커밋):
{
  "version": 1,
  "last_run_at": "2026-05-24T08:00:00+09:00",
  "last_run_status": "success" | "failed" | "skipped",
  "posted_history": [
    {"date": "2026-05-24", "title_hash": "abc123...", "card_title": "..."},
    ...
  ]
}

posted_history는 최근 30일치만 유지 (그 이상은 자동 prune).
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

STATE_PATH = Path(__file__).parent.parent / "state.json"
HISTORY_RETENTION_DAYS = 30
DEDUP_WINDOW_DAYS = 14   # 14일 안에 게시한 제목과 중복되면 스킵

KST = timezone(timedelta(hours=9))


def title_hash(title: str) -> str:
    """제목을 정규화 + 해시 (RSS의 미세한 차이는 무시)."""
    normalized = "".join(title.split()).lower()  # 공백/대소문자 정규화
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"version": 1, "last_run_at": None, "last_run_status": None, "posted_history": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️  state.json 파싱 실패, 빈 state로 시작: {e}")
        return {"version": 1, "last_run_at": None, "last_run_status": None, "posted_history": []}


def save_state(state: dict):
    # 30일 이상 된 history 자동 prune
    cutoff = (datetime.now(KST) - timedelta(days=HISTORY_RETENTION_DAYS)).date().isoformat()
    state["posted_history"] = [h for h in state["posted_history"] if h.get("date", "") >= cutoff]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_recent_hashes(state: dict, window_days: int = DEDUP_WINDOW_DAYS) -> set:
    """최근 window_days 안에 게시된 제목 해시 집합."""
    cutoff = (datetime.now(KST) - timedelta(days=window_days)).date().isoformat()
    return {
        h.get("title_hash") for h in state.get("posted_history", [])
        if h.get("date", "") >= cutoff and h.get("title_hash")
    }


def filter_duplicates(news_items, state: dict):
    """이미 최근에 게시된 뉴스 제거."""
    recent = get_recent_hashes(state)
    fresh, dupes = [], []
    for n in news_items:
        if title_hash(n.title) in recent:
            dupes.append(n)
        else:
            fresh.append(n)
    return fresh, dupes


def record_post(state: dict, card_titles_with_originals: List[tuple], status: str = "success"):
    """게시 성공 시 호출. (original_title, card_title) tuple 리스트를 받음."""
    today = datetime.now(KST).date().isoformat()
    for original, card in card_titles_with_originals:
        state["posted_history"].append({
            "date": today,
            "title_hash": title_hash(original),
            "card_title": card,
        })
    state["last_run_at"] = datetime.now(KST).isoformat()
    state["last_run_status"] = status


def record_run(state: dict, status: str):
    """게시 안 한 실행 (skip / 실패)도 기록."""
    state["last_run_at"] = datetime.now(KST).isoformat()
    state["last_run_status"] = status
