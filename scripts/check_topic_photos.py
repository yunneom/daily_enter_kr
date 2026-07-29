"""토픽 photos 플래그 ↔ 실제 실사 커버리지 정합성 검사.

운영 원칙: 한 카드에 실물사진과 이모지가 섞이지 않는다.
- photos=True 인 토픽은 등장 가능한 멤버 "전원"의 검증 사진이 있어야 한다.
- photos 미지정 토픽은 이모지/엠블럼 고정 (사진을 쓰지 않는다).
전원 실사가 가능해진 토픽은 여기서 안내해 플래그를 올릴 수 있게 한다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from topic_registry import TOPICS  # noqa: E402

HAVE = set(json.loads((ROOT / "assets" / "idol_photos" / "_attribution.json").read_text(encoding="utf-8")))


def names_of(t: dict):
    out = []
    for row in t.get("cells") or []:
        out += [c.get("name") for c in row if c.get("name")]
    for pool in t.get("col_pools") or []:
        out += [c.get("name") for c in pool if c.get("name")]
    return out


def main() -> int:
    errors, upgradable = [], []
    for key, t in TOPICS.items():
        names = names_of(t)
        if not names:
            continue
        missing = [n for n in names if n not in HAVE]
        if t.get("photos"):
            if missing:
                errors.append(f'  ❌ "{key}" photos=True 인데 실사 미보유 {len(missing)}/{len(names)}: '
                              + ", ".join(missing[:8]) + ("..." if len(missing) > 8 else ""))
        elif not missing:
            upgradable.append(f'  💡 "{key}" 전원({len(names)}명) 실사 보유 — photos: True 로 올릴 수 있습니다')

    for line in upgradable:
        print(line)
    if errors:
        print("\n[check-topic-photos] 위반:")
        for e in errors:
            print(e)
        print(f"\n총 {len(errors)}건 — photos 플래그를 내리거나 사진을 채우세요.")
        return 1
    print(f"[check-topic-photos] OK — photos=True 토픽 전원 실사 확인 "
          f"(보유 {len(HAVE)}명)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
