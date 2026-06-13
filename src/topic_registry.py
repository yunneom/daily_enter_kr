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

    # 3) 걸그룹 올스타 — 엠블럼 카드 + 실명 (흰 배경 premium)
    "girlgroup_real_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 걸그룹 올스타 만들기",
        "highlight": "걸그룹",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 당신의 픽은?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🎤", "name": "에스파 카리나"},
                {"role_emoji": "💃", "name": "ITZY 채령"},
                {"role_emoji": "✨", "name": "뉴진스 민지"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "IVE 유진"},
                {"role_emoji": "💃", "name": "르세라핌 카즈하"},
                {"role_emoji": "✨", "name": "에스파 윈터"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "뉴진스 다니엘"},
                {"role_emoji": "💃", "name": "ITZY 리아"},
                {"role_emoji": "✨", "name": "IVE 레이"},
            ],
        ],
    },

    # 5) 축구 드림팀 — 유니폼+등번호 (축구장 배경)
    "soccer_dream_10k": {
        "style": "emblem",
        "background_style": "soccer",
        "title": "만원으로 축구 드림팀 만들기",
        "highlight": "드림팀",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 당신의 베스트일레븐은?",
        "col_headers": ["공격수", "미드필더", "수비수"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원 (jersey color 는 팀 비특정 — 색만)
            [
                {"jersey": {"color": (135, 206, 250), "number": 10}, "name": "메시", "subtitle": "ARG"},
                {"jersey": {"color": (30, 100, 200), "number": 17}, "name": "데브라이너", "subtitle": "BEL"},
                {"jersey": {"color": (230, 130, 30), "number": 4}, "name": "반다이크", "subtitle": "NED"},
            ],
            # 3천원
            [
                {"jersey": {"color": (40, 60, 140), "number": 10}, "name": "음바페", "subtitle": "FRA"},
                {"jersey": {"color": (200, 30, 50), "number": 10}, "name": "모드리치", "subtitle": "CRO"},
                {"jersey": {"color": (220, 40, 40), "number": 3}, "name": "김민재", "subtitle": "KOR"},
            ],
            # 2천원
            [
                {"jersey": {"color": (220, 40, 40), "number": 7}, "name": "손흥민", "subtitle": "KOR"},
                {"jersey": {"color": (140, 30, 30), "number": 20}, "name": "베르나르두", "subtitle": "POR"},
                {"jersey": {"color": (230, 200, 40), "number": 5}, "name": "부스케츠", "subtitle": "ESP"},
            ],
        ],
    },

    # 6) 아이돌 올스타 — 그룹별 멤버 1명 (흰 배경)
    "idol_allstar_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 아이돌 올스타 만들기",
        "highlight": "올스타",
        "rule_hint": "각 그룹 1명씩 골라 합 1만원 — 당신의 올스타는?",
        "col_headers": ["뉴진스", "에스파", "IVE"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🐰", "name": "민지"},
                {"role_emoji": "🦋", "name": "카리나"},
                {"role_emoji": "👑", "name": "장원영"},
            ],
            # 3천원
            [
                {"role_emoji": "🐰", "name": "하니"},
                {"role_emoji": "🦋", "name": "윈터"},
                {"role_emoji": "👑", "name": "안유진"},
            ],
            # 2천원
            [
                {"role_emoji": "🐰", "name": "해린"},
                {"role_emoji": "🦋", "name": "닝닝"},
                {"role_emoji": "👑", "name": "리즈"},
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

    # 7) 일시정지 챌린지 — 근육맨 (먹을지 vs 운동)
    "spinner_food_man": {
        "style": "spinner",
        "character_style": "muscle_man",
        "title": "먹을지 vs 운동 갈지",
        "hint": "⏸ 일시정지로 메뉴 골라봐!",
        # 짝수 인덱스 = 잡힘 (운동가기), 홀수 인덱스 = 절대 못 잡음 (음식)
        "options": ["운동가기", "엽떡먹기", "운동가기", "치킨먹기",
                    "운동가기", "소주먹기", "운동가기", "닭발먹기"],
    },

    # 8) 일시정지 챌린지 — 운동복 (눕기 vs 운동)
    "spinner_lazy_woman": {
        "style": "spinner",
        "character_style": "sport_woman",
        "title": "누울지 vs 운동 갈지",
        "hint": "⏸ 일시정지로 운명 골라봐!",
        "options": ["운동가기", "유튜브보기", "운동가기", "낮잠자기",
                    "운동가기", "넷플릭스", "운동가기", "쇼츠보기"],
        "auto_comment": "⏸ 일시정지로 잡혔나요? 결과 댓글로 알려주세요!",
    },

    # 9) 4세대 걸그룹 올스타 — 다양한 그룹 + NMIXX 포함
    "girlgroup_4gen_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 걸그룹 만들기",
        "highlight": "4세대",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 4세대 올스타!",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🎤", "name": "NMIXX 릴리"},
                {"role_emoji": "💃", "name": "ITZY 채령"},
                {"role_emoji": "✨", "name": "NMIXX 설윤"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "에스파 닝닝"},
                {"role_emoji": "💃", "name": "르세라핌 카즈하"},
                {"role_emoji": "✨", "name": "에스파 윈터"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "IVE 리즈"},
                {"role_emoji": "💃", "name": "뉴진스 해린"},
                {"role_emoji": "✨", "name": "IVE 장원영"},
            ],
        ],
        "auto_comment": "🤔 내 픽 댓글로 알려주세요! NMIXX·뉴진스·에스파·IVE·ITZY·르세라핌 다 모였어요 ⬇️",
    },

    # 10) 4세대 보이그룹 올스타
    "boygroup_4gen_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 보이그룹 만들기",
        "highlight": "4세대",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 4세대 보이그룹 올스타!",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🎤", "name": "엔하이픈 정원"},
                {"role_emoji": "💃", "name": "스키즈 필릭스"},
                {"role_emoji": "✨", "name": "엔하이픈 성훈"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "TXT 태현"},
                {"role_emoji": "💃", "name": "RIIZE 앤톤"},
                {"role_emoji": "✨", "name": "RIIZE 박원빈"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "스키즈 승민"},
                {"role_emoji": "💃", "name": "TXT 휴닝카이"},
                {"role_emoji": "✨", "name": "ATEEZ 윤호"},
            ],
        ],
        "auto_comment": "🔥 본인 픽 댓글로 ⬇️ 스키즈·엔하이픈·TXT·RIIZE·ATEEZ 다 모였어요!",
    },
}
