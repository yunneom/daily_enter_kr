"""그룹 단체사진 캐시 워밍 — 큐레이션된 커먼즈 파일을 assets/group_photos/ 에 수집·커밋.

개인 멤버 사진(warm_photo_cache.py)과 달리 여기서는 "그룹 단체 사진"을 다룬다.
신인 그룹 브랜드평판 카운트다운(run_rookie)처럼 카드의 주체가 개인이 아니라
그룹 브랜드인 포맷 전용. 개인 단독 노출이 아니므로 성인 게이트 대상이 아니고,
대신 다음 게이트를 적용한다 (완화 금지):

- 큐레이션 allowlist: data/rookie_group_photos.json 에 사람이/검증 절차로 등록한
  커먼즈 파일명만 받는다. 자동 검색 없음.
- CC/PD 라이선스 재검증: 등록 당시 라이선스와 무관하게 다운로드 시점에
  커먼즈 API 로 다시 조회해 자유 라이선스가 아니면 거부한다.

사용:
  python scripts/warm_group_photo_cache.py           # 없는 것만 수집
  python scripts/warm_group_photo_cache.py --refresh # 전체 재수집
  python scripts/warm_group_photo_cache.py --check   # 커버리지만 점검 (미보유 시 exit 1)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

import idol_photo  # noqa: E402  (라이선스 조회/판정 헬퍼 재사용)

CURATED_PATH = ROOT / "data" / "rookie_group_photos.json"
DEST_DIR = ROOT / "assets" / "group_photos"
DEST_ATTR = DEST_DIR / "_attribution.json"
UA = idol_photo.UA


def load_group_cache() -> dict:
    """커밋된 그룹 사진 캐시 {그룹명: {path, artist, license, file, descurl}}."""
    if not DEST_ATTR.exists():
        return {}
    try:
        return json.loads(DEST_ATTR.read_text(encoding="utf-8"))
    except Exception:
        return {}


def group_cached_photo(group_kr: str):
    """게시 파이프라인용 조회 — 커밋 캐시에 있으면 절대경로 레코드, 없으면 None."""
    rec = load_group_cache().get(group_kr)
    if rec and rec.get("path") and (DEST_DIR / rec["path"]).exists():
        return {**rec, "path": str(DEST_DIR / rec["path"])}
    return None


def _download(file_name: str, dest: Path) -> bool:
    """Special:FilePath 썸네일 → wsrv 프록시 폴백 (idol_photo 와 같은 429 대응)."""
    direct = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
              f"{quote(file_name)}?width=1080")
    enc = quote(direct, safe="")
    sources = [("direct", direct, 1),
               ("wsrv", f"https://wsrv.nl/?url={enc}&output=jpg", 4)]
    for src_name, url, tries in sources:
        for attempt in range(tries):
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            except Exception as e:
                print(f"  ⚠️ {src_name} 예외: {type(e).__name__}: {e}")
                break
            retryable = r.status_code == 429 or (
                src_name == "wsrv" and r.status_code in (404, 500, 502, 503))
            if retryable:
                if attempt + 1 >= tries:
                    print(f"  ⏭️ {src_name} {r.status_code} — 다음 소스로")
                    break
                wait = min(int(r.headers.get("Retry-After") or 6) + attempt * 6, 45)
                print(f"  ⏳ {src_name} {r.status_code} — {wait}s 대기 재시도({attempt + 1}/{tries})")
                time.sleep(wait)
                continue
            if not r.ok:
                print(f"  ⚠️ {src_name} HTTP {r.status_code} — 다음 소스")
                break
            if len(r.content) < 2000:
                print(f"  ⚠️ {src_name} 응답 과소({len(r.content)}B) — 다음 소스")
                break
            dest.write_bytes(r.content)
            print(f"  ✅ 다운로드 ({src_name}, {len(r.content) // 1024}KB)")
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))["groups"]
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    attr = {} if args.refresh else load_group_cache()

    need = []
    for group_kr, meta in curated.items():
        rec = attr.get(group_kr)
        if rec and rec.get("path") and (DEST_DIR / rec["path"]).exists() and not args.refresh:
            continue
        need.append((group_kr, meta))

    have_n = len(curated) - len(need)
    print(f"📸 그룹 사진 대상 {len(curated)} — 보유 {have_n} / 필요 {len(need)}")
    if args.check:
        if need:
            print("❌ 미보유: " + ", ".join(g for g, _ in need))
            return 1
        print("✅ 전 그룹 보유")
        return 0
    if not need:
        print("✅ 이미 전부 보유")
        return 0

    ok, fail = [], []
    for group_kr, meta in need:
        file_name = meta["file"]
        print(f"\n▶ {group_kr} — File:{file_name}")
        # 라이선스 재검증 (완화 금지): 큐레이션 값이 아니라 커먼즈 실시간 메타로 판정.
        lic = idol_photo._fetch_license(file_name)
        if not idol_photo._is_free_license(lic.get("license") or ""):
            print(f"  🚫 자유 라이선스 확인 실패({lic.get('license') or '조회 불가'}) — 거부")
            fail.append(group_kr)
            time.sleep(4)
            continue
        dest_name = f"{group_kr}.jpg"
        if _download(file_name, DEST_DIR / dest_name):
            attr[group_kr] = {
                "path": dest_name,
                "file": file_name,
                "artist": lic.get("artist", ""),
                "license": lic.get("license", ""),
                "descurl": lic.get("descurl", ""),
            }
            ok.append(group_kr)
        else:
            fail.append(group_kr)
        time.sleep(4)

    DEST_ATTR.write_text(json.dumps(attr, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    print(f"\n📊 신규 {len(ok)} / 실패 {len(fail)} / 총 보유 {have_n + len(ok)}/{len(curated)}")
    if fail:
        print("⚠️ 실패: " + ", ".join(fail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
