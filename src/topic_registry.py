"""
주제 레지스트리 — "XX원으로 ~하기" 매트릭스 토픽 정의.

각 토픽은 style + 매트릭스 데이터를 가짐. 사진은 lifestyle/사물/장소 주제,
그림은 추상 주제, 엠블럼은 인물/포지션 카드 (FIFA UT 스타일).
"""

# style: "photo"   → make_photo_matrix (Unsplash 사진)
#        "drawing" → make_premium_matrix (이모지 + 드롭섀도우 3D 카드)
#        "emblem"  → make_emblem_matrix (FIFA 카드 골드/실버/브론즈 + 실명)
TOPICS = {
    # 1) 라이프스타일 — 사진이 어울림
    "weekend_5man": {
        "style": "photo",
        "title": "5만원으로 주말 보내기",
        "highlight": "5만원",
        "rule_hint": "각 섹터별 1개씩 골라 합 5만원 만들기",
        "col_headers": ["식사", "액티비티", "한잔"],
        "row_prices": ["3만원", "2만원", "1만원"],
        "cells": [
            # 3만원 (premium)
            [
                {"photo_queries": ["korean fine dining", "japanese kaiseki dinner",
                                   "sashimi platter dark", "elegant restaurant plate"],
                 "label": "일식당 정식"},
                {"photo_queries": ["han river picnic seoul", "outdoor picnic blanket sunset",
                                   "park picnic basket"],
                 "label": "한강 피크닉"},
                {"photo_queries": ["cocktail bar moody", "wine bar interior",
                                   "speakeasy cocktail"],
                 "label": "칵테일 바"},
            ],
            # 2만원 (mid)
            [
                {"photo_queries": ["korean restaurant table", "bibimbap meal",
                                   "korean bbq table"],
                 "label": "한식당 정식"},
                {"photo_queries": ["movie theater seats", "cinema interior",
                                   "popcorn cinema dark"],
                 "label": "영화관"},
                {"photo_queries": ["draft beer pub interior", "craft beer glass bar",
                                   "pub friends night"],
                 "label": "동네 호프"},
            ],
            # 1만원 (budget)
            [
                {"photo_queries": ["instant cup noodles bowl", "korean convenience store food",
                                   "ramen noodles"],
                 "label": "컵라면 + 김밥"},
                {"photo_queries": ["computer cafe pc bang", "internet cafe gaming",
                                   "neon arcade dark"],
                 "label": "PC방 2시간"},
                {"photo_queries": ["convenience store beer can night",
                                   "korean convenience store night neon",
                                   "beer can street"],
                 "label": "편의점 캔맥"},
            ],
        ],
    },

    # 2) 점심 메뉴 — 사진 (음식)
    "lunch_15k": {
        "style": "photo",
        "title": "만 5천원으로 점심 즐기기",
        "highlight": "만 5천원",
        "rule_hint": "각 섹터별 1개씩 골라 합 1.5만원 만들기",
        "col_headers": ["주식", "사이드", "음료"],
        "row_prices": ["1만원", "5천원", "2천원"],
        "cells": [
            # 1만원
            [
                {"photo_queries": ["sushi platter lunch", "korean lunch set",
                                   "fine lunch plate"],
                 "label": "초밥 세트"},
                {"photo_queries": ["small dessert plate", "fancy salad bowl",
                                   "appetizer plate"],
                 "label": "샐러드 + 디저트"},
                {"photo_queries": ["specialty coffee glass", "iced latte aesthetic",
                                   "cafe latte art"],
                 "label": "스페셜 라떼"},
            ],
            # 5천원
            [
                {"photo_queries": ["kimbap roll", "bibimbap simple", "korean rice bowl"],
                 "label": "분식 한 그릇"},
                {"photo_queries": ["tteokbokki spicy bowl", "korean street food snack",
                                   "fried mandu plate"],
                 "label": "떡볶이 한컵"},
                {"photo_queries": ["bubble tea cup", "iced americano",
                                   "cafe coffee cup"],
                 "label": "버블티"},
            ],
            # 2천원
            [
                {"photo_queries": ["instant noodles bowl", "convenience store food korea",
                                   "cup ramen"],
                 "label": "컵라면"},
                {"photo_queries": ["chocolate bar snack", "potato chips bag",
                                   "snack bag store"],
                 "label": "과자 1개"},
                {"photo_queries": ["water bottle table", "tea bag cup",
                                   "convenience store drink"],
                 "label": "생수 / 캔커피"},
            ],
        ],
    },

    # 3) 걸그룹 꾸리기 v2 — 엠블럼 카드 + 실명 (FIFA UT 스타일)
    "girlgroup_real_10k": {
        "style": "emblem",
        "background_style": "gradient_idol",
        "title": "만원으로 걸그룹 꾸리기",
        "highlight": "만원",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 당신의 픽은?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원 — GOLD 등급
            [
                {"role_emoji": "🎤", "name": "에스파 카리나", "subtitle": "GOLD"},
                {"role_emoji": "💃", "name": "ITZY 채령", "subtitle": "GOLD"},
                {"role_emoji": "✨", "name": "뉴진스 민지", "subtitle": "GOLD"},
            ],
            # 3천원 — SILVER
            [
                {"role_emoji": "🎤", "name": "IVE 유진", "subtitle": "SILVER"},
                {"role_emoji": "💃", "name": "르세라핌 카즈하", "subtitle": "SILVER"},
                {"role_emoji": "✨", "name": "에스파 윈터", "subtitle": "SILVER"},
            ],
            # 2천원 — BRONZE
            [
                {"role_emoji": "🎤", "name": "뉴진스 다니엘", "subtitle": "BRONZE"},
                {"role_emoji": "💃", "name": "ITZY 리아", "subtitle": "BRONZE"},
                {"role_emoji": "✨", "name": "IVE 레이", "subtitle": "BRONZE"},
            ],
        ],
    },

    # 5) 축구 드림팀 꾸리기 — 엠블럼 카드 + 실명 (FIFA UT 스타일)
    "soccer_dream_10k": {
        "style": "emblem",
        "background_style": "soccer",
        "title": "만원으로 축구 드림팀 꾸리기",
        "highlight": "만원",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 당신의 베스트일레븐은?",
        "col_headers": ["공격수", "미드필더", "수비수"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원 — GOLD
            [
                {"role_emoji": "⚽", "name": "메시 #10", "subtitle": "ARG"},
                {"role_emoji": "🎯", "name": "데브라이너 #17", "subtitle": "BEL"},
                {"role_emoji": "🛡", "name": "반다이크 #4", "subtitle": "NED"},
            ],
            # 3천원 — SILVER
            [
                {"role_emoji": "⚽", "name": "음바페 #10", "subtitle": "FRA"},
                {"role_emoji": "🎯", "name": "모드리치 #10", "subtitle": "CRO"},
                {"role_emoji": "🛡", "name": "김민재 #3", "subtitle": "KOR"},
            ],
            # 2천원 — BRONZE
            [
                {"role_emoji": "⚽", "name": "손흥민 #7", "subtitle": "KOR"},
                {"role_emoji": "🎯", "name": "베르나르두 #20", "subtitle": "POR"},
                {"role_emoji": "🛡", "name": "사울리스키 #5", "subtitle": "ESP"},
            ],
        ],
    },

    # 6) 세대별 아이돌 조합 — 엠블럼 카드 + 실명
    "idol_generation_10k": {
        "style": "emblem",
        "background_style": "gradient_dark",
        "title": "만원으로 세대 조합 꾸리기",
        "highlight": "만원",
        "rule_hint": "각 세대 1팀씩 골라 합 1만원 — 인생 아이돌 조합",
        "col_headers": ["2세대", "3세대", "4세대"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원 — GOLD (각 세대 최정상)
            [
                {"role_emoji": "👑", "name": "빅뱅", "subtitle": "2세대 LEGEND"},
                {"role_emoji": "👑", "name": "BTS", "subtitle": "3세대 LEGEND"},
                {"role_emoji": "👑", "name": "뉴진스", "subtitle": "4세대 LEGEND"},
            ],
            # 3천원 — SILVER (각 세대 인기)
            [
                {"role_emoji": "⭐", "name": "소녀시대", "subtitle": "2세대 STAR"},
                {"role_emoji": "⭐", "name": "트와이스", "subtitle": "3세대 STAR"},
                {"role_emoji": "⭐", "name": "IVE", "subtitle": "4세대 STAR"},
            ],
            # 2천원 — BRONZE (각 세대 추억)
            [
                {"role_emoji": "💎", "name": "원더걸스", "subtitle": "2세대 ICON"},
                {"role_emoji": "💎", "name": "EXO", "subtitle": "3세대 ICON"},
                {"role_emoji": "💎", "name": "에스파", "subtitle": "4세대 ICON"},
            ],
        ],
    },

    # 4) 이상형 만들기 — 그림 (추상 속성)
    "idealtype_10k": {
        "style": "drawing",
        "title": "만원으로 이상형 만들기",
        "highlight": "이상형",
        "rule_hint": "각 항목 1개씩 골라 합 1만원 만들기",
        "col_headers": ["외모", "성격", "능력"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"emoji": "✨", "label": "비주얼 만점"},
                {"emoji": "😇", "label": "다정 자상"},
                {"emoji": "🧠", "label": "전문직 고소득"},
            ],
            # 3천원
            [
                {"emoji": "😊", "label": "편안한 인상"},
                {"emoji": "😎", "label": "쿨한 성격"},
                {"emoji": "💼", "label": "안정 직장"},
            ],
            # 2천원
            [
                {"emoji": "🙃", "label": "취향 차이"},
                {"emoji": "😬", "label": "기분파"},
                {"emoji": "🎒", "label": "취준 중"},
            ],
        ],
    },
}
