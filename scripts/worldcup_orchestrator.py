"""
월드컵 캠페인 오케스트레이터 — 캠페인 일정 dict 매칭 + 액션 실행.

[배경]
GitHub Actions cron 매 30분 트리거. 현재 KST 시각이 SCHEDULE 의 어떤 슬롯과 매칭하면
해당 action(publish/tally) 을 실행. 캠페인 시간 외엔 silent skip.

[일정] 한국기업평판연구소 2026.6.21 TOP100 + Reels 알고리즘 추천 슬롯 기준
  화 12:00 32강 게시 → 수 12:00 32강 집계
  수 21:00 16강 게시 → 목 21:00 16강 집계
  목 14:30 8강 게시  → 금 14:30 8강 집계
  금 14:00 4강 게시  → 토 14:00 4강 집계
  토 13:00 결승+3위전 게시 → 일 13:00 집계
  일 13:30 우승 발표

[실행]
- cron: */30 * * * *  (매 30분 트리거)
- 캠페인 시간 외엔 skip
- manual dispatch 로 ACTION/ROUND 강제 실행 가능
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
KST = timezone(timedelta(hours=9))
TOLERANCE_MIN = 25  # cron 매 30분이라 ±25분 안에 매칭하면 1번만 실행

# (KST datetime, action, round)
SCHEDULE = [
    # === Day 1 (화 6/23) — 32강 게시 ===
    (datetime(2026, 6, 23, 12,  0, tzinfo=KST), "publish",      "R32"),
    # === Day 2 (수 6/24) ===
    (datetime(2026, 6, 24, 12,  0, tzinfo=KST), "tally",        "R32"),
    (datetime(2026, 6, 24, 12, 30, tzinfo=KST), "announce",     "R32"),  # 16강 진출자 발표
    (datetime(2026, 6, 24, 21,  0, tzinfo=KST), "publish",      "R16"),
    # === Day 3 (목 6/25) ===
    (datetime(2026, 6, 25, 21,  0, tzinfo=KST), "tally",        "R16"),
    (datetime(2026, 6, 25, 22,  0, tzinfo=KST), "announce",     "R16"),  # 8강 진출자
    # === Day 4 (금 6/26) ===
    (datetime(2026, 6, 26, 14,  0, tzinfo=KST), "publish",      "R8"),
    # === Day 5 (토 6/27) ===
    (datetime(2026, 6, 27, 14,  0, tzinfo=KST), "tally",        "R8"),
    (datetime(2026, 6, 27, 14, 30, tzinfo=KST), "announce",     "R8"),   # 4강 진출
    (datetime(2026, 6, 27, 15,  0, tzinfo=KST), "publish",      "R4"),   # 4강 1 게시(콤비)
    # === Day 6 (일 6/28) ===
    (datetime(2026, 6, 28, 15,  0, tzinfo=KST), "tally",        "R4"),
    (datetime(2026, 6, 28, 15, 30, tzinfo=KST), "announce",     "R4"),   # 결승+3위전 라인업
    (datetime(2026, 6, 28, 16,  0, tzinfo=KST), "publish",      "R2"),   # 결승+3위전 1 게시
    # === Day 7 (월 6/29) ===
    (datetime(2026, 6, 29, 16,  0, tzinfo=KST), "tally",        "R2"),
    (datetime(2026, 6, 29, 16, 30, tzinfo=KST), "announce",     "R1"),   # 🏆 우승+1·2·3위 발표
]


def now_kst() -> datetime:
    return datetime.now(KST)


def find_slot(now: datetime):
    """현재 시각 ±TOLERANCE 안의 SCHEDULE 슬롯 찾기. 없으면 None."""
    best = None
    best_delta = TOLERANCE_MIN * 60 + 1
    for sched, action, rnd in SCHEDULE:
        delta = abs((now - sched).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best = (sched, action, rnd)
    if best and best_delta <= TOLERANCE_MIN * 60:
        return best
    return None


def already_done(action: str, round_key: str) -> bool:
    """idempotency — 이미 같은 round/action 실행했는지 체크.
    publish: post_ledger 에 해당 round 의 worldcup topic_id 가 N개 이상 있으면 done.
    tally: bracket json 의 해당 round.matches 의 winner 가 모두 채워졌으면 done.
    """
    bracket_path = ROOT / "data" / "worldcup_bracket.json"
    if not bracket_path.exists():
        return False
    bracket = json.loads(bracket_path.read_text(encoding="utf-8"))
    rnd = bracket.get("rounds", {}).get(round_key, {})
    if action == "publish":
        # ledger 체크
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        prefix = f"worldcup_{round_key.lower()}_"
        n_target = len(rnd.get("posts", []))
        n_have = sum(1 for e in ledger.get("entries", [])
                     if (e.get("topic_id") or "").startswith(prefix))
        return n_have >= n_target and n_target > 0
    elif action == "tally":
        matches = rnd.get("matches", [])
        if not matches:
            return False
        return all(m.get("winner") for m in matches)
    return False


def run(cmd: list) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def execute(action: str, round_key: str) -> int:
    if action == "publish":
        rc = run([sys.executable, "scripts/build_worldcup_round.py", round_key])
        if rc != 0:
            print(f"❌ build {round_key} 실패 (rc={rc})")
            return rc
        rc = run([sys.executable, "scripts/worldcup_publish.py", round_key])
        if rc != 0:
            print(f"❌ publish {round_key} 실패 (rc={rc})")
            return rc
        return 0
    elif action == "tally":
        return run([sys.executable, "scripts/worldcup_tally.py", round_key])
    elif action == "announce":
        # 라운드 진출자 결과 발표 카드 게시
        return run([sys.executable, "scripts/worldcup_announce.py", round_key])
    else:
        print(f"❌ 알 수 없는 action: {action}")
        return 1


def main():
    # manual dispatch (env로 강제)
    forced_action = os.environ.get("WORLDCUP_ACTION")
    forced_round = os.environ.get("WORLDCUP_ROUND")
    if forced_action and forced_round:
        print(f"🔧 manual dispatch: {forced_action} {forced_round}")
        return execute(forced_action, forced_round)

    now = now_kst()
    print(f"⏰ now KST: {now.isoformat()}")

    # 캠페인 윈도우 외엔 skip
    if not (datetime(2026, 6, 23, tzinfo=KST) <= now <
            datetime(2026, 6, 30, tzinfo=KST)):
        print("⏭️  캠페인 윈도우(6/23-29) 외 — skip")
        return 0

    slot = find_slot(now)
    if not slot:
        print(f"⏭️  ±{TOLERANCE_MIN}분 안 일정 슬롯 없음 — skip")
        return 0

    sched, action, rnd = slot
    print(f"🎯 슬롯 매칭: {sched.isoformat()} → {action} {rnd}")

    if already_done(action, rnd):
        print(f"✅ {action} {rnd} 이미 완료 — idempotent skip")
        return 0

    return execute(action, rnd)


if __name__ == "__main__":
    sys.exit(main())
