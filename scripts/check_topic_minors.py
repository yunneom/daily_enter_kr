"""매트릭스 토픽의 미성년 멤버 배제 게이트.

[왜] "만원으로 걸그룹 조합" 류 토픽은 멤버에게 가격표를 붙이고 '비주얼' 같은
컬럼으로 고른다. 만 18세 미만 멤버를 이 프레임에 넣는 것은 프로젝트 안전 정책
(미성년 외모/서열 언급 금지)과 IG 정책 모두에 걸린다. 사람이 손으로 적는
topic_registry 라인업에서 실수로 미성년이 들어가는 것을 게시 전에 막는다.

[정책]
- data/group_rosters.json 의 groups[<그룹>].birthdays[<활동명>] = "YYYY-MM-DD" 기준.
- 오늘(KST) 만 18세 미만 → 오류(exit 1).
- 생년 미등록 → 기본은 경고만(기존 토픽 호환). STRICT_MINOR_GATE=1 이면 오류.
  (생년을 채울수록 게이트가 강해진다 — 새 토픽은 반드시 생년을 채운 뒤 등록.)

사용:
  python scripts/check_topic_minors.py            # 위반 있으면 exit 1
  STRICT_MINOR_GATE=1 python scripts/check_topic_minors.py
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
ROSTERS = json.loads((ROOT / "data" / "group_rosters.json").read_text(encoding="utf-8"))["groups"]
KST = timezone(timedelta(hours=9))
ADULT_AGE = 18


def _norm(s: str) -> str:
    return "".join((s or "").lower().split()).replace("(", "").replace(")", "").replace("_", "").replace("-", "")


_GROUP_KEY = {}
for key, r in ROSTERS.items():
    for spelling in [key] + list(r.get("aliases_of_group") or []):
        _GROUP_KEY[_norm(spelling)] = key


def topic_pairs():
    src = (ROOT / "src" / "topic_registry.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r'"name":\s*"([^"]+)",\s*"subtitle":\s*"([^"]+)"', src)))


def age_on(birth: str, today: date) -> int:
    b = datetime.strptime(birth, "%Y-%m-%d").date()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def main() -> int:
    strict = os.environ.get("STRICT_MINOR_GATE") == "1"
    today = datetime.now(KST).date()
    errors, warns = [], []
    for name, group in topic_pairs():
        gkey = _GROUP_KEY.get(_norm(group))
        if not gkey:
            continue  # 미검증 그룹은 check_topic_names 가 보고
        r = ROSTERS[gkey]
        canonical = r.get("aliases", {}).get(name, name)
        birth = (r.get("birthdays") or {}).get(canonical)
        if not birth:
            warns.append(f"  ⚠️ {group} {name} — 생년 미등록")
            continue
        try:
            a = age_on(birth, today)
        except ValueError:
            warns.append(f"  ⚠️ {group} {name} — 생년 형식 오류({birth})")
            continue
        if a < ADULT_AGE:
            errors.append(f"  ❌ {group} {name} — 만 {a}세 (생년 {birth}) → 가격표 토픽 사용 불가")
    if warns:
        print(f"생년 미등록/오류 {len(warns)}건:")
        print("\n".join(warns))
    if errors:
        print(f"\n🛑 미성년 멤버 {len(errors)}명이 매트릭스 토픽에 포함됨:")
        print("\n".join(errors))
        return 1
    if strict and warns:
        print("\n🛑 STRICT_MINOR_GATE: 생년 미등록 멤버가 있어 실패 처리")
        return 1
    print(f"✅ 미성년 게이트 통과 — 대조 {len(topic_pairs())}쌍, 위반 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
