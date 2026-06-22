"""
5개 안전 대안 토픽 빠른 샘플 — 외모 호불호 우회용 viral matrix 들.
"""

import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from make_premium_matrix import make_premium_matrix

BRAND = "👥 친구 소환 → 조합 대결! · 📲 스토리 공유 · @daily_enter_kr"
OUT = Path("output_enter/publish")

ALTERNATIVES = {
    "boyfriend_outfit_love_hate": {
        "title": "여친이 환장 vs 극혐하는 남친 옷차림",
        "highlight": "남친 옷차림",
        "rule_hint": "각 강도 1개씩 골라 합 1만원 — 당신의 픽?",
        "col_headers": ["환장 💖", "보통 🙂", "극혐 ❌"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            [
                {"emoji": "🧥", "label": "롱 트렌치 코트"},
                {"emoji": "👕", "label": "단정 셔츠"},
                {"emoji": "👖", "label": "통넓은 츄리닝"},
            ],
            [
                {"emoji": "🧢", "label": "후드 + 볼캡"},
                {"emoji": "👔", "label": "정장 풀세트"},
                {"emoji": "🩴", "label": "쪼리 + 양말"},
            ],
            [
                {"emoji": "🧶", "label": "니트 카디건"},
                {"emoji": "🦺", "label": "베이직 티"},
                {"emoji": "👘", "label": "전신 호피무늬"},
            ],
        ],
        "auto_comment": "💬 환장 옷차림 하나만 꼽으면? 본인 픽 댓글 ⬇️",
    },

    "date_course_pick_10k": {
        "title": "여친이 좋아 vs 헤어질 데이트 코스",
        "highlight": "데이트 코스",
        "rule_hint": "각 강도 1개씩 골라 합 1만원 — 당신의 픽?",
        "col_headers": ["좋아 💖", "그저 🙂", "헤어져 ❌"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            [
                {"emoji": "🍣", "label": "오마카세"},
                {"emoji": "🍝", "label": "동네 양식당"},
                {"emoji": "🍜", "label": "PC방 컵라면"},
            ],
            [
                {"emoji": "🌸", "label": "벚꽃길 산책"},
                {"emoji": "🎬", "label": "심야 영화"},
                {"emoji": "🎮", "label": "롤 듀오 9시간"},
            ],
            [
                {"emoji": "🎡", "label": "놀이공원"},
                {"emoji": "☕", "label": "카페 투어"},
                {"emoji": "🏠", "label": "그냥 우리집"},
            ],
        ],
        "auto_comment": "💬 헤어질 코스 1개만 꼽으면? 본인 픽 댓글 ⬇️",
    },

    "instagram_style_love_hate": {
        "title": "남친이 환장 vs 극혐하는 여친 인스타",
        "highlight": "여친 인스타",
        "rule_hint": "각 강도 1개씩 골라 합 1만원 — 당신의 픽?",
        "col_headers": ["환장 💖", "보통 🙂", "극혐 ❌"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            [
                {"emoji": "🍱", "label": "맛집 코스 후기"},
                {"emoji": "📸", "label": "감성 풍경샷"},
                {"emoji": "🤳", "label": "거울셀카 매일"},
            ],
            [
                {"emoji": "🏋️", "label": "운동 인증샷"},
                {"emoji": "🌅", "label": "여행지 사진"},
                {"emoji": "💼", "label": "명품 자랑 도배"},
            ],
            [
                {"emoji": "🐶", "label": "반려동물"},
                {"emoji": "✍️", "label": "긴 일기글"},
                {"emoji": "💔", "label": "전남친 떡밥"},
            ],
        ],
        "auto_comment": "💬 극혐 인스타 1개만 꼽으면? 본인 픽 댓글 ⬇️",
    },

    "company_perks_love_hate": {
        "title": "MZ가 환장 vs 극혐하는 회사 복지",
        "highlight": "회사 복지",
        "rule_hint": "각 강도 1개씩 골라 합 1만원 — 당신의 픽?",
        "col_headers": ["환장 💖", "보통 🙂", "극혐 ❌"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            [
                {"emoji": "🏖️", "label": "주 4일제"},
                {"emoji": "💰", "label": "연 4회 보너스"},
                {"emoji": "🍺", "label": "강제 회식 월 2회"},
            ],
            [
                {"emoji": "🏠", "label": "재택근무"},
                {"emoji": "🚇", "label": "교통비 지원"},
                {"emoji": "📞", "label": "퇴근 후 카톡"},
            ],
            [
                {"emoji": "🍱", "label": "점심 무료"},
                {"emoji": "💻", "label": "장비 최신화"},
                {"emoji": "👔", "label": "정장 의무"},
            ],
        ],
        "auto_comment": "💬 극혐 복지 1개만 꼽으면? 본인 픽 댓글 ⬇️ 회사 비밀 ㄴㄴ",
    },
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for tid, t in ALTERNATIVES.items():
        out = OUT / f"alt_{tid}.jpg"
        make_premium_matrix(
            title=t["title"], highlight=t["highlight"],
            rule_hint=t["rule_hint"],
            col_headers=t["col_headers"], row_prices=t["row_prices"],
            cells=t["cells"], output_path=out, brand=BRAND,
        )
        print(f"  ✓ {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
