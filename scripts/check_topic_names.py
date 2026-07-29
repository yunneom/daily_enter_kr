"""토픽 하드코딩 멤버명 ↔ 검증된 공식 명단 대조.

[왜] topic_registry 의 col_pools/cells 는 사람이 손으로 적은 실명이다. 실제로
- 'fromis_9 시연' — 존재하지 않는 이름
- 'fromis_9 이새롬', 'RIIZE 승한' — 탈퇴 멤버
- 'IVE 유진'+'IVE 안유진', 'RIIZE 원빈'+'RIIZE 박원빈' — 동일인 중복
같은 오류가 확인됐다. 실존 인물 오표기라 게시 전에 막아야 한다.

[정책]
data/group_rosters.json 에 검증된 그룹만 등재한다. 검증된 그룹의 멤버는 반드시
현역 명단(또는 alias)에 있어야 하고, former 에 있으면 오류로 잡는다.
아직 검증하지 않은 그룹은 통과시키되 리포트에 남겨 진행 상황을 보이게 한다.

사용:
  python scripts/check_topic_names.py           # 위반 있으면 exit 1
  python scripts/check_topic_names.py --report   # 미검증 그룹까지 전체 현황
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
ROSTERS = json.loads((ROOT / "data" / "group_rosters.json").read_text(encoding="utf-8"))["groups"]


def _norm(s: str) -> str:
    return "".join((s or "").lower().split()).replace("(", "").replace(")", "").replace("_", "").replace("-", "")


# 그룹 표기 → 검증 로스터 키
_GROUP_KEY = {}
for key, r in ROSTERS.items():
    for spelling in [key] + list(r.get("aliases_of_group") or []):
        _GROUP_KEY[_norm(spelling)] = key


def topic_pairs():
    """topic_registry 소스에서 (그룹, 멤버) 쌍 추출 — import 없이 정규식으로."""
    src = (ROOT / "src" / "topic_registry.py").read_text(encoding="utf-8")
    return re.findall(r'"name":\s*"([^"]+)",\s*"subtitle":\s*"([^"]+)"', src)


def main() -> int:
    report = "--report" in sys.argv
    pairs = topic_pairs()
    errors, unverified = [], defaultdict(set)
    seen_person = defaultdict(set)   # (group_key, canonical_name) → 표기들

    for name, group in pairs:
        gkey = _GROUP_KEY.get(_norm(group))
        if not gkey:
            unverified[group].add(name)
            continue
        r = ROSTERS[gkey]
        canonical = r.get("aliases", {}).get(name, name)
        if name in (r.get("former") or []) or canonical in (r.get("former") or []):
            errors.append(f'  ❌ {group} "{name}" — 탈퇴 멤버 (현역 아님)')
        elif canonical not in r["members"]:
            errors.append(f'  ❌ {group} "{name}" — 공식 명단에 없음 '
                          f'(현역: {", ".join(r["members"])})')
        else:
            seen_person[(gkey, canonical)].add(name)

    # 같은 인물이 여러 표기로 중복 등재된 경우
    for (gkey, canonical), spellings in seen_person.items():
        if len(spellings) > 1:
            errors.append(f'  ❌ {gkey} "{canonical}" — 동일 인물이 여러 표기로 중복: '
                          + ", ".join(sorted(spellings)))

    verified_cnt = sum(1 for n, g in pairs if _GROUP_KEY.get(_norm(g)))
    print(f"[check-topic-names] 검증 대상 {verified_cnt}/{len(pairs)}건 "
          f"(검증 그룹 {len(ROSTERS)}개 / 미검증 {len(unverified)}개)")

    if report and unverified:
        print("\n미검증 그룹 (group_rosters.json 에 추가 필요):")
        for g, names in sorted(unverified.items()):
            print(f"   {g}: {', '.join(sorted(names))}")

    if errors:
        print("\n위반:")
        for e in errors:
            print(e)
        print(f"\n총 {len(errors)}건 — 실존 인물 오표기이므로 수정 전 게시 금지.")
        return 1
    print("검증된 그룹 범위에서 오류 없음.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
