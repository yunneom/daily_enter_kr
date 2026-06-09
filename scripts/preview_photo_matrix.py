"""
사진 매트릭스 1회성 미리보기 — Unsplash 사진으로 'C 주말' 매트릭스 빌드
→ Cloudinary 업로드 → Discord 알림으로 URL 전달.

실행: GitHub Actions workflow_dispatch (preview_matrix.yml)
필요 시크릿: UNSPLASH_ACCESS_KEY, CLOUDINARY_*, DISCORD_WEBHOOK_URL
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from make_photo_matrix import make_photo_matrix
from post_instagram import upload_image
from notify import notify_discord


# C — 5만원으로 주말 보내기 (3 카테고리 × 3 가격 위→아래로 고→저)
TITLE = "5만원으로 주말 보내기"
HIGHLIGHT = "5만원"
RULE = "각 섹터별 1개씩 골라 합 5만원 만들기"
COL_HEADERS = ["식사", "액티비티", "한잔"]
ROW_PRICES = ["3만원", "2만원", "1만원"]

CELLS = [
    # 3만원 (top)
    [
        {"photo_query": "omakase sushi fine dining", "label": "오마카세"},
        {"photo_query": "imax movie theater cinema", "label": "IMAX 영화"},
        {"photo_query": "wine dinner restaurant", "label": "와인 다이닝"},
    ],
    # 2만원
    [
        {"photo_query": "burger family meal restaurant", "label": "프차 패밀리세트"},
        {"photo_query": "karaoke room neon korea", "label": "코노 2시간"},
        {"photo_query": "korean pub craft beer", "label": "동네 호프"},
    ],
    # 1만원
    [
        {"photo_query": "instant noodle convenience store", "label": "편의점 라면"},
        {"photo_query": "han river seoul walking", "label": "한강 산책"},
        {"photo_query": "beer can convenience store night", "label": "편의점 맥주"},
    ],
]

BRAND = "@daily_enter_kr · 당신의 조합은? 댓글로 ⬇️"

OUTPUT = ROOT / "output_enter" / "preview" / "C_weekend_photo.jpg"


def main():
    print(f"📸 사진 매트릭스 빌드: {TITLE}")
    if not os.environ.get("UNSPLASH_ACCESS_KEY"):
        print("⚠️  UNSPLASH_ACCESS_KEY 미설정 — 폴백 단색 셀 (의미 없음)")
        notify_discord("⚠️ Matrix preview: UNSPLASH_ACCESS_KEY 미설정으로 사진 없이 빌드됨")

    make_photo_matrix(
        title=TITLE, highlight=HIGHLIGHT, rule_hint=RULE,
        col_headers=COL_HEADERS, row_prices=ROW_PRICES,
        cells=CELLS, output_path=OUTPUT, brand=BRAND,
    )
    print(f"✓ 빌드 완료: {OUTPUT}")

    # Cloudinary 업로드 → URL 받기
    try:
        url = upload_image(OUTPUT)
        print(f"✓ Cloudinary 업로드: {url}")
    except Exception as e:
        print(f"❌ Cloudinary 업로드 실패: {e}")
        notify_discord(f"❌ Matrix preview Cloudinary 실패: {e}")
        return 1

    notify_discord(
        f"🖼 **사진 매트릭스 미리보기 준비됨**\n"
        f"주제: {TITLE}\n"
        f"브라우저에서 열기 → {url}\n\n"
        f"이 톤 OK면 게시 진행, 수정 사항 있으면 알려주세요.",
        username="daily_enter_kr preview",
    )
    print(f"✓ Discord 알림 전송됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
