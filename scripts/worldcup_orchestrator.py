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
TOLERANCE_MIN = 60  # cron 매 30분 + 정시 부하 지연(실측 47분) 흡수. find_slot 은
                    # 최단 거리 슬롯만 반환하므로 30분 간격 인접 슬롯과도 안전 매칭.

# (KST datetime, action, round)
# [일정 연장 — 도달 누적 우선] 첫 라운드 노출이 약해서 앞 라운드에 48~63h 몰아주고
# 빅매치(16강)·클라이맥스(결승)를 주말에 배치. 뒤 라운드는 24h (모멘텀 구축 후).
SCHEDULE = [
    # === Day 1 (화 6/23) — 32강 게시 (완료) ===
    (datetime(2026, 6, 23, 12,  0, tzinfo=KST), "publish",  "R32"),
    # === Day 2 (수 6/24) 07:00 — 32강 대진표 홍보 (한 장, 양사이드) ===
    # 사용자 결정: 6/24는 월드컵 홍보 게시글만. 7시 = 출근/등교 시간대 노출.
    (datetime(2026, 6, 24,  7,  0, tzinfo=KST), "bracket",  ""),
    # === Day 5 (토 6/27) 07:00 — 16강 단독 대진표 홍보 (아침 출근 슬롯) ===
    # v4: WIN 배지 제거 + 4강 헤더 + 결승 선 단순화. current_round=R16.
    (datetime(2026, 6, 27,  7,  0, tzinfo=KST), "bracket",  ""),
    # === Day 5 (토 6/27) 02:30 — 16강 홍보 블라스트 (missed) ===
    # (datetime(2026, 6, 27,  2, 30, tzinfo=KST), "promo_blast", ""),  # 코드 푸시 전 슬롯
    # === Day 7 (월 6/29) 09:15 — 16강 홍보 블라스트 1차 재시도 (cron 드롭) ===
    # (datetime(2026, 6, 29,  9, 15, tzinfo=KST), "promo_blast", ""),  # cron 2h 드롭으로 미발화
    # === Day 7 (월 6/29) 11:30 — 16강 홍보 블라스트 최종 즉시 실행 ===
    (datetime(2026, 6, 29, 11, 30, tzinfo=KST), "promo_blast", ""),
    # === Day 7 (월 6/29) 12:30 — HF 릴스 재시도 (playwright 수정 후) ===
    (datetime(2026, 6, 29, 12, 30, tzinfo=KST), "hf_blast",   ""),
    # === Day 7 (월 6/29) 13:25 — R16 집계·발표 + R8 빌드·게시 즉시 체인 ===
    (datetime(2026, 6, 29, 13, 25, tzinfo=KST), "chain_r16_r8", ""),
    # === Day 7 (월 6/29) 14:00 — R8 HF 대진표 릴스 (Playwright 수정 후 재시도) ===
    (datetime(2026, 6, 29, 14,  0, tzinfo=KST), "hf_r8", ""),
    # === Day 3 (목 6/25) — 32강 집계 (48h) + 16강 진출 발표 ===
    (datetime(2026, 6, 25, 12,  0, tzinfo=KST), "tally",    "R32"),
    (datetime(2026, 6, 25, 12, 30, tzinfo=KST), "announce", "R32"),
    # === Day 4 (금 6/26) 12:00 — 16강 게시 (점심 슬롯, 투표창 72h 주말 전체) ===
    (datetime(2026, 6, 26, 12,  0, tzinfo=KST), "publish",  "R16"),
    # === Day 7 (월 6/29) — 16강 집계 (주말 63h) 오후 5시 + 발표 + 오후 6시 8강 게시 ===
    (datetime(2026, 6, 29, 17,  0, tzinfo=KST), "tally",    "R16"),
    (datetime(2026, 6, 29, 17, 30, tzinfo=KST), "announce", "R16"),
    (datetime(2026, 6, 29, 18,  0, tzinfo=KST), "publish",  "R8"),
    # === Day 8 (화 6/30) — 8강 집계 (24h) + 4강 진출 발표 ===
    (datetime(2026, 6, 30, 21,  0, tzinfo=KST), "tally",    "R8"),
    (datetime(2026, 6, 30, 21, 30, tzinfo=KST), "announce", "R8"),
    # === Day 9 (수 7/1) 21:00 — 4강 게시 ===
    (datetime(2026, 7,  1, 21,  0, tzinfo=KST), "publish",  "R4"),
    # === Day 10 (목 7/2) — 4강 집계 (24h) + 결승 라인업 발표 ===
    (datetime(2026, 7,  2, 21,  0, tzinfo=KST), "tally",    "R4"),
    (datetime(2026, 7,  2, 21, 30, tzinfo=KST), "announce", "R4"),
    # === Day 11 (금 7/3) 21:00 — 결승+3·4위전 게시 (주말 관통) ===
    (datetime(2026, 7,  3, 21,  0, tzinfo=KST), "publish",  "R2"),
    # === Day 13 (일 7/5) — 결승 집계 (주말 39h) + 🏆 우승 발표 ===
    (datetime(2026, 7,  5, 12,  0, tzinfo=KST), "tally",    "R2"),
    (datetime(2026, 7,  5, 12, 30, tzinfo=KST), "announce", "R1"),
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
    elif action == "announce":
        # ledger 에 worldcup_announce_{round} 기록이 있으면 done — 중복 발표 방지.
        # (cron 40분 윈도우에 announce 슬롯이 두 번 매칭될 수 있어 필수)
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        tid = f"worldcup_announce_{round_key.lower()}"
        return any((e.get("topic_id") or "") == tid
                   for e in ledger.get("entries", []))
    elif action == "bracket":
        # ledger 에 worldcup_bracket 기록 있으면 done — 중복 게시 방지.
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        # 라운드별 분리 — current_round 의 대진표가 게시됐는지만 체크
        cur = bracket.get("current_round", "R32").lower()
        target_tid = f"worldcup_bracket_{cur}"
        return any((e.get("topic_id") or "") == target_tid
                   for e in ledger.get("entries", []))
    elif action == "promo_blast":
        # ledger 에 캐러셀 기록 있으면 done (1번만 실행)
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        cur = bracket.get("current_round", "R16").lower()
        return any((e.get("topic_id") or "") == f"worldcup_promo_{cur}_carousel"
                   for e in ledger.get("entries", []))
    elif action == "hf_blast":
        # HF 릴스 기록 있으면 done
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        cur = bracket.get("current_round", "R16").lower()
        return any((e.get("topic_id") or "") == f"worldcup_promo_{cur}_hf_reels"
                   for e in ledger.get("entries", []))
    elif action == "chain_r16_r8":
        # R8 posts 가 ledger 에 있으면 완료
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return any((e.get("topic_id") or "").startswith("worldcup_r8_")
                   for e in ledger.get("entries", []))
    elif action == "hf_r8":
        # R8 HF 대진표 릴스가 ledger 에 있으면 완료
        ledger_path = ROOT / "post_ledger.json"
        if not ledger_path.exists():
            return False
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return any((e.get("topic_id") or "") == "worldcup_hf_r8_bracket"
                   for e in ledger.get("entries", []))
    return False


def _round_has_winners(round_key: str) -> bool:
    """라운드 매치 winner 가 모두 채워졌는지 (announce 선행 tally 판단용)."""
    bp = ROOT / "data" / "worldcup_bracket.json"
    if not bp.exists():
        return False
    try:
        b = json.loads(bp.read_text(encoding="utf-8"))
    except Exception:
        return False
    matches = b.get("rounds", {}).get(round_key, {}).get("matches", [])
    return bool(matches) and all(m.get("winner") for m in matches)


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
        # 자가복구: cron 지연으로 tally 슬롯을 놓치고 announce 만 잡힌 경우,
        # winner 가 비어있으면 announce 전에 tally 를 먼저 실행 (R1 은 R2 winner 기준이라 예외).
        if round_key not in ("R1",) and not _round_has_winners(round_key):
            print(f"⚠️  {round_key} winner 미정 — announce 전에 tally 먼저 실행")
            rc = run([sys.executable, "scripts/worldcup_tally.py", round_key])
            if rc != 0:
                print(f"❌ 선행 tally {round_key} 실패 (rc={rc})")
                return rc
        # 라운드 진출자 결과 발표 카드 게시
        return run([sys.executable, "scripts/worldcup_announce.py", round_key])
    elif action == "bracket":
        # 32강 대진표 캐러셀 게시 (manual dispatch 전용 — SCHEDULE 에 없음)
        return run([sys.executable, "scripts/worldcup_post_bracket.py"])
    elif action == "promo_blast":
        # 16강 홍보 블라스트: 캐러셀 + 티저 + 조별 릴스 + HF 릴스
        extra = ["--skip", round_key] if round_key else []
        return run([sys.executable, "scripts/worldcup_promo_blast.py"] + extra)
    elif action == "hf_blast":
        # HF 릴스만 재실행 (파트 1·2·3 스킵)
        return run([sys.executable, "scripts/worldcup_promo_blast.py",
                    "--skip", "1", "2", "3"])
    elif action == "chain_r16_r8":
        # R16 집계·발표 → R8 빌드·게시 전체 체인
        return run([sys.executable, "scripts/worldcup_chain.py", "R16", "R8"])
    elif action == "hf_r8":
        # R8 HF 대진표 릴스 단독 게시
        return run([sys.executable, "scripts/worldcup_post_hf_reel.py", "R8"])
    elif action == "render_test":
        # 16강 미리보기 렌더 (게시 X — 아티팩트로 실사 사진 컨펌). manual 전용.
        return run([sys.executable, "scripts/worldcup_preview_r16.py"])
    else:
        print(f"❌ 알 수 없는 action: {action}")
        return 1


def main():
    # manual dispatch (env로 강제)
    forced_action = os.environ.get("WORLDCUP_ACTION", "").strip()
    forced_round = os.environ.get("WORLDCUP_ROUND", "").strip()
    # workflow_dispatch event 면 GITHUB_EVENT_NAME=workflow_dispatch.
    # input 비어있는 dispatch (사용자가 입력란 안 채움) = 의도 불명 → 명확한 에러.
    is_dispatch = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    if is_dispatch and not forced_action:
        print("❌ workflow_dispatch 인데 action 입력란이 비어있음.")
        print("   유효 값: publish | tally | announce | bracket")
        print("   다시 Run workflow → action 입력란에 정확히 타이핑 필요.")
        return 1
    # bracket / promo_blast / render_test / chain_r16_r8 / hf_r8 는 round 불필요
    if forced_action in ("bracket", "promo_blast", "render_test", "chain_r16_r8", "hf_r8"):
        print(f"🔧 manual dispatch: {forced_action}")
        return execute(forced_action, "")
    if forced_action and forced_round:
        print(f"🔧 manual dispatch: {forced_action} {forced_round}")
        return execute(forced_action, forced_round)
    if is_dispatch and forced_action and not forced_round:
        print(f"❌ workflow_dispatch action={forced_action!r} 인데 round 비어있음.")
        print("   bracket/promo_blast/render_test 외 액션은 round 필수 (R32 | R16 | R8 | R4 | R2 | R1).")
        return 1

    now = now_kst()
    print(f"⏰ now KST: {now.isoformat()}")

    # 캠페인 윈도우 외엔 skip (연장: 6/23 ~ 7/5 우승 발표)
    if not (datetime(2026, 6, 23, tzinfo=KST) <= now <
            datetime(2026, 7, 6, tzinfo=KST)):
        print("⏭️  캠페인 윈도우(6/23 ~ 7/5) 외 — skip")
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

    rc = execute(action, rnd)
    if rc != 0:
        print(f"⚠️  execute 실패 rc={rc} — 즉시 1회 재시도")
        rc = execute(action, rnd)

    # 게시 완료 검증 (ledger 기록 확인)
    import time as _time
    _time.sleep(10)
    if already_done(action, rnd):
        print(f"✅ {action} {rnd} 검증 완료 — ledger 기록 확인됨")
    else:
        print(f"⚠️  {action} {rnd} 검증 실패 — ledger 미기록. rc={rc}")
        # rc=0 이어도 실제 게시 안됐으면 한 번 더
        if rc == 0:
            print("↩️  rc=0 이지만 ledger 미기록 — 마지막 재시도")
            rc = execute(action, rnd)
    return rc


if __name__ == "__main__":
    sys.exit(main())
