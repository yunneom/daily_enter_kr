"""
월드컵 라운드 결과 발표 카드 게시 — tally 완료 후 진출자 카드를 IG+YT 게시.

사용:
  python scripts/worldcup_announce.py R32   # 32강 결과 (16명 진출 발표)
  python scripts/worldcup_announce.py R16   # 16강 결과 (8명)
  python scripts/worldcup_announce.py R8    # 8강 결과 (4명 → 4강)
  python scripts/worldcup_announce.py R4    # 4강 결과 (결승+3·4위전 라인업)
  python scripts/worldcup_announce.py R1    # 🏆 우승 발표 (1·2·3위)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from make_worldcup_announce_card import (  # noqa: E402
    make_round_announce_card, make_podium_card,
)
from make_worldcup_match_video import make_worldcup_match_video  # sparkle motion 재사용
from post_instagram import InstagramPublisher, upload_video  # noqa: E402
import post_youtube  # noqa: E402
import post_ledger  # noqa: E402
from notify import notify_discord  # noqa: E402


KST = timezone(timedelta(hours=9))

# 다음 라운드 시각 (캡션에 안내) — orchestrator SCHEDULE 과 일치 유지
NEXT_PUBLISH_HINT = {
    "R32": "6/26(금) 21:00 KST — 16강 4경기 (주말 내내 투표!)",
    "R16": "6/29(월) 21:00 KST — 8강 2경기",
    "R8":  "7/1(수) 21:00 KST — 4강",
    "R4":  "7/3(금) 21:00 KST — 결승전 + 3·4위전",
    "R2":  "7/5(일) 12:30 KST — 🏆 우승 발표",
}


def gather_round_winners(bracket: dict, round_key: str) -> list:
    """라운드의 모든 매치 winners 추출."""
    matches = bracket["rounds"][round_key].get("matches", [])
    out = []
    for m in matches:
        w = m.get("winner")
        if w:
            out.append(w)
    return out


def gather_final_results(bracket: dict) -> tuple:
    """R2 의 결승+3·4위전 결과에서 1·2·3위 추출."""
    r2 = bracket["rounds"].get("R2", {})
    matches = r2.get("matches", [])
    # type 으로 구분 (build_finals 가 type 채움)
    final = next((m for m in matches if m.get("type") == "final"), None)
    third = next((m for m in matches if m.get("type") == "third_place"), None)
    if not final or not third:
        return None, None, None
    winner = final.get("winner")
    loser = final["b"] if winner == final["a"] else final["a"]
    third_winner = third.get("winner")
    return winner, loser, third_winner


def build_announce_caption(round_key: str, winners: list, bracket: dict) -> str:
    """결과 발표 캡션 — 진출자 + 다음 라운드 안내 (강조)."""
    next_hint = NEXT_PUBLISH_HINT.get(round_key, "")
    label = {
        "R32": "🏆 32강 결과 — 16강 진출 16명!",
        "R16": "🏆 16강 결과 — 8강 진출 8명!",
        "R8":  "🏆 8강 결과 — 4강 진출 4명!",
        "R4":  "🏆 4강 결과 — 결승전·3·4위전 라인업!",
    }.get(round_key, f"🏆 {round_key} 결과")
    lines = [label, ""]
    for i, w in enumerate(winners, 1):
        lines.append(f"  {i}. {w['member']} ({w['group']})")
    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"⏰ 다음 라운드",
        f"   {next_hint}",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🔔 팔로우 + 알림 ON → 자동 알림",
        "💬 누가 우승할지 댓글로 예측 ⬇️",
        "👯 친구 소환 → 예측 대결",
        "",
        "📊 출처: 한국기업평판연구소 2026.6.21",
        "",
        "#걸그룹월드컵 #월드컵토너먼트 #케이팝 #kpop "
        "#아이돌투표 #밸런스게임 #카드뉴스 #릴스 #reels",
    ]
    return "\n".join(lines)


def build_announce_comment(round_key: str, winners: list) -> str:
    """결과 발표 자동 댓글 — 진출자 일부 + 다음 라운드 명시."""
    next_hint = NEXT_PUBLISH_HINT.get(round_key, "")
    # 진출자 첫 5명만 댓글에 표시 (가독성)
    preview = winners[:5] if len(winners) > 5 else winners
    lines = [f"🏆 {round_key} 결과 — 진출자:"]
    for w in preview:
        lines.append(f"  · {w['member']} ({w['group']})")
    if len(winners) > 5:
        lines.append(f"  · 외 {len(winners) - 5}명")
    lines += [
        "",
        f"⏰ 다음 라운드: {next_hint}",
        "🔔 팔로우 + 알림 ON 으로 놓치지 마세요!",
    ]
    return "\n".join(lines)


def build_podium_caption(winner, second, third) -> str:
    """우승 발표 캡션."""
    lines = [
        "🏆 걸그룹 월드컵 최종 결과",
        "",
        f"🥇 1위: {winner['member']} ({winner['group']})",
        f"🥈 2위: {second['member']} ({second['group']})",
        f"🥉 3위: {third['member']} ({third['group']})",
        "",
        "🙌 우승 축하 댓글 ⬇️",
        "팔로우 + 알림 ON → 다음 시즌 (보이그룹 월드컵 예정)",
        "",
        "📊 출처: 한국기업평판연구소 2026.6.21",
        "",
        "#걸그룹월드컵 #월드컵토너먼트 #케이팝 #kpop "
        f"#{winner['group']} #{winner['member']} "
        "#아이돌투표 #밸런스게임 #카드뉴스 #릴스 #reels",
    ]
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("usage: worldcup_announce.py R32|R16|R8|R4|R1")
        return 1
    round_key = sys.argv[1]

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and
            os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    bracket_path = ROOT / "data" / "worldcup_bracket.json"
    bracket = json.loads(bracket_path.read_text(encoding="utf-8"))
    out_dir = ROOT / "output_enter" / "publish" / f"worldcup_{round_key.lower()}_announce"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 카드 + caption 생성
    if round_key == "R1":
        winner, second, third = gather_final_results(bracket)
        if not winner:
            print("❌ R2 결승 결과 없음")
            return 1
        jpg = out_dir / "podium.jpg"
        make_podium_card(winner, second, third, jpg)
        caption = build_podium_caption(winner, second, third)
        comment = "🏆 최종 우승 축하 댓글로 ⬇️"
    else:
        winners = gather_round_winners(bracket, round_key)
        if not winners:
            print(f"❌ {round_key} winners 없음 — tally 먼저")
            return 1
        cols = {16: 4, 8: 4, 4: 2, 2: 2}.get(len(winners), 4)
        jpg = out_dir / f"{round_key.lower()}_winners.jpg"
        label_map = {
            "R32": ("32강 → 16강", f"🏆 16강 진출 {len(winners)}명!"),
            "R16": ("16강 → 8강", f"🏆 8강 진출 {len(winners)}명!"),
            "R8":  ("8강 → 4강", f"🏆 4강 진출 {len(winners)}명!"),
            "R4":  ("4강 → 결승", f"🏆 결승 라인업 {len(winners)}명!"),
        }
        round_lbl, title = label_map.get(round_key, (round_key, "🏆 진출자"))
        next_hint = NEXT_PUBLISH_HINT.get(round_key, "")
        make_round_announce_card(
            round_label=round_lbl, title=title,
            sub=f"여러분의 픽이 다음 라운드로!",
            members=winners, output_path=jpg, cols=cols,
            next_schedule=next_hint)  # ← 하단 강조 박스에 표시
        caption = build_announce_caption(round_key, winners, bracket)
        comment = build_announce_comment(round_key, winners)

    # 정적 jpg → sparkle motion mp4 (월드컵 매치와 같은 톤)
    bgm = ROOT / "assets" / "bgm" / "daily_enter_theme_c.mp3"
    mp4 = out_dir / "announce.mp4"
    make_worldcup_match_video(card_jpg=jpg, output_path=mp4,
                              duration=18.0,
                              bgm_path=bgm if bgm.exists() else None,
                              sparkle_count=10)
    print(f"  ✓ announce mp4: {mp4} ({mp4.stat().st_size//1024}KB)")

    # 게시
    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1

    video_url = upload_video(mp4)
    media_id = publisher.post_reel(video_url=video_url, caption=caption,
                                    cover_url=None, share_to_feed=True)
    print(f"  ✓ IG: {media_id}")
    if comment:
        time.sleep(30)
        try:
            cid = publisher.post_comment(media_id, comment)
            print(f"  💬 댓글: {cid}")
        except Exception as e:
            print(f"  ⚠️  댓글 실패 (비치명): {e}")

    yt_id = None
    if post_youtube.is_configured():
        try:
            yt_title = caption.split("\n")[0][:100] + " #Shorts"
            yt_id = post_youtube.upload_short(
                mp4, yt_title, caption, tags=[], category_id="24")
            print(f"  ✓ YT: https://youtu.be/{yt_id}" if yt_id else "  ⚠️ YT 실패")
        except Exception as e:
            print(f"  ⚠️  YT 실패 (비치명): {e}")

    post_ledger.record_results([{
        "ok": True,
        "topic_id": f"worldcup_announce_{round_key.lower()}",
        "title": f"걸그룹 월드컵 {round_key} 결과",
        "style": "worldcup_announce",
        "seed": None,
        "media_id": media_id,
        "youtube_id": yt_id,
        "threads_id": None,
        "bgm": "daily_enter_theme_c.mp3",
    }])

    notify_discord(
        f"🏆 **걸그룹 월드컵 {round_key} 결과 발표 완료**\n"
        f"진출자 {len(winners) if round_key != 'R1' else 3}명 / "
        f"다음 라운드: {NEXT_PUBLISH_HINT.get(round_key, '—')}",
        username="daily_enter_kr worldcup")
    print(f"✅ {round_key} 결과 발표 게시 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
