"""
32강 대진표 캐러셀 게시 — 상반부·하반부 2장을 IG 피드 캐러셀로 + 자동 댓글.

[흐름]
1. make_bracket_half 로 top/bottom jpg 렌더 (vote_note 동적)
2. Cloudinary 업로드 → 2 URL
3. post_carousel (스와이프 2장)
4. 자동 댓글 (현재 진행 라운드 안내)
5. ledger 기록 (topic_id=worldcup_bracket)

[사용]
python scripts/worldcup_post_bracket.py
(IG/Cloudinary secret 필요. 현재 진행 라운드는 bracket.current_round 로 자동 판단)
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from make_worldcup_bracket_card import make_bracket_full  # noqa: E402
from post_instagram import InstagramPublisher, upload_image  # noqa: E402
import post_ledger  # noqa: E402
from notify import notify_discord  # noqa: E402


# 현재 진행 라운드별 투표 안내 (대진표 카드 하단 + 캡션)
ROUND_VOTE_NOTE = {
    "R32": "🔴 32강 투표 진행 중 — 목요일까지! 프로필에서 참여",
    "R16": "🔴 16강 투표 진행 중 — 주말 내내! 프로필에서 참여",
}


def build_caption(current_round: str) -> str:
    note = {
        "R32": "🔴 32강 투표 진행 중! (~6/25 목)",
        "R16": "🔴 16강 투표 진행 중! (주말 내내)",
    }.get(current_round, "🔴 투표 진행 중!")
    return "\n".join([
        "🏆 걸그룹 월드컵 32강 대진표",
        "",
        "좌 16명 / 우 16명 → 중앙 결승까지 한 눈에!",
        "숫자 = 브랜드평판 시드순위",
        "(TOP1-4 분산 → 빅매치는 결승까지 안 만남)",
        "",
        note,
        "💬 각 매치 게시글에서 1·2·3·4 번호로 투표",
        "🔔 팔로우 + 알림 ON → 매 라운드 자동 안내",
        "👯 친구 소환 → 우승 예측 대결",
        "",
        "📊 출처: 한국기업평판연구소 2026.6.21",
        "",
        "#걸그룹월드컵 #대진표 #월드컵토너먼트 #케이팝 #kpop "
        "#아이돌투표 #장원영 #카리나 #제니 #로제 #안유진 #윈터 "
        "#밸런스게임 #카드뉴스 #릴스 #reels",
    ])


def main():
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and
            os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    cur = bracket.get("current_round", "R32")
    vote_note = ROUND_VOTE_NOTE.get(cur, "🔴 투표 진행 중 — 프로필에서 참여!")

    out_dir = ROOT / "output_enter" / "publish" / "worldcup_bracket"
    out_dir.mkdir(parents=True, exist_ok=True)
    jpg = out_dir / "bracket_full.jpg"
    make_bracket_full(bracket, jpg, vote_note=vote_note)
    url = upload_image(jpg)
    print(f"  ✓ bracket: {url}")

    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1

    caption = build_caption(cur)
    media_id = publisher.post_single_image(url, caption)
    print(f"✅ 대진표 게시: {media_id}")

    # 자동 댓글
    time.sleep(30)
    try:
        comment = (
            "💬 각 매치는 별도 게시글에서 1·2·3·4 번호로 투표!\n"
            "🔔 팔로우 + 알림 ON → 16강·8강·결승까지 자동 안내\n"
            "🏆 누가 우승할까요? 예측 댓글 ⬇️"
        )
        cid = publisher.post_comment(media_id, comment)
        print(f"  💬 댓글: {cid}")
    except Exception as e:
        print(f"  ⚠️  댓글 실패 (비치명): {e}")

    post_ledger.record_results([{
        "ok": True, "topic_id": "worldcup_bracket",
        "title": "걸그룹 월드컵 32강 대진표", "style": "worldcup_bracket",
        "seed": None, "media_id": media_id, "youtube_id": None,
        "threads_id": None, "bgm": None,
    }])
    notify_discord(
        f"🏆 **걸그룹 월드컵 대진표 게시 완료** (캐러셀 2장)\nMedia: `{media_id}`",
        username="daily_enter_kr worldcup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
