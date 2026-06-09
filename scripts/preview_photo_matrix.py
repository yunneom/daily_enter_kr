"""
사진 매트릭스 1회성 미리보기 — Unsplash 사진으로 'C 주말' 매트릭스 빌드
→ Cloudinary 업로드 → Discord 알림 (DISCORD_WEBHOOK_URL 있을 때).

실행: GitHub Actions workflow_dispatch (preview_matrix.yml)
필요 시크릿: UNSPLASH_ACCESS_KEY, CLOUDINARY_*, (선택) DISCORD_WEBHOOK_URL
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


# 5만원 = 1만/2만/3만 위→아래 고→저. 합 5만원 조합: (3,1,1) / (2,2,1) / (1,3,1) ...
# 라벨은 현실 시세 기준. 1만원 tier 는 budget 인상 위해 살짝 박하게.
TITLE = "5만원으로 주말 보내기"
HIGHLIGHT = "5만원"
RULE = "각 섹터별 1개씩 골라 합 5만원 만들기"
COL_HEADERS = ["식사", "액티비티", "한잔"]
ROW_PRICES = ["3만원", "2만원", "1만원"]

# 각 셀은 photo_queries 리스트 — 첫 성공한 쿼리 사용 (Unsplash niche 0결과 회피)
CELLS = [
    # ─── 3만원 (premium) ───
    [
        {
            "photo_queries": ["korean fine dining", "japanese kaiseki dinner",
                              "sashimi platter dark", "elegant restaurant plate"],
            "label": "일식당 정식",
        },
        {
            "photo_queries": ["han river picnic seoul", "outdoor picnic blanket sunset",
                              "park picnic basket"],
            "label": "한강 피크닉",
        },
        {
            "photo_queries": ["cocktail bar moody", "wine bar interior",
                              "speakeasy cocktail"],
            "label": "칵테일 바",
        },
    ],
    # ─── 2만원 (mid) ───
    [
        {
            "photo_queries": ["korean restaurant table", "bibimbap meal",
                              "korean bbq table", "comfort food meal"],
            "label": "한식당 정식",
        },
        {
            "photo_queries": ["movie theater seats", "cinema interior",
                              "popcorn cinema dark"],
            "label": "영화관",
        },
        {
            "photo_queries": ["draft beer pub interior", "craft beer glass bar",
                              "pub friends night"],
            "label": "동네 호프",
        },
    ],
    # ─── 1만원 (budget) ───
    [
        {
            "photo_queries": ["instant cup noodles bowl", "korean convenience store food",
                              "ramen noodles"],
            "label": "컵라면 + 김밥",
        },
        {
            "photo_queries": ["computer cafe pc bang", "internet cafe gaming",
                              "neon arcade dark"],
            "label": "PC방 2시간",
        },
        {
            "photo_queries": ["convenience store beer can night",
                              "korean convenience store night neon",
                              "beer can street"],
            "label": "편의점 캔맥",
        },
    ],
]

BRAND = "@daily_enter_kr · 당신의 조합은? 댓글로 ⬇️"

OUTPUT = ROOT / "output_enter" / "preview" / "C_weekend_photo.jpg"


def main():
    print(f"📸 사진 매트릭스 빌드: {TITLE}")
    if not os.environ.get("UNSPLASH_ACCESS_KEY"):
        print("⚠️  UNSPLASH_ACCESS_KEY 미설정 — 폴백 단색 셀")

    make_photo_matrix(
        title=TITLE, highlight=HIGHLIGHT, rule_hint=RULE,
        col_headers=COL_HEADERS, row_prices=ROW_PRICES,
        cells=CELLS, output_path=OUTPUT, brand=BRAND,
    )
    print(f"✓ 빌드 완료: {OUTPUT}")

    try:
        url = upload_image(OUTPUT)
        print(f"✓ Cloudinary 업로드: {url}")
        # 워크플로우 step summary 에도 노출 (Discord 안 와도 사용자가 GitHub 에서 보게)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a") as f:
                f.write(f"## 🖼 미리보기 URL\n\n[브라우저에서 열기]({url})\n\n주제: {TITLE}\n")
    except Exception as e:
        print(f"❌ Cloudinary 업로드 실패: {e}")
        return 1

    sent = notify_discord(
        f"🖼 **사진 매트릭스 미리보기 준비됨**\n"
        f"주제: {TITLE}\n"
        f"브라우저에서 열기 → {url}",
        username="daily_enter_kr preview",
    )
    print(f"✓ Discord 알림: {'전송됨' if sent else '⏭️ 스킵 (DISCORD_WEBHOOK_URL 없음)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
