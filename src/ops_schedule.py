"""운영 스위치 — data/ops_schedule.json 의 회복 모드(일시정지) 판정.

모든 자동 게시 진입점(main.py 뉴스 / publish_matrix / engagement_daily)이
게시 전에 pause_active() 를 확인한다. 워크플로우는 정상 종료(exit 0)하므로
실패 알림이 뜨지 않는다.
"""
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
PATH = ROOT / "data" / "ops_schedule.json"
KST = timezone(timedelta(hours=9))


def pause_active(today: date = None):
    """(일시정지 여부, 사유). OPS_IGNORE_PAUSE=1 이면 항상 False."""
    if os.environ.get("OPS_IGNORE_PAUSE") == "1":
        return False, ""
    try:
        cfg = json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return False, ""
    until = cfg.get("pause_until")
    if not until:
        return False, ""
    today = today or datetime.now(KST).date()
    try:
        if today <= date.fromisoformat(until):
            return True, f"회복 모드 (pause_until {until}) — {cfg.get('reason', '')}"
    except ValueError:
        return False, ""
    return False, ""


def guard(label: str) -> bool:
    """일시정지면 안내 출력 후 True. 호출자는 True 면 게시를 건너뛰고 0 반환."""
    active, reason = pause_active()
    if active:
        print(f"⏸️ [{label}] 자동 게시 건너뜀 — {reason}")
    return active
