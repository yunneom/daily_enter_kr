"""
실사 사진 캐시 워밍 — 검증된 커먼즈 사진을 저장소(assets/idol_photos/)에 수집·커밋.

[왜 필요한가]
upload.wikimedia.org 는 GitHub Actions 공유 IP 에 429 를 강하게 건다. 매 실행마다
30장을 새로 받으면 일부가 반드시 실패하고, 그 멤버는 그라디언트 폴백 카드로 나간다
(2026-07: 유닛 빌더 12명 중 윈터·카즈하 2명 전 소스 실패 → 폴백으로 게시된 사고).

이 스크립트는 사진을 한 번 받아 저장소에 커밋해 둔다. 이후 게시 파이프라인은
idol_photo.repo_cached_photo() 로 커밋된 파일만 읽으므로 런타임 네트워크 의존이 0.

[사용]
  python scripts/warm_photo_cache.py                 # 없는 것만 수집
  python scripts/warm_photo_cache.py --refresh       # 전체 재수집(기존 무시)
  python scripts/warm_photo_cache.py --check         # 수집 없이 커버리지만 점검
  IDOL_PHOTO_GAP_SEC=12 python scripts/warm_photo_cache.py   # 더 느리게(429 회피)

[안전]
사진 획득 자체는 idol_photo.fetch_photo() 를 그대로 쓴다 — 성인 게이트, 검증
오버라이드 allowlist, 제목 일치 가드, CC/PD 라이선스 가드가 모두 그대로 적용된다.
이 스크립트는 그 결과물을 저장소 캐시로 복사만 한다 (게이트 우회 없음).
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

import idol_photo  # noqa: E402

OVERRIDES_PATH = ROOT / "data" / "idol_photo_overrides.json"
DEST_DIR = idol_photo.REPO_CACHE_DIR
DEST_ATTR = idol_photo.REPO_ATTR_PATH


def targets() -> list:
    """검증 오버라이드에 등록된 멤버 = 실사 대상 전체."""
    ov = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    return [(int(r), v["member"], v["group"]) for r, v in sorted(ov.items(), key=lambda kv: int(kv[0]))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="기존 캐시 무시하고 전체 재수집")
    ap.add_argument("--check", action="store_true", help="수집 없이 커버리지만 점검")
    args = ap.parse_args()

    all_targets = targets()
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    attr = {} if args.refresh else idol_photo.load_repo_cache()

    have, need = [], []
    for rank, name, group in all_targets:
        rec = attr.get(name)
        if rec and rec.get("path") and (DEST_DIR / rec["path"]).exists() and not args.refresh:
            have.append(name)
        else:
            need.append((rank, name, group))

    print(f"📸 실사 대상 {len(all_targets)}명 — 보유 {len(have)} / 필요 {len(need)}")

    if args.check:
        if need:
            print("\n❌ 미보유 멤버:")
            for rank, name, group in need:
                print(f"   {rank:2d} {group} {name}")
            return 1
        print("✅ 전원 실사 보유")
        return 0

    if not need:
        print("✅ 이미 전원 보유 — 수집할 것 없음")
        return 0

    gap = os.environ.get("IDOL_PHOTO_GAP_SEC", "(기본 4)")
    print(f"⏬ 수집 시작 (멤버 간 간격: {gap}초)\n")

    ok, fail = [], []
    for rank, name, group in need:
        rec = idol_photo.fetch_photo(name)
        if not rec or not rec.get("path"):
            print(f"  ❌ {group} {name} — 획득 실패")
            fail.append((rank, name, group))
            continue
        src = Path(rec["path"])
        dest_name = f"{rank:02d}_{name}{src.suffix or '.jpg'}"
        shutil.copyfile(src, DEST_DIR / dest_name)
        attr[name] = {
            "path": dest_name,
            "artist": rec.get("artist", ""),
            "license": rec.get("license", ""),
            "title": rec.get("title", ""),
            "descurl": rec.get("descurl", ""),
        }
        print(f"  ✅ {group} {name} → {dest_name}")
        ok.append(name)

    DEST_ATTR.write_text(json.dumps(attr, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")

    print(f"\n📊 신규 {len(ok)} / 실패 {len(fail)} / 총 보유 {len(have) + len(ok)}/{len(all_targets)}")
    if fail:
        print("\n⚠️ 실패 멤버 (재실행하면 이어서 시도):")
        for rank, name, group in fail:
            print(f"   {rank:2d} {group} {name}")
        # 부분 성공도 커밋 가치가 있으므로 0 반환. 전량 필요 여부는 --check 로 판정.
    return 0


if __name__ == "__main__":
    sys.exit(main())
