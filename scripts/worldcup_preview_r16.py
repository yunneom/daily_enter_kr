"""
16강 미리보기 렌더 — 게시 X, 카드/영상만 빌드해 아티팩트로 업로드.

[목적]
실사 사진(위키미디어 CC)이 실제로 어떻게 나오는지 게시 전 컨펌.
dev 컨테이너는 위키 차단이라 로컬 확인 불가 → Actions 런타임(위키 접근 가능)에서
이 스크립트로 렌더 → workflow 가 output_enter 를 아티팩트로 올림 → 다운받아 확인.

[라인업]
32강 집계 전이므로 '시드 기준 예상 16강'(높은 시드 진출) 으로 렌더.
실제 라인업은 6/25 집계 후 확정되며 포맷은 동일.

[게시 안 함]
IG/YT 호출 0. 순수 렌더만. output_enter/worldcup_r16_preview/ 에 저장.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import worldcup_tally as wt  # noqa: E402
from make_worldcup_match_card import make_worldcup_match_card  # noqa: E402
from make_worldcup_match_video import (  # noqa: E402
    make_worldcup_match_video, build_worldcup_caption,
)
import idol_photo  # noqa: E402


def main():
    br = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    sim = copy.deepcopy(br)
    # R32 각 매치 winner = 높은 시드(낮은 rank)
    for m in sim["rounds"]["R32"]["matches"]:
        a, b = m["a"], m["b"]
        m["winner"] = a if a.get("rank", 99) <= b.get("rank", 99) else b
    wt.build_next_round(sim, "R32")
    posts = sim["rounds"]["R16"]["posts"]

    out = ROOT / "output_enter" / "worldcup_r16_preview"
    out.mkdir(parents=True, exist_ok=True)
    bgm = ROOT / "assets" / "bgm" / "daily_enter_theme_c.mp3"

    print(f"=== 16강 미리보기 렌더 (시드 예상, {len(posts)}게시글) ===")
    # 사진 커버리지 집계
    all_members = set()
    for p in posts:
        for mt in (p["match1"], p["match2"]):
            all_members.add(mt["a"]["member"]); all_members.add(mt["b"]["member"])
    photo_ok, photo_no = [], []
    for name in sorted(all_members):
        rec = idol_photo.fetch_photo(name)
        (photo_ok if rec else photo_no).append(name)
    print(f"📷 실사 사진 있음 ({len(photo_ok)}): {', '.join(photo_ok)}")
    print(f"🔤 이모지 폴백 ({len(photo_no)}): {', '.join(photo_no)}")

    for p in posts:
        idx = p["post_idx"] + 1
        jpg = out / f"r16_preview_post{idx}.jpg"
        mp4 = out / f"r16_preview_post{idx}.mp4"
        make_worldcup_match_card("16강", idx, len(posts), p["match1"], p["match2"], jpg)
        make_worldcup_match_video(jpg, mp4, duration=10.0,
                                  bgm_path=bgm if bgm.exists() else None)
        cap = build_worldcup_caption("16강", idx, len(posts), p["match1"], p["match2"])
        (out / f"r16_preview_post{idx}.caption.txt").write_text(cap, encoding="utf-8")
        print(f"  ✓ post{idx}: {jpg.name} + {mp4.name}")

    print(f"\n✅ 미리보기 렌더 완료 → {out.relative_to(ROOT)}/")

    # 컨테이너/로컬에서 아티팩트 다운로드가 막히는 경우 대비:
    # 추적되는 docs/worldcup_preview/ 로 jpg + 커버리지 json 복사 → 워크플로우가 커밋
    # → git pull 로 확인 가능. (mp4 는 용량 커서 jpg 만)
    import shutil
    pub = ROOT / "docs" / "worldcup_preview"
    if pub.exists():
        shutil.rmtree(pub)
    pub.mkdir(parents=True, exist_ok=True)
    for f in sorted(out.glob("*.jpg")):
        shutil.copy(f, pub / f.name)
    # 커버리지 요약 json
    (pub / "_coverage.json").write_text(json.dumps({
        "photo_ok": photo_ok, "photo_none": photo_no,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    # idol_photos attribution 도 복사 (어떤 라이선스/저작자인지)
    attr_src = ROOT / "output_enter" / "idol_photos" / "_attribution.json"
    if attr_src.exists():
        shutil.copy(attr_src, pub / "_attribution.json")
    print(f"📋 docs/worldcup_preview/ 에 jpg + 커버리지 복사 (커밋 대상)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
