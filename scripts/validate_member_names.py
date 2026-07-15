"""
멤버 이름 무결성 검증 — 오타로 인한 방송사고 방지 게이트.

[배경] 2026-07-13 브랜드평판 TOP30 카드에 '이채영→이재명'(정치인명!), '최유정→최정정'
오타가 게시됨. 원인: data/brand_reputation_girlgroup.json 만 수기 편집돼 다른 파일과 어긋남.

[원리] data/girlgroup_brand_rep_top100.json 을 정본(rank→member/group)으로 삼아,
rank 를 공유하는 모든 데이터 파일의 이름이 정본과 일치하는지 교차 검증:
  - data/brand_reputation_girlgroup.json ("그룹 멤버" 결합 문자열)
  - data/idol_photo_overrides.json / data/member_birthdays.json (rank 키)
  - data/worldcup_bracket.json (모든 라운드 a/b 후보의 rank↔member)
불일치 1건이라도 있으면 exit 1 → 게시 스크립트가 시작 전에 중단 (조용한 오타 게시 원천 차단).

사용:  python scripts/validate_member_names.py          # 전체 검증
       from validate_member_names import validate; validate()  # 게이트 (raise SystemExit)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# 그룹 표기 별칭 (정본 ↔ 파생 파일 간 허용 표기)
GROUP_ALIASES = {
    "아이브": {"아이브", "IVE"},
    "엔믹스": {"엔믹스", "NMIXX"},
    "르세라핌": {"르세라핌", "LE SSERAFIM"},
}


def _canonical() -> dict:
    """정본: rank → {member, group}."""
    raw = json.loads((DATA / "girlgroup_brand_rep_top100.json").read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else next(v for v in raw.values() if isinstance(v, list))
    return {int(r["rank"]): {"member": r["member"], "group": r["group"]} for r in rows}


def _group_ok(canon_group: str, seen: str) -> bool:
    return seen in GROUP_ALIASES.get(canon_group, {canon_group})


def validate(verbose: bool = True) -> list:
    """모든 rank 공유 파일 교차 검증. 반환: 오류 리스트(비면 통과)."""
    canon = _canonical()
    errors = []

    def err(msg):
        errors.append(msg)
        if verbose:
            print(f"  ❌ {msg}")

    # 1) brand_reputation_girlgroup.json — "그룹 멤버" 결합 문자열
    p = DATA / "brand_reputation_girlgroup.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = d.get("rankings") or d.get("data") or next(
            (v for v in d.values() if isinstance(v, list)), [])
        for r in rows:
            rank = int(r.get("rank", 0))
            if rank not in canon:
                continue
            name = (r.get("name") or "").strip()
            c = canon[rank]
            # 멤버명은 문자열 끝, 그룹명은 앞 (공백 결합)
            if not name.endswith(c["member"]):
                err(f"{p.name} rank{rank}: '{name}' ≠ 정본 멤버 '{c['member']}'")
            else:
                grp = name[: -len(c["member"])].strip()
                if grp and not _group_ok(c["group"], grp):
                    err(f"{p.name} rank{rank}: 그룹 '{grp}' ≠ 정본 '{c['group']}'")

    # 2) rank 키 dict 파일들 (idol_photo_overrides / member_birthdays)
    for fname in ("idol_photo_overrides.json", "member_birthdays.json"):
        p = DATA / fname
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for k, rec in d.items():
            try:
                rank = int(k)
            except ValueError:
                continue
            if rank not in canon or not isinstance(rec, dict):
                continue
            m = rec.get("member")
            if m and m != canon[rank]["member"]:
                err(f"{fname} rank{rank}: '{m}' ≠ 정본 '{canon[rank]['member']}'")

    # 3) worldcup_bracket.json — 모든 라운드 후보 rank↔member
    p = DATA / "worldcup_bracket.json"
    if p.exists():
        b = json.loads(p.read_text(encoding="utf-8"))
        seen = set()
        for rnd in (b.get("rounds") or {}).values():
            for m in rnd.get("matches", []):
                for side in ("a", "b"):
                    c = m.get(side) or {}
                    rank, member = c.get("rank"), c.get("member")
                    if rank is None or (rank, member) in seen:
                        continue
                    seen.add((rank, member))
                    if int(rank) in canon and member != canon[int(rank)]["member"]:
                        err(f"worldcup_bracket rank{rank}: '{member}' ≠ 정본 '{canon[int(rank)]['member']}'")

    if verbose and not errors:
        print("✅ 멤버 이름 무결성 검증 통과 (rank 교차 일치)")
    return errors


def gate():
    """게시 스크립트용 게이트 — 오류 시 즉시 중단."""
    errors = validate(verbose=True)
    if errors:
        print(f"🛑 멤버 이름 불일치 {len(errors)}건 — 게시 중단 (오타 방송사고 방지)")
        raise SystemExit(1)


if __name__ == "__main__":
    sys.exit(1 if validate() else 0)
