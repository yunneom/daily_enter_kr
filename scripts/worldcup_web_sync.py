"""
worldcup_web_sync.py — 웹 투표(data/web_votes.json) → 브래킷(data/worldcup_bracket.json) 수렴.

[목적]
웹앱(web/)의 1:1 탭 투표를 집계해 각 매치의 votes.raw_a/raw_b 와 votes.a/votes.b(웹 가중치=1
이므로 raw 와 동일) 를 채우고, winner 를 결정한다. GitHub Actions 에서 주기적으로 실행해
웹 표를 브래킷에 수렴시키는 용도. 결과 발표/다음 라운드 빌드는 기존 worldcup_announce /
worldcup_tally 파이프라인이 담당한다.

[winner 결정 규칙 — scripts/worldcup_tally.py decide_winners.pick() 와 동일하게 재구현]
  ① 가중 집계 (weighted) 큰 쪽
  ② 동률 시 raw 인원수 큰 쪽
  ③ 그래도 동률 시 시드 높은(rank 낮은) 쪽
worldcup_tally 모듈을 직접 import 하지 않고(결합도 회피) 동일 로직을 pick() 으로 재구현했다.
바뀌면 worldcup_tally.py 의 decide_winners 와 함께 갱신할 것.

[옵션]
  --round R8       특정 라운드만 (기본: bracket current_round)
  --merge-ig       기존 IG 가중표(votes.a/b)에 웹 표를 더함 (기본: 웹 표로 덮어씀)
  --dry-run        파일 저장하지 않고 요약만 출력

순수 표준 라이브러리(json, pathlib, argparse). 재실행해도 동일 결과(idempotent).
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).parent.parent
BRACKET_PATH = ROOT / "data" / "worldcup_bracket.json"
WEB_VOTES_PATH = ROOT / "data" / "web_votes.json"


def pick(wa: int, wb: int, ra: int, rb: int, rank_a: int, rank_b: int) -> str:
    """'a' | 'b'. scripts/worldcup_tally.py decide_winners.pick() 와 동일 규칙.
    ① weighted → ② raw → ③ 시드(rank 낮은 쪽)."""
    if wa != wb:
        return "a" if wa > wb else "b"
    if ra != rb:
        return "a" if ra > rb else "b"
    return "a" if rank_a <= rank_b else "b"


def load_web_counts(round_key: str) -> Dict[Tuple[int, int], Dict[str, int]]:
    """web_votes.json → {(quarter, slot): {'a': N, 'b': N}} (해당 라운드, suspected 제외)."""
    counts: Dict[Tuple[int, int], Dict[str, int]] = {}
    if not WEB_VOTES_PATH.exists():
        return counts
    try:
        data = json.loads(WEB_VOTES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return counts
    for v in data.get("votes", []):
        if v.get("round") != round_key:
            continue
        if v.get("suspected"):
            continue
        q = v.get("quarter")
        s = v.get("slot")
        pk = v.get("pick")
        if q is None or s is None or pk not in ("a", "b"):
            continue
        key = (int(q), int(s))
        bucket = counts.setdefault(key, {"a": 0, "b": 0})
        bucket[pk] += 1
    return counts


def apply_to_match(m: Dict, web: Dict[str, int], merge_ig: bool) -> Dict:
    """매치 1개에 웹 표 반영 + winner 결정. 변경 요약 dict 반환."""
    raw_web_a = web.get("a", 0)
    raw_web_b = web.get("b", 0)

    existing = m.get("votes") or {}
    if merge_ig:
        # 기존 IG 가중/raw 에 웹 표(가중치 1)를 더함
        wa = int(existing.get("a", 0)) + raw_web_a
        wb = int(existing.get("b", 0)) + raw_web_b
        ra = int(existing.get("raw_a", 0)) + raw_web_a
        rb = int(existing.get("raw_b", 0)) + raw_web_b
    else:
        # 웹 표로 덮어씀 (웹 가중치=1 → weighted == raw)
        wa = ra = raw_web_a
        wb = rb = raw_web_b

    rank_a = int(m["a"].get("rank", 99))
    rank_b = int(m["b"].get("rank", 99))
    win = pick(wa, wb, ra, rb, rank_a, rank_b)
    winner = m["a"] if win == "a" else m["b"]

    m["votes"] = {"a": wa, "b": wb, "raw_a": ra, "raw_b": rb}
    # 표가 0:0 이면 winner 미정으로 둔다 (시드 자동승 방지 — 발표 단계가 결정)
    if wa == 0 and wb == 0 and ra == 0 and rb == 0:
        m["winner"] = None
        decided = None
    else:
        m["winner"] = winner
        decided = winner

    return {
        "quarter": m["quarter"],
        "slot": m["slot"],
        "a": m["a"]["member"],
        "b": m["b"]["member"],
        "wa": wa,
        "wb": wb,
        "ra": ra,
        "rb": rb,
        "winner": decided["member"] if decided else None,
    }


def sync_round(bracket: Dict, round_key: str, merge_ig: bool) -> List[Dict]:
    """라운드의 matches[] 와 posts[].match1/2 양쪽을 (quarter,slot) 으로 동기화."""
    rnd = bracket["rounds"][round_key]
    web_counts = load_web_counts(round_key)

    # matches[] 가 권위(authority). 여기서 결정한 votes/winner 를 posts 카피에 미러.
    summaries: List[Dict] = []
    decided_by_key: Dict[Tuple[int, int], Tuple[Dict, Dict]] = {}
    for m in rnd.get("matches", []):
        key = (m["quarter"], m["slot"])
        web = web_counts.get(key, {"a": 0, "b": 0})
        summary = apply_to_match(m, web, merge_ig)
        summaries.append(summary)
        decided_by_key[key] = (m.get("votes"), m.get("winner"))

    # posts[].match1/match2 미러 (같은 좌표면 동일 votes/winner)
    for post in rnd.get("posts", []):
        for mk in ("match1", "match2"):
            pm = post.get(mk)
            if not pm:
                continue
            key = (pm.get("quarter"), pm.get("slot"))
            if key in decided_by_key:
                votes, winner = decided_by_key[key]
                pm["votes"] = votes
                pm["winner"] = winner

    return summaries


def main() -> int:
    ap = argparse.ArgumentParser(description="웹 투표 → 브래킷 수렴")
    ap.add_argument("--round", help="집계할 라운드 (기본: current_round)")
    ap.add_argument("--merge-ig", action="store_true", help="기존 IG 가중표에 웹 표를 더함")
    ap.add_argument("--dry-run", action="store_true", help="저장 없이 요약만 출력")
    args = ap.parse_args()

    bracket = json.loads(BRACKET_PATH.read_text(encoding="utf-8"))
    round_key = args.round or bracket.get("current_round")
    if round_key not in bracket.get("rounds", {}):
        print(f"[ERROR] 라운드 없음: {round_key}")
        return 1

    print(f"=== 웹 투표 수렴: {round_key} (merge_ig={args.merge_ig}, dry_run={args.dry_run}) ===")
    summaries = sync_round(bracket, round_key, args.merge_ig)
    for s in summaries:
        win = s["winner"] or "미정(0표)"
        print(
            f"  ({s['quarter']},{s['slot']}) {s['a']} [가중{s['wa']}/raw{s['ra']}] vs "
            f"{s['b']} [가중{s['wb']}/raw{s['rb']}] -> 승: {win}"
        )

    if args.dry_run:
        print("[dry-run] 저장하지 않음")
        return 0

    BRACKET_PATH.write_text(
        json.dumps(bracket, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] {BRACKET_PATH.relative_to(ROOT)} 갱신")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
