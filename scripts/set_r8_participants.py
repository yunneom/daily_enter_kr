"""
8강(R8) 진출자 수동 확정 — 운영자 지정 8명으로 R16 승자 확정 + R8 대진 구성.

배경: 시즌2 32강 실투표 완료(R32 winner 확정) + 16강 게시됨(current_round=R16).
운영자가 8강 진출자 8명을 직접 지정해 R16 투표를 조기 확정:
  카리나 · 장원영 · 설윤 · 지수 · 원희 · 원이 · 닝닝 · 윈터

원리(기존 R32/R16 결과 보존):
  1) 이미 게시된 R16 각 매치의 winner = 그 매치 안의 지정 멤버 (매치당 정확히 1명)
  2) build_next_round → R8, current_round="R8"

결과 R8 대진 (build_next_round 페어링: R16 matches 순서대로 0vs1, 2vs3, ...):
  q0 장원영 vs 설윤 / q1 원희 vs 닝닝 / q2 카리나 vs 지수 / q3 원이 vs 윈터
게시글(2매치/게시): post1 = 장원영vs설윤 + 카리나vs지수, post2 = 원희vs닝닝 + 원이vs윈터.
멱등 — R16 이 있으면 여러 번 실행해도 동일. (R32/R16 원본 데이터는 손대지 않음)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BP = ROOT / "data" / "worldcup_bracket.json"
sys.path.insert(0, str(ROOT / "scripts"))

from worldcup_tally import build_next_round  # noqa: E402

R8_MEMBERS = {"카리나", "장원영", "설윤", "지수", "원희", "원이", "닝닝", "윈터"}


def main() -> int:
    b = json.loads(BP.read_text(encoding="utf-8"))

    if "R16" not in b["rounds"]:
        print("❌ R16 라운드가 없음 — 이 스크립트는 16강 게시 후 실행해야 함")
        return 1

    # 재실행 안전: 이미 만든 R8+ 는 제거하고 R16 부터 다시 확정 (R32/R16 원본 보존)
    for stale in ("R8", "R4", "R2", "R1"):
        b["rounds"].pop(stale, None)
    b.pop("winner", None)

    # 1) R16 winner = 매치 안의 지정멤버 (매치당 정확히 1명이어야 함)
    r16 = b["rounds"]["R16"]
    for m in r16["matches"]:
        picks = [s for s in ("a", "b") if m[s]["member"] in R8_MEMBERS]
        if len(picks) != 1:
            print(f"❌ R16 (q{m['quarter']},s{m['slot']}) 지정멤버 {len(picks)}명 — 기대 1명: "
                  f"{m['a']['member']} vs {m['b']['member']}")
            return 1
        m["winner"] = dict(m[picks[0]])
    # posts 복사본도 동기화
    for p in r16.get("posts", []):
        for key in ("match1", "match2"):
            mm = p.get(key)
            if not mm:
                continue
            for s in ("a", "b"):
                if mm[s]["member"] in R8_MEMBERS:
                    mm["winner"] = dict(mm[s])

    # 2) R16 → R8
    if not build_next_round(b, "R16"):
        print("❌ R8 빌드 실패")
        return 1

    BP.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r8 = b["rounds"]["R8"]
    print("✅ current_round =", b["current_round"])
    print("✅ 8강 대진:")
    for m in r8["matches"]:
        print(f"   q{m['quarter']}: {m['a']['member']} vs {m['b']['member']}")
    print("✅ 게시글:")
    for p in r8["posts"]:
        m1, m2 = p["match1"], p["match2"]
        print(f"   post{p['post_idx']+1}: {m1['a']['member']}vs{m1['b']['member']} / "
              f"{m2['a']['member']}vs{m2['b']['member']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
