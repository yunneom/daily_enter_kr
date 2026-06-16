"""
주제 레지스트리 — "XX원으로 ~하기" 매트릭스 토픽 정의.

각 토픽은 style + 매트릭스 데이터를 가짐. 사진은 lifestyle/사물/장소 주제,
그림은 추상 주제, 엠블럼은 인물/포지션 카드 (FIFA UT 스타일).
"""

# style: "photo"   → make_photo_matrix (Unsplash 사진)
#        "drawing" → make_premium_matrix (이모지 + 드롭섀도우 3D 카드)
#        "emblem"  → make_emblem_matrix (FIFA 카드 골드/실명)
#
# [티어 풀 회전 — 한 토픽에서 여러 콘텐츠]
# 토픽에 `col_pools` (컬럼별 멤버 풀 3개)를 주면, 게시 seed 에 따라 매번
# 다른 멤버 라인업이 생성됨. 예: A티어 메인보컬 풀에 [안유진, 리즈, 카리나, ...]
# → 이번 게시엔 안유진, 다음 게시엔 리즈. 같은 주제로 1개 이상의 콘텐츠 양산.
# 각 컬럼 풀은 S→하위 순서로 나열하고, 행(가격 티어)은 풀에서 연속 인덱스를
# 뽑아 항상 서로 다른 3명이 노출됨.

def cells_from_col_pools(col_pools, n_rows: int, seed: int = 0):
    """컬럼별 풀에서 행(가격티어)마다 서로 다른 멤버를 회전 선택.

    cells[r][c] = col_pools[c][(seed + c + r) % len(pool)]
    - +r : 같은 컬럼 안에서 3행이 연속 인덱스 → 항상 distinct (풀 길이 ≥ n_rows)
    - +c : 컬럼마다 시작 위상차 → 컬럼 간 멤버 겹침 최소화
    - seed 가 게시마다 바뀌므로 라인업 전체가 회전.
    """
    cells = []
    for r in range(n_rows):
        row = []
        for c, pool in enumerate(col_pools):
            member = pool[(seed + c + r) % len(pool)]
            row.append(dict(member))
        cells.append(row)
    return cells


def resolve_topic_cells(topic: dict, seed: int = 0):
    """토픽의 셀을 확정. col_pools 있으면 회전 생성, 없으면 고정 cells 그대로."""
    if topic.get("col_pools"):
        n_rows = len(topic["row_prices"])
        return cells_from_col_pools(topic["col_pools"], n_rows, seed=seed)
    return [[dict(cell) for cell in row] for row in topic["cells"]]


def resolve_pick_pool(topic: dict, seed: int = 0, n: int = 9):
    """pick_pool 에서 seed 기준 연속 n 개 픽 — 게시마다 회전. pool 12개면 4개 매번 교체."""
    pool = topic.get("pick_pool", [])
    L = len(pool)
    return [dict(pool[(seed + i) % L]) for i in range(n)]


