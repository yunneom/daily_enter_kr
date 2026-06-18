"""
쿠팡 파트너스 어필리에이트 통합 — 토픽 → 상품 카테고리 매핑 + URL 빌더.

[전략]
IG bio 링크는 1개만 가능. → GitHub Pages 랜딩(`docs/index.html`)에
토픽별 추천 카테고리 그리드 + Coupang 검색 링크(AF_ID 자동 첨부).
매 게시 후 generate_landing.py 가 docs/index.html 재생성 → 자동 커밋.

[URL 형식]
1순위 — 사용자가 Partners 대시보드에서 만든 link.coupang.com/a/XXXX 단축링크
        (가장 정확한 attribution). 카테고리별로 CATEGORY_SHORTLINKS 채우면 됨.
2순위 — 검색 URL 폴백: coupang.com/np/search?q=... 에 AF_ID query 첨부.

[법적]
한국 공정위 추천·보증 심사지침 — 모든 게시물 / 페이지에 다음 문구 노출 필수:
"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
landing 페이지 푸터 + IG 캡션 양쪽 모두 표시.
"""

import os
import urllib.parse


COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받습니다."
)

# 토픽 ID → 카테고리 (랜딩 페이지에서 자연스럽게 묶어줄 그룹)
TOPIC_TO_CATEGORY = {
    # 음식·라이프스타일
    "weekend_5man": "캠핑·피크닉",
    "lunch_15k": "도시락·간편식",
    "spinner_food_man": "야식·치킨",
    "spinner_lazy_woman": "홈트·요가",
    "travel_30man": "여행·캐리어",

    # K-pop · 아이돌
    "girlgroup_real_10k": "K-POP 굿즈",
    "idol_allstar_10k": "K-POP 굿즈",
    "girlgroup_4gen_10k": "K-POP 굿즈",
    "boygroup_4gen_10k": "K-POP 굿즈",
    "girlgroup_5gen_tier1_10k": "K-POP 굿즈",
    "girlgroup_5gen_tier2_10k": "K-POP 굿즈",
    "girlgroup_4gen_tier1_10k": "K-POP 굿즈",
    "girlgroup_4gen_tier2_10k": "K-POP 굿즈",
    "girlgroup_4gen_tier3_10k": "K-POP 굿즈",
    "boygroup_4gen_tier1_10k": "K-POP 굿즈",
    "boygroup_4gen_tier2_10k": "K-POP 굿즈",
    "boygroup_5gen_tier1_10k": "K-POP 굿즈",
    "spinner_idol_pick": "K-POP 굿즈",
    "powerpick_idol": "K-POP 굿즈",

    # 콘서트 / 라이브
    "trot_concert_10k": "트로트 굿즈",
    "ballad_concert_10k": "콘서트 굿즈",

    # 카테고리 일상
    "idealtype_10k": "데이트룩",
    "child_pick_100man": "육아용품",
    "soccer_nationalteam_1000eok": "축구·국대유니폼",
    "job_pick_10k": "직장인 가전",
    "power_budget_10k": "두뇌 굿즈",
    "powerpick_office": "직장인 가전",
    "powerpick_student": "학용품·문구",
    "powerpick_teacher": "선생님 선물",
    "powerpick_neet": "홈트·라운지웨어",
    "powerpick_landlord": "재테크 도서",
    "spot_diff_bear": "곰돌이 굿즈",
}


# 카테고리별 검색 쿼리 (검색 URL 폴백용)
CATEGORY_QUERIES = {
    "캠핑·피크닉": "피크닉 매트",
    "도시락·간편식": "도시락통",
    "야식·치킨": "치킨 엽떡",
    "홈트·요가": "요가매트",
    "여행·캐리어": "여행 캐리어",
    "K-POP 굿즈": "케이팝 응원봉",
    "트로트 굿즈": "임영웅 굿즈",
    "콘서트 굿즈": "콘서트 야광봉",
    "데이트룩": "데이트룩 원피스",
    "육아용품": "유아 장난감",
    "축구·국대유니폼": "축구 유니폼",
    "직장인 가전": "사무용 데스크",
    "두뇌 굿즈": "두뇌 트레이닝",
    "학용품·문구": "수험생 문구",
    "선생님 선물": "스승의날 선물",
    "홈트·라운지웨어": "라운지웨어",
    "재테크 도서": "재테크 책",
    "곰돌이 굿즈": "곰돌이 인형",
}


# 카테고리별 단축링크 — 사용자가 Coupang Partners 대시보드에서 직접 생성해 채움.
# 값이 비면 검색 URL 폴백 사용. attribution 정확도 ↑ 위해 단축링크 채우는 것 권장.
CATEGORY_SHORTLINKS = {
    # "K-POP 굿즈": "https://link.coupang.com/a/XXXXXX",
    # "야식·치킨": "https://link.coupang.com/a/YYYYYY",
}


# 카테고리별 이모지 (랜딩 페이지 시각 강조)
CATEGORY_EMOJI = {
    "캠핑·피크닉": "⛺", "도시락·간편식": "🍱", "야식·치킨": "🍗",
    "홈트·요가": "🧘", "여행·캐리어": "✈️", "K-POP 굿즈": "💿",
    "트로트 굿즈": "🎤", "콘서트 굿즈": "🎟️", "데이트룩": "💕",
    "육아용품": "👶", "축구·국대유니폼": "⚽", "직장인 가전": "💼",
    "두뇌 굿즈": "🧠", "학용품·문구": "✏️", "선생님 선물": "🍎",
    "홈트·라운지웨어": "🛋️", "재테크 도서": "📚", "곰돌이 굿즈": "🐻",
}


def get_affiliate_url(category: str) -> str:
    """카테고리 → Coupang 어필리에이트 URL.

    1순위: CATEGORY_SHORTLINKS 의 단축링크 (Partners 단축링크가 attribution 정확).
    2순위: 검색 URL + AF_ID 트래킹 파라미터.
    AF_ID 미설정 시: 일반 검색 URL (트래킹 없음 — 수익 X).
    """
    short = CATEGORY_SHORTLINKS.get(category)
    if short:
        return short
    query = CATEGORY_QUERIES.get(category, category)
    encoded = urllib.parse.quote(query)
    base = (
        f"https://www.coupang.com/np/search?q={encoded}"
        f"&channel=user&listSize=36"
    )
    af = os.environ.get("COUPANG_AF_ID", "").strip()
    if af:
        # Coupang Partners 검색 트래킹 — traid=affiliate + trcid=AF_ID
        base += f"&trcid={urllib.parse.quote(af)}&traid=affiliate"
    return base


def get_topic_category(topic_id: str) -> str:
    """토픽 → 카테고리. 매핑 없으면 'K-POP 굿즈' 폴백."""
    return TOPIC_TO_CATEGORY.get(topic_id, "K-POP 굿즈")


def caption_bio_cta(topic_id: str) -> str:
    """캡션 끝부분에 넣을 짧은 bio 유도 CTA.

    IG 캡션에 외부 링크 직접 노출은 클릭 불가 → bio 링크로 유도.
    """
    cat = get_topic_category(topic_id)
    emoji = CATEGORY_EMOJI.get(cat, "🛒")
    return f"{emoji} 추천 {cat} 보러가기 → 프로필 링크 ⬇️"
