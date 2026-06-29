"""
월드컵 라운드 전환 체인 — 한 번의 워크플로우 실행으로 전체 처리.

R16 집계 → R16 발표 → R8 빌드 → R8 게시 (HF 릴스 포함)

[사용]
python scripts/worldcup_chain.py R16 R8
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: list) -> int:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        print(f"❌ 실패 rc={rc}")
    return rc


def main():
    if len(sys.argv) < 3:
        print("usage: worldcup_chain.py <from_round> <to_round>  (예: R16 R8)")
        return 1

    from_round = sys.argv[1]  # e.g. R16
    to_round = sys.argv[2]    # e.g. R8

    print(f"=== 체인 시작: {from_round} 집계·발표 → {to_round} 빌드·게시 ===")

    # 1. 집계
    print(f"\n[1/4] {from_round} 집계 (tally)")
    rc = run([sys.executable, "scripts/worldcup_tally.py", from_round])
    if rc != 0:
        print(f"❌ {from_round} 집계 실패 — 중단")
        return rc

    # 2. 발표 (HF 릴스 포함)
    print(f"\n[2/4] {from_round} 결과 발표 (announce + HF 릴스)")
    rc = run([sys.executable, "scripts/worldcup_announce.py", from_round])
    if rc != 0:
        print(f"⚠️  {from_round} 발표 실패 rc={rc} — 계속 진행")

    # 3. 다음 라운드 빌드
    print(f"\n[3/4] {to_round} 빌드 (build_worldcup_round)")
    rc = run([sys.executable, "scripts/build_worldcup_round.py", to_round])
    if rc != 0:
        print(f"❌ {to_round} 빌드 실패 — 중단")
        return rc

    # 4. 다음 라운드 게시 (HF 릴스 포함)
    print(f"\n[4/4] {to_round} 게시 (publish + HF 릴스)")
    rc = run([sys.executable, "scripts/worldcup_publish.py", to_round])
    if rc != 0:
        print(f"❌ {to_round} 게시 실패")
        return rc

    print(f"\n✅ 체인 완료: {from_round} → {to_round}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
