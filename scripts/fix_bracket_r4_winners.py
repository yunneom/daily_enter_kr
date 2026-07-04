"""
4강(R4) 승자 수동 확정 + 결승(R2) 생성.

배경: 7/4 크론 3시간 드롭으로 14:00 자동 집계가 미실행 → 운영자가 댓글 확인 후
승자 직접 확정: 닝닝(vs 윈터) · 카리나(vs 설윤).
R2 구조는 worldcup_tally._build_finals 와 동일 (결승=승자전, 3·4위전=패자전,
posts 는 *_solo 2건). 멱등.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
BP = ROOT / "data" / "worldcup_bracket.json"

CORRECT = {(0, 0): "닝닝", (2, 1): "카리나"}


def _winner_loser(m: dict):
    want = CORRECT[(m["quarter"], m["slot"])]
    if m["a"]["member"] == want:
        return dict(m["a"]), dict(m["b"])
    if m["b"]["member"] == want:
        return dict(m["b"]), dict(m["a"])
    raise SystemExit(f"❌ (q{m['quarter']},s{m['slot']}) 승자 '{want}' 후보 없음")


def main() -> int:
    b = json.loads(BP.read_text(encoding="utf-8"))
    r4 = b["rounds"]["R4"]

    winners, losers = [], []
    for m in r4["matches"]:
        w, l = _winner_loser(m)
        m["winner"] = w
        winners.append(w)
        losers.append(l)
    for p in r4.get("posts", []):
        for key in ("match1", "match2"):
            mm = p.get(key)
            if mm and (mm.get("quarter"), mm.get("slot")) in CORRECT:
                mm["winner"], _ = _winner_loser(mm)

    final_match = {"round": "R2", "type": "final",
                   "a": winners[0], "b": winners[1], "winner": None}
    third_match = {"round": "R2", "type": "third_place",
                   "a": losers[0], "b": losers[1], "winner": None}
    b["rounds"]["R2"] = {
        "matches": [third_match, final_match],
        "posts": [
            {"post_idx": 0, "match1": third_match, "match2": third_match,
             "type": "third_place_solo"},
            {"post_idx": 1, "match1": final_match, "match2": final_match,
             "type": "final_solo"},
        ],
    }
    b["current_round"] = "R2"
    BP.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ R4 확정: {winners[0]['member']}·{winners[1]['member']} 결승 진출")
    print(f"✅ 결승: {winners[0]['member']} vs {winners[1]['member']} / "
          f"3·4위전: {losers[0]['member']} vs {losers[1]['member']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
