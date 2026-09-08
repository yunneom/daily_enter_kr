"""GitHub Actions cron 지연 보정 — 목표 시각(UTC)까지 대기.

이 저장소의 schedule 트리거는 예정보다 2~7시간 늦게 시작된다(실측 2026-08~09:
cron 04:00 → 08:42~10:18 시작, cron 09:00 → 13:52~16:38 시작). 그래서 cron 을
목표보다 5~6시간 앞당겨 걸고, 잡이 일찍 시작되면 여기서 목표 시각까지 잔다.
목표를 이미 지났으면 즉시 반환(늦게라도 게시). 저장소가 public 이라 Actions 분은 무료.

사용: python scripts/wait_until.py 09:00 --max-minutes 330
"""
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="UTC HH:MM")
    ap.add_argument("--max-minutes", type=int, default=300, help="이보다 오래 기다려야 하면 대기 안 함")
    a = ap.parse_args()
    hh, mm = (int(x) for x in a.target.split(":"))
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        print(f"⏱ 목표 {a.target} UTC 이미 지남 (지금 {now:%H:%M}) — 즉시 진행")
        return 0
    wait = (target - now).total_seconds()
    if wait > a.max_minutes * 60:
        print(f"⏱ 대기 {wait/60:.0f}분 > 상한 {a.max_minutes}분 — 즉시 진행")
        return 0
    print(f"⏱ {a.target} UTC(KST {(target + timedelta(hours=9)):%H:%M})까지 {wait/60:.0f}분 대기")
    sys.stdout.flush()
    time.sleep(wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
