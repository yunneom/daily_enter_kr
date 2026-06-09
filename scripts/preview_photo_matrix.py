"""
모든 주제 매트릭스 미리보기 — topic_registry 의 각 토픽을 해당 style 로 빌드
→ Cloudinary 업로드 → Step Summary + Discord 알림.

style="photo"  → Unsplash 사진 매트릭스
style="drawing" → 이모지 + 3D 카드 드롭섀도우

실행: GitHub Actions workflow_dispatch (preview_matrix.yml)
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from topic_registry import TOPICS
from make_photo_matrix import make_photo_matrix
from make_premium_matrix import make_premium_matrix
from post_instagram import upload_image
from notify import notify_discord


BRAND = "@daily_enter_kr · 당신의 조합은? 댓글로 ⬇️"
OUTPUT_DIR = ROOT / "output_enter" / "preview"


def build_one(topic_id: str, topic: dict) -> Path:
    out_path = OUTPUT_DIR / f"{topic_id}.jpg"
    common_args = dict(
        title=topic["title"],
        highlight=topic["highlight"],
        rule_hint=topic["rule_hint"],
        col_headers=topic["col_headers"],
        row_prices=topic["row_prices"],
        cells=topic["cells"],
        output_path=out_path,
        brand=BRAND,
    )
    if topic["style"] == "photo":
        make_photo_matrix(**common_args)
    else:
        make_premium_matrix(**common_args)
    return out_path


def main() -> int:
    print(f"📸 {len(TOPICS)}개 토픽 매트릭스 빌드")
    if not os.environ.get("UNSPLASH_ACCESS_KEY"):
        print("⚠️  UNSPLASH_ACCESS_KEY 미설정 — photo 토픽은 폴백 단색")

    results = []  # (topic_id, title, style, url 또는 None)
    for topic_id, topic in TOPICS.items():
        print(f"\n--- {topic_id}: {topic['title']} ({topic['style']}) ---")
        try:
            local = build_one(topic_id, topic)
            print(f"  ✓ 빌드: {local.name}")
        except Exception as e:
            print(f"  ❌ 빌드 실패: {e}")
            results.append((topic_id, topic["title"], topic["style"], None))
            continue

        try:
            url = upload_image(local)
            print(f"  ✓ 업로드: {url}")
            results.append((topic_id, topic["title"], topic["style"], url))
        except Exception as e:
            print(f"  ❌ Cloudinary 업로드 실패: {e}")
            results.append((topic_id, topic["title"], topic["style"], None))

    # Step Summary — 클릭 가능한 링크 목록
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("# 🖼 매트릭스 미리보기\n\n")
            f.write("| ID | 제목 | 스타일 | URL |\n|---|---|---|---|\n")
            for tid, title, style, url in results:
                if url:
                    f.write(f"| `{tid}` | {title} | {style} | [열기]({url}) |\n")
                else:
                    f.write(f"| `{tid}` | {title} | {style} | ❌ 실패 |\n")

    # Discord
    ok_lines = [f"• `{tid}` ({style}): {url}" for tid, _, style, url in results if url]
    fail_lines = [f"• `{tid}` ❌" for tid, _, _, url in results if not url]
    notify_discord(
        "🖼 **매트릭스 미리보기 준비됨**\n"
        + ("성공:\n" + "\n".join(ok_lines) + "\n" if ok_lines else "")
        + ("실패:\n" + "\n".join(fail_lines) if fail_lines else ""),
        username="daily_enter_kr preview",
    )

    # 최소 1개 성공해야 OK
    return 0 if any(url for _, _, _, url in results) else 1


if __name__ == "__main__":
    sys.exit(main())
