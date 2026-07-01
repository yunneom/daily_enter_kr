"""
8강(R8) 승자 수동 정정 + 4강(R4) 재구성.

배경: R8 이 잘못 집계되어(자동/시드 기준) 결과가 틀린 채 발표됨 → 운영자가 삭제.
실제 투표 결과 승자: 닝닝 · 윈터 · 카리나 · 설윤.
이 스크립트는 data/worldcup_bracket.json 의 R8 winner 를 정답으로 바꾸고,
그 승자들로 R4(준결승) matches/posts 를 다시 만든다. 멱등(여러 번 실행해도 동일).

준결승 대진: 닝닝 vs 윈터 / 카리나 vs 설윤.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
BP = ROOT / "data" / "worldcup_bracket.json"

# (quarter, slot) → 정답 승자 멤버명
CORRECT = {(0, 0): "닝닝", (1, 1): "윈터", (2, 2): "카리나", (3, 3): "설윤"}


def _winner_obj(m: dict) -> dict:
    want = CORRECT[(m["quarter"], m["slot"])]
    for side in ("a", "b"):
        if m[side]["member"] == want:
            return dict(m[side])
    raise SystemExit(f"❌ (q{m['quarter']},s{m['slot']}) 에서 승자 '{want}' 후보를 못 찾음")


def main() -> int:
    b = json.loads(BP.read_text(encoding="utf-8"))
    r8 = b["rounds"]["R8"]

    # 1) R8 winner 정정 (matches)
    for m in r8["matches"]:
        m["winner"] = _winner_obj(m)
    # posts 복사본도 동기화
    for p in r8.get("posts", []):
        for key in ("match1", "match2"):
            mm = p.get(key)
            if mm and (mm["quarter"], mm["slot"]) in CORRECT:
                mm["winner"] = _winner_obj(mm)

    # 2) R8 승자 (slot 순서) → R4 재구성
    order = [(0, 0), (1, 1), (2, 2), (3, 3)]
    winners = [next(m["winner"] for m in r8["matches"]
                    if (m["quarter"], m["slot"]) == qs) for qs in order]

    def r4_match(quarter, slot, a, b_):
        return {"quarter": quarter, "slot": slot, "round": "R4",
                "a": dict(a), "b": dict(b_), "winner": None}

    m1 = r4_match(0, 0, winners[0], winners[1])   # 닝닝 vs 윈터
    m2 = r4_match(2, 1, winners[2], winners[3])   # 카리나 vs 설윤
    b["rounds"]["R4"] = {
        "matches": [m1, m2],
        "posts": [{"post_idx": 0, "match1": dict(m1), "match2": dict(m2)}],
    }
    b["current_round"] = "R4"

    BP.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("✅ R8 승자 정정:", [w["member"] for w in winners])
    print(f"✅ 준결승 대진: {winners[0]['member']} vs {winners[1]['member']} / "
          f"{winners[2]['member']} vs {winners[3]['member']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
