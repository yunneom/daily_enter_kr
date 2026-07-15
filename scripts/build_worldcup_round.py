"""
월드컵 32강 — 8게시글 일괄 빌드 (jpg 카드 + mp4 + 캡션·댓글 텍스트).

[입력] data/worldcup_bracket.json (이미 빌드됨)
[출력] output_enter/publish/worldcup_r32/post_{01-08}.{jpg,mp4,caption.txt,comment.txt}

[사용]
python scripts/build_worldcup_round.py R32
python scripts/build_worldcup_round.py R16  (다음 라운드)
...
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from make_worldcup_match_card import make_worldcup_match_card  # noqa: E402
from make_worldcup_match_video import (  # noqa: E402
    make_worldcup_match_video,
    build_worldcup_caption, build_worldcup_auto_comment,
    build_worldcup_solo_caption, build_worldcup_solo_comment,
)


ROUND_LABELS = {
    "R32": "32강", "R16": "16강", "R8": "8강",
    "R4": "4강", "R2": "결승전·3위전", "R1": "우승 발표",
}

# R2 솔로 게시 (1매치 1게시) — post.type → 카드/캡션 타이틀
SOLO_LABELS = {"final_solo": "결승전", "third_place_solo": "3·4위전"}


def main():
    # ── 멤버 이름 무결성 게이트 — 브래킷 오타 시 카드 빌드 전 중단 ──
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_member_names import gate as _names_gate
    _names_gate()

    if len(sys.argv) < 2:
        round_key = "R32"
    else:
        round_key = sys.argv[1]

    bracket_path = ROOT / "data" / "worldcup_bracket.json"
    bracket = json.loads(bracket_path.read_text(encoding="utf-8"))
    if round_key not in bracket["rounds"]:
        print(f"❌ {round_key} 라운드가 bracket 에 없음. 이전 라운드 집계 먼저 필요.")
        return 1
    rnd = bracket["rounds"][round_key]
    posts = rnd.get("posts", [])
    if not posts:
        print(f"❌ {round_key} posts 비어있음")
        return 1

    out_dir = ROOT / "output_enter" / "publish" / f"worldcup_{round_key.lower()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    bgm = ROOT / "assets" / "bgm" / "daily_enter_theme_c.mp3"
    if not bgm.exists():
        print(f"⚠️  BGM {bgm} 없음 — 무음 영상으로 빌드")
        bgm = None
    round_label = ROUND_LABELS.get(round_key, round_key)
    source_date = bracket.get("source", "").split()[-1] if bracket.get("source") else "2026.6.21"

    n = len(posts)
    print(f"=== {round_label} {n}게시글 빌드 시작 ===")
    for p in posts:
        idx = p["post_idx"] + 1
        jpg = out_dir / f"post_{idx:02d}.jpg"
        mp4 = out_dir / f"post_{idx:02d}.mp4"
        cap = out_dir / f"post_{idx:02d}.caption.txt"
        com = out_dir / f"post_{idx:02d}.comment.txt"

        ptype = p.get("type", "") or ""
        solo = ptype.endswith("_solo")           # R2 결승전/3·4위전 — 1매치 1게시
        label = SOLO_LABELS.get(ptype, round_label)

        # 1. jpg 카드 (솔로는 post_type 전달 → 1매치 중앙 레이아웃 + 2지선다)
        make_worldcup_match_card(
            round_label=label, post_index=idx, post_total=n,
            match1=p["match1"], match2=p["match2"], output_path=jpg,
            source_note=f"출처: 한국기업평판연구소 {source_date}",
            post_type=ptype,
        )
        # 2. mp4 (sparkle motion + BGM)
        make_worldcup_match_video(
            card_jpg=jpg, output_path=mp4, duration=18.0, bgm_path=bgm)
        # 3. 캡션 / 댓글 텍스트 저장 (자동 게시 워크플로우가 읽음)
        if solo:
            cap.write_text(build_worldcup_solo_caption(
                label, idx, n, p["match1"],
                source_date=source_date), encoding="utf-8")
            com.write_text(build_worldcup_solo_comment(
                p["match1"]), encoding="utf-8")
        else:
            cap.write_text(build_worldcup_caption(
                round_label, idx, n, p["match1"], p["match2"],
                source_date=source_date), encoding="utf-8")
            com.write_text(build_worldcup_auto_comment(
                p["match1"], p["match2"]), encoding="utf-8")

        m1 = p["match1"]; m2 = p["match2"]
        if solo:
            print(f"  ✓ post_{idx:02d} ({label}): "
                  f"{m1['a']['member']}vs{m1['b']['member']}  "
                  f"({jpg.stat().st_size//1024}KB jpg, {mp4.stat().st_size//1024}KB mp4)")
        else:
            print(f"  ✓ post_{idx:02d}: "
                  f"{m1['a']['member']}vs{m1['b']['member']} / "
                  f"{m2['a']['member']}vs{m2['b']['member']}  "
                  f"({jpg.stat().st_size//1024}KB jpg, {mp4.stat().st_size//1024}KB mp4)")
    print(f"\n✅ {round_label} 빌드 완료 — {out_dir.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
