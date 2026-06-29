"""
특정 라운드의 HyperFrames 대진표 릴스만 단독 게시.

[사용]
python scripts/worldcup_post_hf_reel.py R8
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from post_instagram import InstagramPublisher, upload_video  # noqa
import post_ledger  # noqa


def main():
    if len(sys.argv) < 2:
        print("usage: worldcup_post_hf_reel.py <round>  (예: R8)")
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

    out_dir = ROOT / "output_enter" / "publish" / f"worldcup_{round_key.lower()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from make_worldcup_hf_html import generate as gen_hf_html
        from render_hf import render_html_to_mp4

        hf_html = out_dir / "hf_bracket.html"
        gen_hf_html(round_key, hf_html)
        print(f"✓ HF HTML 생성: {hf_html}")

        hf_mp4 = out_dir / "hf_bracket.mp4"
        rc = render_html_to_mp4(hf_html, hf_mp4, duration=6.0, fps=30)
        if rc != 0 or not hf_mp4.exists():
            print(f"❌ HF 렌더 실패 rc={rc}")
            return 1
        print(f"✓ HF MP4: {hf_mp4} ({hf_mp4.stat().st_size // 1024}KB)")

        hf_url = upload_video(hf_mp4)
        print(f"✓ Cloudinary: {hf_url}")

        labels = {"R32": "32강", "R16": "16강", "R8": "8강", "R4": "4강", "R2": "결승"}
        lbl = labels.get(round_key, round_key)
        hf_caption = (
            f"🏆 걸그룹 월드컵 {lbl} 대진표!\n\n"
            "지금 피드에서 각 경기 게시글 찾아서 댓글로 투표! 💬\n"
            "🔔 팔로우 + 알림 ON → 결과 즉시 알림\n\n"
            f"#걸그룹월드컵 #{lbl} #케이팝 #kpop #아이돌투표"
        )
        hf_id = publisher.post_reel(hf_url, hf_caption,
                                    cover_url=None, share_to_feed=True)
        print(f"✅ HF 릴스 게시 완료! {hf_id}")

        post_ledger.record_results([{
            "ok": True,
            "topic_id": f"worldcup_hf_{round_key.lower()}_bracket",
            "title": f"걸그룹 월드컵 {round_key} HF 대진표",
            "style": "worldcup_hf", "seed": None,
            "media_id": hf_id, "youtube_id": None,
            "threads_id": None, "bgm": None,
        }])
        return 0
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