# 공통 출처 한 줄 (아이돌/티어 토픽에 공신력 부여 — 논란 완화)
BR_SOURCE_NOTE = "※ 한국기업평판연구소 브랜드평판지수 기준 · 매월 갱신"


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
                {"role_emoji": "🎤", "name": "카리나", "subtitle": "에스파"},
                {"role_emoji": "💃", "name": "채령", "subtitle": "ITZY"},
                {"role_emoji": "✨", "name": "민지", "subtitle": "뉴진스"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "유진", "subtitle": "IVE"},
                {"role_emoji": "💃", "name": "카즈하", "subtitle": "르세라핌"},
                {"role_emoji": "✨", "name": "윈터", "subtitle": "에스파"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "다니엘", "subtitle": "뉴진스"},
                {"role_emoji": "💃", "name": "리아", "subtitle": "ITZY"},
                {"role_emoji": "✨", "name": "레이", "subtitle": "IVE"},
            ],
        ],
        "auto_comment": "🤔 당신의 올스타 픽은? 더 좋은 조합 있으면 댓글로 ⬇️",
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
        "auto_comment": "🤔 그룹별 픽 댓글로 ⬇️ 더 좋은 멤버 조합 있으면 알려주세요!",
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

    # 8b) 일시정지 챌린지 — 아이돌 픽 (공정 스피너: 8명 모두 잡힘)
    #     팀별 1명씩 시계방향 배치. 정지 프레임마다 팔 끝이 한 명에게 떨어짐 →
    #     "나는 누구 걸렸어!" 자랑 댓글 자연 유도. 팬덤 분쟁 회피 위해 못 잡는
    #     구조는 제거 (요청대로 다 고를 수 있게).
    "spinner_idol_pick": {
        "style": "spinner",
        "character_style": "idol_woman",
        "title": "오늘의 최애 픽 챌린지",
        "hint": "⏸ 일시정지! 내 최애 누구 걸렸나?",
        "options": ["장원영", "윈터", "카리나", "민지",
                    "카즈하", "안유진", "닝닝", "하니"],
        # 프레임당 45° → 8명 모두 정렬 (음식 스피너의 90°와 달리 공정)
        "deg_per_frame": 45,
        "option_fill": [196, 64, 124],
        "auto_comment": "🎀 일시정지로 누가 걸렸나요? 본인 픽 댓글로 ⬇️",
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
                {"role_emoji": "🎤", "name": "릴리", "subtitle": "NMIXX"},
                {"role_emoji": "💃", "name": "채령", "subtitle": "ITZY"},
                {"role_emoji": "✨", "name": "설윤", "subtitle": "NMIXX"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "닝닝", "subtitle": "에스파"},
                {"role_emoji": "💃", "name": "카즈하", "subtitle": "르세라핌"},
                {"role_emoji": "✨", "name": "윈터", "subtitle": "에스파"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "리즈", "subtitle": "IVE"},
                {"role_emoji": "💃", "name": "해린", "subtitle": "뉴진스"},
                {"role_emoji": "✨", "name": "장원영", "subtitle": "IVE"},
            ],
        ],
        "auto_comment": "🤔 4세대 올스타 픽 댓글로 ⬇️ 더 좋은 조합 있으면 알려주세요!",
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
                {"role_emoji": "🎤", "name": "정원", "subtitle": "엔하이픈"},
                {"role_emoji": "💃", "name": "필릭스", "subtitle": "스키즈"},
                {"role_emoji": "✨", "name": "성훈", "subtitle": "엔하이픈"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "태현", "subtitle": "TXT"},
                {"role_emoji": "💃", "name": "앤톤", "subtitle": "RIIZE"},
                {"role_emoji": "✨", "name": "박원빈", "subtitle": "RIIZE"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "승민", "subtitle": "스키즈"},
                {"role_emoji": "💃", "name": "휴닝카이", "subtitle": "TXT"},
                {"role_emoji": "✨", "name": "윤호", "subtitle": "ATEEZ"},
            ],
        ],
        "auto_comment": "🔥 4세대 보이그룹 본인 픽 댓글로 ⬇️ 더 좋은 조합 있으면 알려주세요!",
    },

    # 11) 30만원 해외여행 — 실사 (도시별 사진)
    "travel_30man": {
        "style": "photo",
        "title": "30만원으로 해외여행 가기",
        "highlight": "30만원",
        "rule_hint": "각 도시 1코스 골라 합 30만원 — 당신의 여행 계획은?",
        "col_headers": ["일본", "동남아", "유럽"],
        "row_prices": ["15만원", "10만원", "5만원"],
        "cells": [
            # 15만원 (premium)
            [
                {"photo_queries": ["tokyo skyline night neon", "japan luxury ryokan onsen",
                                   "japanese fine dining sushi"],
                 "label": "도쿄 5성급 3박"},
                {"photo_queries": ["bali pool villa luxury", "phuket beach resort",
                                   "danang beachfront sunset"],
                 "label": "발리 풀빌라 4박"},
                {"photo_queries": ["paris eiffel tower night", "rome colosseum",
                                   "santorini greece sunset"],
                 "label": "파리 부티크 호텔 2박"},
            ],
            # 10만원 (mid)
            [
                {"photo_queries": ["osaka castle dotonbori", "kyoto bamboo forest",
                                   "japanese street food"],
                 "label": "오사카 게스트하우스 4박"},
                {"photo_queries": ["bangkok night market", "vietnam danang beach",
                                   "thailand temple"],
                 "label": "방콕 4성급 5박"},
                {"photo_queries": ["barcelona park guell", "amsterdam canal night",
                                   "prague old town square"],
                 "label": "바르셀로나 호스텔 4박"},
            ],
            # 5만원 (budget)
            [
                {"photo_queries": ["fukuoka tonkotsu ramen", "tokyo convenience store night",
                                   "japan budget hostel"],
                 "label": "후쿠오카 당일치기"},
                {"photo_queries": ["vietnam street food hanoi", "philippines local market",
                                   "thailand budget hostel"],
                 "label": "다낭 호스텔 2박"},
                {"photo_queries": ["budapest danube night", "prague old town",
                                   "european hostel dorm"],
                 "label": "프라하 도미토리 3박"},
            ],
        ],
        "auto_comment": "✈️ 내 30만원 여행 코스 댓글로 ⬇️ 어디 가실?",
    },

    # 12) 트로트가수 라이브 라인업
    "trot_concert_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 트로트 라이브 가기",
        "highlight": "트로트",
        "rule_hint": "각 카테고리 1명씩 골라 합 1만원 — 당신의 트로트 라인업?",
        "col_headers": ["남자트로트", "여자트로트", "신성트로트"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🎤", "name": "임영웅"},
                {"role_emoji": "🎤", "name": "송가인"},
                {"role_emoji": "🎤", "name": "정동원"},
            ],
            # 3천원
            [
                {"role_emoji": "🎤", "name": "영탁"},
                {"role_emoji": "🎤", "name": "장윤정"},
                {"role_emoji": "🎤", "name": "이찬원"},
            ],
            # 2천원
            [
                {"role_emoji": "🎤", "name": "김호중"},
                {"role_emoji": "🎤", "name": "김연자"},
                {"role_emoji": "🎤", "name": "양지은"},
            ],
        ],
        "auto_comment": "🎤 내 트로트 라인업 댓글로 ⬇️ 임영웅·송가인·영탁 다 모였어요!",
    },

    # 13) 발라드가수 콘서트 라인업
    "ballad_concert_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 발라드 콘서트 가기",
        "highlight": "발라드",
        "rule_hint": "각 카테고리 1명씩 골라 합 1만원 — 당신의 감성 라인업?",
        "col_headers": ["남자발라더", "여자발라더", "신성발라더"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "cells": [
            # 5천원
            [
                {"role_emoji": "🎵", "name": "성시경"},
                {"role_emoji": "🎵", "name": "박정현"},
                {"role_emoji": "🎵", "name": "폴킴"},
            ],
            # 3천원
            [
                {"role_emoji": "🎵", "name": "김범수"},
                {"role_emoji": "🎵", "name": "백지영"},
                {"role_emoji": "🎵", "name": "케이시"},
            ],
            # 2천원
            [
                {"role_emoji": "🎵", "name": "박효신"},
                {"role_emoji": "🎵", "name": "정인"},
                {"role_emoji": "🎵", "name": "정승환"},
            ],
        ],
        "auto_comment": "🎵 내 감성 라인업 댓글로 ⬇️ 성시경·박정현·박효신 다 있어요!",
    },

    # 14) 100만원으로 자식 만들기 — 그림 (이상형 시리즈 후속, 부모 공감 톤)
    "child_pick_100man": {
        "style": "drawing",
        "title": "100만원으로 자식 만들기",
        "highlight": "자식",
        "rule_hint": "각 항목 1개씩 골라 합 100만원 — 당신의 픽은?",
        "col_headers": ["외모", "성격", "공부머리"],
        "row_prices": ["50만원", "30만원", "20만원"],
        "cells": [
            # 50만원
            [
                {"emoji": "✨", "label": "조각상 외모"},
                {"emoji": "💖", "label": "효자효녀 다정"},
                {"emoji": "🧠", "label": "전교 1등 천재"},
            ],
            # 30만원
            [
                {"emoji": "😊", "label": "호감 외모"},
                {"emoji": "😎", "label": "마이웨이 쿨"},
                {"emoji": "📚", "label": "성실한 모범생"},
            ],
            # 20만원
            [
                {"emoji": "🙂", "label": "포인트 매력"},
                {"emoji": "🤪", "label": "엉뚱 발랄 매력"},
                {"emoji": "🏃", "label": "체육 만점"},
            ],
        ],
        "auto_comment": "👶 내 자식 픽 댓글로 ⬇️ 외모·성격·공부 중 뭐가 1순위?",
    },

    # 15) 5세대 걸그룹 1티어편 — BABYMONSTER + ILLIT + KISS OF LIFE 3대 메이저
    # 15) 5세대 걸그룹 1티어편 — col_pools 회전 (게시마다 다른 9명)
    #     1티어 그룹: BABYMONSTER·ILLIT·KIIIKIII·KISS OF LIFE·Hearts2Hearts·MEOVV
    "girlgroup_5gen_tier1_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 5세대 걸그룹 1티어편",
        "highlight": "1티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 5세대 진짜 1티어?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            # 메인보컬 풀 (게시마다 회전)
            [
                {"role_emoji": "🎤", "name": "윤아", "subtitle": "ILLIT"},
                {"role_emoji": "🎤", "name": "아현", "subtitle": "BABYMONSTER"},
                {"role_emoji": "🎤", "name": "지유", "subtitle": "KIIIKIII"},
                {"role_emoji": "🎤", "name": "벨", "subtitle": "KISS OF LIFE"},
                {"role_emoji": "🎤", "name": "카르멘", "subtitle": "Hearts2Hearts"},
                {"role_emoji": "🎤", "name": "수인", "subtitle": "MEOVV"},
            ],
            # 메인댄서 풀
            [
                {"role_emoji": "💃", "name": "루카", "subtitle": "BABYMONSTER"},
                {"role_emoji": "💃", "name": "모카", "subtitle": "ILLIT"},
                {"role_emoji": "💃", "name": "이솔", "subtitle": "KIIIKIII"},
                {"role_emoji": "💃", "name": "나띠", "subtitle": "KISS OF LIFE"},
                {"role_emoji": "💃", "name": "가원", "subtitle": "MEOVV"},
                {"role_emoji": "💃", "name": "유하", "subtitle": "Hearts2Hearts"},
            ],
            # 비주얼 풀
            [
                {"role_emoji": "✨", "name": "원희", "subtitle": "ILLIT"},
                {"role_emoji": "✨", "name": "차퀴타", "subtitle": "BABYMONSTER"},
                {"role_emoji": "✨", "name": "키야", "subtitle": "KIIIKIII"},
                {"role_emoji": "✨", "name": "줄리", "subtitle": "KISS OF LIFE"},
                {"role_emoji": "✨", "name": "스텔라", "subtitle": "Hearts2Hearts"},
                {"role_emoji": "✨", "name": "안나", "subtitle": "MEOVV"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🌟 5세대 진짜 1티어 — BABYMONSTER·ILLIT·KIIIKIII·미야오·하투하·키스오브라이프! 더 강한 픽 있으면 댓글로 ⬇️",
    },

    # 16) 5세대 걸그룹 2티어편 — IZNA + Young Posse 다크호스 (col_pools 회전)
    "girlgroup_5gen_tier2_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 5세대 걸그룹 2티어편",
        "highlight": "2티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 5세대 다크호스!",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "사랑", "subtitle": "IZNA"},
                {"role_emoji": "🎤", "name": "도은", "subtitle": "Young Posse"},
                {"role_emoji": "🎤", "name": "마유나", "subtitle": "IZNA"},
                {"role_emoji": "🎤", "name": "예은", "subtitle": "Young Posse"},
            ],
            [
                {"role_emoji": "💃", "name": "정원", "subtitle": "IZNA"},
                {"role_emoji": "💃", "name": "선혜", "subtitle": "Young Posse"},
                {"role_emoji": "💃", "name": "지우", "subtitle": "IZNA"},
                {"role_emoji": "💃", "name": "재희", "subtitle": "Young Posse"},
            ],
            [
                {"role_emoji": "✨", "name": "사야", "subtitle": "IZNA"},
                {"role_emoji": "✨", "name": "지아나", "subtitle": "Young Posse"},
                {"role_emoji": "✨", "name": "코코로", "subtitle": "IZNA"},
                {"role_emoji": "✨", "name": "윤지", "subtitle": "IZNA"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🌠 5세대 다크호스 — IZNA·Young Posse! 1티어로 올라올 멤버는? 댓글로 ⬇️",
    },

    # 17) 4세대 걸그룹 1티어편 — 뉴진스/에스파/IVE/르세라핌 (col_pools 회전)
    "girlgroup_4gen_tier1_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 걸그룹 1티어편",
        "highlight": "1티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 4세대 진짜 1티어?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            # 메인보컬 S/A 풀
            [
                {"role_emoji": "🎤", "name": "카리나", "subtitle": "에스파"},
                {"role_emoji": "🎤", "name": "민지", "subtitle": "뉴진스"},
                {"role_emoji": "🎤", "name": "닝닝", "subtitle": "에스파"},
                {"role_emoji": "🎤", "name": "다니엘", "subtitle": "뉴진스"},
                {"role_emoji": "🎤", "name": "김채원", "subtitle": "르세라핌"},
                {"role_emoji": "🎤", "name": "안유진", "subtitle": "IVE"},
            ],
            # 메인댄서 S/A 풀
            [
                {"role_emoji": "💃", "name": "카즈하", "subtitle": "르세라핌"},
                {"role_emoji": "💃", "name": "하니", "subtitle": "뉴진스"},
                {"role_emoji": "💃", "name": "사쿠라", "subtitle": "르세라핌"},
                {"role_emoji": "💃", "name": "지젤", "subtitle": "에스파"},
                {"role_emoji": "💃", "name": "해린", "subtitle": "뉴진스"},
                {"role_emoji": "💃", "name": "혜인", "subtitle": "뉴진스"},
            ],
            # 비주얼 S/A 풀
            [
                {"role_emoji": "✨", "name": "장원영", "subtitle": "IVE"},
                {"role_emoji": "✨", "name": "윈터", "subtitle": "에스파"},
                {"role_emoji": "✨", "name": "리즈", "subtitle": "IVE"},
                {"role_emoji": "✨", "name": "허윤진", "subtitle": "르세라핌"},
                {"role_emoji": "✨", "name": "이서", "subtitle": "IVE"},
                {"role_emoji": "✨", "name": "레이", "subtitle": "IVE"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🥇 4세대 진짜 1티어 — 더 강한 픽 있으면 댓글로 ⬇️ 너희가 생각하는 1티어는?",
    },

    # 18) 4세대 걸그룹 2티어편 — ITZY/NMIXX/(여자)아이들 (col_pools 회전)
    "girlgroup_4gen_tier2_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 걸그룹 2티어편",
        "highlight": "2티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 1티어급 누구?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "릴리", "subtitle": "NMIXX"},
                {"role_emoji": "🎤", "name": "미연", "subtitle": "(여자)아이들"},
                {"role_emoji": "🎤", "name": "류진", "subtitle": "ITZY"},
                {"role_emoji": "🎤", "name": "해원", "subtitle": "NMIXX"},
                {"role_emoji": "🎤", "name": "민니", "subtitle": "(여자)아이들"},
            ],
            [
                {"role_emoji": "💃", "name": "채령", "subtitle": "ITZY"},
                {"role_emoji": "💃", "name": "소연", "subtitle": "(여자)아이들"},
                {"role_emoji": "💃", "name": "베이", "subtitle": "NMIXX"},
                {"role_emoji": "💃", "name": "리아", "subtitle": "ITZY"},
                {"role_emoji": "💃", "name": "우기", "subtitle": "(여자)아이들"},
            ],
            [
                {"role_emoji": "✨", "name": "설윤", "subtitle": "NMIXX"},
                {"role_emoji": "✨", "name": "슈화", "subtitle": "(여자)아이들"},
                {"role_emoji": "✨", "name": "지우", "subtitle": "NMIXX"},
                {"role_emoji": "✨", "name": "예지", "subtitle": "ITZY"},
                {"role_emoji": "✨", "name": "규진", "subtitle": "NMIXX"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🥈 2티어도 만만찮다 — 누가 1티어급? 더 좋은 픽 있으면 댓글로 ⬇️",
    },

    # 19) 4세대 걸그룹 3티어편 — STAYC/Kep1er/Billlie/fromis_9 (col_pools 회전)
    "girlgroup_4gen_tier3_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 걸그룹 3티어편",
        "highlight": "3티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 다음 시즌 1티어는?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "시은", "subtitle": "STAYC"},
                {"role_emoji": "🎤", "name": "다영", "subtitle": "Kep1er"},
                {"role_emoji": "🎤", "name": "백지헌", "subtitle": "fromis_9"},
                {"role_emoji": "🎤", "name": "수현", "subtitle": "Billlie"},
            ],
            [
                {"role_emoji": "💃", "name": "재이", "subtitle": "STAYC"},
                {"role_emoji": "💃", "name": "샤오팅", "subtitle": "Kep1er"},
                {"role_emoji": "💃", "name": "츠키", "subtitle": "Billlie"},
                {"role_emoji": "💃", "name": "시연", "subtitle": "fromis_9"},
            ],
            [
                {"role_emoji": "✨", "name": "수민", "subtitle": "STAYC"},
                {"role_emoji": "✨", "name": "아이사", "subtitle": "STAYC"},
                {"role_emoji": "✨", "name": "바히에", "subtitle": "Kep1er"},
                {"role_emoji": "✨", "name": "이새롬", "subtitle": "fromis_9"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🥉 3티어 다크호스 — 1티어로 올라올 멤버 댓글로 ⬇️ 더 좋은 픽 있으면 알려주세요!",
    },

    # ════════════════════════════════════════════════════════════
    #  남자 아이돌 티어편 (그룹/개인 BR 기준 · col_pools 회전)
    #  4세대 1티어: Stray Kids·ENHYPEN·TXT·RIIZE·ATEEZ·ZEROBASEONE
    #  4세대 2티어: THE BOYZ·NCT·TREASURE·P1Harmony 등
    #  5세대 1티어: CORTIS·TWS·BOYNEXTDOOR·KickFlip
    # ════════════════════════════════════════════════════════════
    "boygroup_4gen_tier1_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 보이그룹 1티어편",
        "highlight": "1티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 4세대 보이그룹 1티어?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "필릭스", "subtitle": "스트레이키즈"},
                {"role_emoji": "🎤", "name": "정원", "subtitle": "엔하이픈"},
                {"role_emoji": "🎤", "name": "태현", "subtitle": "TXT"},
                {"role_emoji": "🎤", "name": "승한", "subtitle": "RIIZE"},
                {"role_emoji": "🎤", "name": "종호", "subtitle": "ATEEZ"},
                {"role_emoji": "🎤", "name": "성한빈", "subtitle": "제로베이스원"},
            ],
            [
                {"role_emoji": "💃", "name": "현진", "subtitle": "스트레이키즈"},
                {"role_emoji": "💃", "name": "니키", "subtitle": "엔하이픈"},
                {"role_emoji": "💃", "name": "휴닝카이", "subtitle": "TXT"},
                {"role_emoji": "💃", "name": "앤톤", "subtitle": "RIIZE"},
                {"role_emoji": "💃", "name": "산", "subtitle": "ATEEZ"},
                {"role_emoji": "💃", "name": "리키", "subtitle": "제로베이스원"},
            ],
            [
                {"role_emoji": "✨", "name": "성훈", "subtitle": "엔하이픈"},
                {"role_emoji": "✨", "name": "한", "subtitle": "스트레이키즈"},
                {"role_emoji": "✨", "name": "연준", "subtitle": "TXT"},
                {"role_emoji": "✨", "name": "원빈", "subtitle": "RIIZE"},
                {"role_emoji": "✨", "name": "윤호", "subtitle": "ATEEZ"},
                {"role_emoji": "✨", "name": "장하오", "subtitle": "제로베이스원"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🥇 4세대 보이그룹 1티어 — 스키즈·엔하이픈·TXT·RIIZE·ATEEZ·ZB1! 더 강한 픽 댓글로 ⬇️",
    },

    "boygroup_4gen_tier2_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 4세대 보이그룹 2티어편",
        "highlight": "2티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 1티어급 누구?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "주연", "subtitle": "더보이즈"},
                {"role_emoji": "🎤", "name": "도영", "subtitle": "NCT"},
                {"role_emoji": "🎤", "name": "지훈", "subtitle": "트레저"},
                {"role_emoji": "🎤", "name": "기호", "subtitle": "P1Harmony"},
            ],
            [
                {"role_emoji": "💃", "name": "재현", "subtitle": "NCT"},
                {"role_emoji": "💃", "name": "현재", "subtitle": "트레저"},
                {"role_emoji": "💃", "name": "큐", "subtitle": "더보이즈"},
                {"role_emoji": "💃", "name": "인탁", "subtitle": "P1Harmony"},
            ],
            [
                {"role_emoji": "✨", "name": "선우", "subtitle": "더보이즈"},
                {"role_emoji": "✨", "name": "정우", "subtitle": "NCT"},
                {"role_emoji": "✨", "name": "마시호", "subtitle": "트레저"},
                {"role_emoji": "✨", "name": "테오", "subtitle": "P1Harmony"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🥈 4세대 보이그룹 2티어 — 1티어급 픽 댓글로 ⬇️ 더 좋은 조합 있으면 알려주세요!",
    },

    "boygroup_5gen_tier1_10k": {
        "style": "emblem",
        "background_style": "white",
        "title": "만원으로 5세대 보이그룹 1티어편",
        "highlight": "1티어편",
        "rule_hint": "각 포지션 1명씩 골라 합 1만원 — 5세대 보이그룹 1티어?",
        "col_headers": ["메인보컬", "메인댄서", "비주얼"],
        "row_prices": ["5천원", "3천원", "2천원"],
        "col_pools": [
            [
                {"role_emoji": "🎤", "name": "마틴", "subtitle": "CORTIS"},
                {"role_emoji": "🎤", "name": "신유", "subtitle": "TWS"},
                {"role_emoji": "🎤", "name": "성호", "subtitle": "보이넥스트도어"},
                {"role_emoji": "🎤", "name": "민재", "subtitle": "KickFlip"},
            ],
            [
                {"role_emoji": "💃", "name": "제임스", "subtitle": "CORTIS"},
                {"role_emoji": "💃", "name": "도훈", "subtitle": "TWS"},
                {"role_emoji": "💃", "name": "태산", "subtitle": "보이넥스트도어"},
                {"role_emoji": "💃", "name": "휘찬", "subtitle": "KickFlip"},
            ],
            [
                {"role_emoji": "✨", "name": "주훈", "subtitle": "CORTIS"},
                {"role_emoji": "✨", "name": "영재", "subtitle": "TWS"},
                {"role_emoji": "✨", "name": "리우", "subtitle": "보이넥스트도어"},
                {"role_emoji": "✨", "name": "동현", "subtitle": "KickFlip"},
            ],
        ],
        "source_note": BR_SOURCE_NOTE,
        "auto_comment": "🌟 5세대 보이그룹 1티어 — CORTIS·TWS·보이넥스트도어·KickFlip! 더 강한 픽 댓글로 ⬇️",
    },

    # ════════════════════════════════════════════════════════════
    #  초능력 픽 — 단일 픽 9-셀 grid (가격/합산 없음, 손그림 cute)
    #  pick_pools 길이 = 9 의 배수 → 게시마다 다른 9개 회전
    # ════════════════════════════════════════════════════════════
    "powerpick_office": {
        "style": "powerpick",
        "title": "단 하나의 초능력만 고를 수 있다면?",
        "rule_hint": "(직장인편)",
        # 12개 풀에서 9개 회전 (seed offset). 한 토픽 = 여러 콘텐츠.
        "pick_pool": [
            {"emoji": "💼", "label": "연봉 매년\n2배 인상"},
            {"emoji": "🎁", "label": "매년 보너스\n5천만원"},
            {"emoji": "📈", "label": "모든 평가\nS등급 자동"},
            {"emoji": "📊", "label": "PPT/엑셀\n자동 완성"},
            {"emoji": "🚪", "label": "평생 칼퇴\n보장권"},
            {"emoji": "🏖️", "label": "원하는 날\n연차 무조건 승인"},
            {"emoji": "⏰", "label": "일할 때만\n시간 정지"},
            {"emoji": "✈️", "label": "출퇴근\n순간이동"},
            {"emoji": "😴", "label": "잠 안 자도\n풀컨디션"},
            {"emoji": "🧠", "label": "한 번 보면\n100% 암기"},
            {"emoji": "🌐", "label": "모든 언어\n즉시 마스터"},
            {"emoji": "📅", "label": "월요일\n영구 삭제"},
        ],
        "auto_comment": "💬 단 하나만! 본인 픽 댓글로 ⬇️ 친구는 뭐 고를까?",
    },
}
