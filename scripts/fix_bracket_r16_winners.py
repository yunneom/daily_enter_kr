"""
R16 승자 수동 수정 (닝닝·안유진·태연) + R8 재구성.

IG Graph API 댓글 조회가 instagram_manage_comments 권한 없이는 항상 빈 배열을 반환해
집계가 모두 0표 → 시드(랭킹) 우선으로 잘못된 결과가 생성됐음.
실제 댓글 투표 결과를 반영해 R16 승자를 수동으로 설정한다.

실행: python scripts/fix_bracket_r16_winners.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BRACKET_PATH = ROOT / "data" / "worldcup_bracket.json"

ALL_WINNERS = {
    0: {"rank":  1, "group": "아이브",    "member": "장원영", "score": 7538960},
    1: {"rank": 15, "group": "에스파",    "member": "닝닝",   "score": 1596316},  # 업셋
    2: {"rank":  8, "group": "아이브",    "member": "안유진", "score": 2696338},  # 업셋
    3: {"rank":  9, "group": "에스파",    "member": "윈터",   "score": 2361861},
    4: {"rank":  3, "group": "에스파",    "member": "카리나", "score": 4736626},
    5: {"rank": 16, "group": "소녀시대",  "member": "태연",   "score": 1572474},  # 업셋
    6: {"rank":  2, "group": "블랙핑크",  "member": "제니",   "score": 7166269},
    7: {"rank": 12, "group": "엔믹스",    "member": "설윤",   "score": 1778210},
}
A_WINS = {0, 3, 4, 6}


def make_votes(slot: int) -> dict:
    a = 1 if slot in A_WINS else 0
    return {"a": a, "b": 1 - a, "raw_a": a, "raw_b": 1 - a}


def main() -> int:
    bracket = json.loads(BRACKET_PATH.read_text(encoding="utf-8"))
    r16 = bracket["rounds"]["R16"]

    for m in r16["matches"]:
        s = m["slot"]
        m["winner"] = ALL_WINNERS[s]
        m["votes"] = make_votes(s)
        print(f"  R16 slot {s}: {m['a']['member']} vs {m['b']['member']} → {m['winner']['member']}")

    for p in r16["posts"]:
        for k in ("match1", "match2"):
            m = p[k]
            s = m.get("slot")
            if s in ALL_WINNERS:
                m["winner"] = ALL_WINNERS[s]
                m["votes"] = make_votes(s)

    r16_m = r16["matches"]
    r8_m = []
    for i in range(0, len(r16_m), 2):
        a, b = r16_m[i], r16_m[i + 1]
        r8_m.append({
            "quarter": a["quarter"], "slot": i // 2,
            "round": "R8", "a": a["winner"], "b": b["winner"], "winner": None,
        })
    half = len(r8_m) // 2
    r8_posts = [
        {"post_idx": i, "match1": r8_m[i], "match2": r8_m[i + half]}
        for i in range(half)
    ]
    bracket["rounds"]["R8"] = {"matches": r8_m, "posts": r8_posts}
    bracket["current_round"] = "R8"

    BRACKET_PATH.write_text(json.dumps(bracket, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 새 R8 대진표 ===")
    for m in r8_m:
        print(f"  {m['a']['member']}({m['a']['group']}) vs {m['b']['member']}({m['b']['group']})")
    print("✅ bracket.json 수정 완료")

    # 잘못 게시된 항목 ledger 에서 제거
    _fix_ledger()
    return 0


WRONG_TOPIC_IDS = {
    "worldcup_announce_r16",
    "worldcup_r8_1",
    "worldcup_r8_2",
    "worldcup_hf_r8_bracket",
}


def _fix_ledger() -> None:
    ledger_path = ROOT / "post_ledger.json"
    if not ledger_path.exists():
        print("ℹ️  post_ledger.json 없음 — ledger 수정 스킵")
        return
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    before = len(ledger.get("entries", []))
    ledger["entries"] = [
        e for e in ledger.get("entries", [])
        if e.get("topic_id") not in WRONG_TOPIC_IDS
    ]
    after = len(ledger["entries"])
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ post_ledger.json 수정: {before - after}개 잘못된 항목 제거 ({before} → {after})")


if __name__ == "__main__":
    sys.exit(main())
