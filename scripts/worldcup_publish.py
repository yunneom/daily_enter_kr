"""
월드컵 라운드 게시 — 8개(또는 4/2/1) mp4 + 캡션 → IG Reels + YT Shorts 양쪽 게시.

[전제]
build_worldcup_round.py 가 사전 빌드:
  output_enter/publish/worldcup_{round}/post_{NN}.{jpg,mp4,caption.txt,comment.txt}

[흐름]
1. post 별로:
   a. mp4 Cloudinary 업로드 → video_url
   b. IG Reels post (caption 첨부) → media_id
   c. 30s 후 자동 첫 댓글 (comment 텍스트)
   d. YT Shorts 업로드 (같은 mp4) → youtube_id
   e. post_ledger.json 에 topic_id = "worldcup_{round}_{N}" 로 기록
2. 게시글 간 INTER_POST_SLEEP (180초 = 3분) 분산 → 30분 안 8개 분산
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from post_instagram import InstagramPublisher, upload_video  # noqa: E402
import post_youtube  # noqa: E402
import post_ledger  # noqa: E402
from notify import notify_discord  # noqa: E402


INTER_POST_SLEEP = 120  # 2분 간격 — 16분 안 8개 분산 + 봇 패턴 회피
                        # (cron 정시 지연 흡수 + 총 게시 시간 단축. 3분→2분 = 8분 절약)


def main():
    if len(sys.argv) < 2:
        print("usage: worldcup_publish.py R32|R16|R8|R4|R2|R1")
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

    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1
    print(f"✓ IG 토큰 OK: @{health.get('username')}")

    round_dir = ROOT / "output_enter" / "publish" / f"worldcup_{round_key.lower()}"
    if not round_dir.exists():
        print(f"❌ {round_dir} 없음 — build_worldcup_round.py 먼저 실행")
        return 1

    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    posts = bracket["rounds"][round_key].get("posts", [])
    if not posts:
        print(f"❌ {round_key} posts 비어있음")
        return 1

    print(f"\n📣 {round_key} {len(posts)}개 게시 시작 (간격 {INTER_POST_SLEEP}s)")
    results = []
    for i, post in enumerate(posts):
        idx = post["post_idx"] + 1
        mp4 = round_dir / f"post_{idx:02d}.mp4"
        cap_f = round_dir / f"post_{idx:02d}.caption.txt"
        com_f = round_dir / f"post_{idx:02d}.comment.txt"

        if not mp4.exists():
            print(f"  ❌ post #{idx} mp4 없음 — skip")
            continue
        caption = cap_f.read_text(encoding="utf-8") if cap_f.exists() else ""
        auto_comment = com_f.read_text(encoding="utf-8") if com_f.exists() else ""

        if i > 0:
            print(f"\n⏱  {INTER_POST_SLEEP}s 대기 (다음 게시까지)...")
            time.sleep(INTER_POST_SLEEP)

        print(f"\n=== post #{idx} ({round_key}) ===")
        try:
            video_url = upload_video(mp4)
            print(f"  ✓ video: {video_url}")
        except Exception as e:
            print(f"  ❌ Cloudinary 업로드 실패: {e}")
            results.append({"post_idx": idx, "ok": False, "error": str(e)})
            continue

        # IG Reels 게시
        try:
            media_id = publisher.post_reel(
                video_url=video_url, caption=caption,
                cover_url=None, share_to_feed=True)
            print(f"  ✓ IG: {media_id}")
        except Exception as e:
            print(f"  ❌ IG 실패: {e}")
            results.append({"post_idx": idx, "ok": False, "error": str(e)})
            continue

        # 30s 후 자동 댓글
        if auto_comment:
            time.sleep(30)
            try:
                cid = publisher.post_comment(media_id, auto_comment)
                print(f"  💬 IG 댓글: {cid}")
            except Exception as e:
                print(f"  ⚠️  IG 댓글 실패 (비치명): {e}")

        # YT Shorts 업로드 (월드컵은 같은 mp4 양쪽 게시)
        yt_id = None
        if post_youtube.is_configured():
            try:
                # YT 메타는 caption 의 첫 줄 + 해시태그 일부
                first_line = caption.split("\n")[0] if caption else f"걸그룹 월드컵 {round_key}"
                yt_title = f"{first_line} #Shorts"[:100]
                yt_desc = caption  # 동일 사용
                yt_id = post_youtube.upload_short(
                    mp4, yt_title, yt_desc, tags=[],
                    category_id="24")  # Entertainment
                print(f"  ✓ YT: https://youtu.be/{yt_id}" if yt_id else "  ⚠️ YT 실패")
            except Exception as e:
                print(f"  ⚠️  YT 실패 (비치명): {e}")

        # ledger 기록 — topic_id = worldcup_{round}_{idx}
        post_ledger.record_results([{
            "ok": True,
            "topic_id": f"worldcup_{round_key.lower()}_{idx}",
            "title": f"걸그룹 월드컵 {round_key} #{idx}",
            "style": "worldcup_match",
            "seed": None,
            "media_id": media_id,
            "youtube_id": yt_id,
            "threads_id": None,
            "bgm": "daily_enter_theme_c.mp3",
        }])
        results.append({"post_idx": idx, "ok": True, "media_id": media_id, "youtube_id": yt_id})

    ok = sum(1 for r in results if r.get("ok"))
    print(f"\n✅ {round_key} 게시 완료: {ok}/{len(posts)}")
    # Discord 알림
    summary = (f"🏆 **걸그룹 월드컵 {round_key}** 게시 완료\n"
               f"{ok}/{len(posts)} 성공\n"
               f"⏰ 집계 예정: 24h 후\n"
               f"💬 댓글에 1·2·3·4 번호로 투표!")
    notify_discord(summary, username="daily_enter_kr worldcup")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
