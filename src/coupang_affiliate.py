"""
쿠팡 파트너스 어필리에이트 — 수익 모델 v2 (수동 단축링크 기반).

[중요 — 수익 발생 메커니즘]
쿠팡 파트너스는 **자기 시스템에서 생성한 링크만 수수료를 인정**합니다:
  ✅ link.coupang.com/a/XXXX  ← 파트너스 대시보드에서 수동 생성한 단축링크
  ✅ coupa.ng/XXXX            ← 위와 동일
  ❌ coupang.com/np/search?...&trcid=...  ← 검색 URL + AF_ID 첨부는 수익 X

OpenAPI Access+Secret 키가 있으면 딥링크 API로 자동 생성 가능하지만,
현재 운영자 보유는 AF 추적 ID 1개뿐 → **수동 단축링크 채우는 게 유일한 수익 경로**.

[24시간 라스트클릭 쿠키]
사용자가 내 단축링크 1번만 클릭하면 그 후 24시간 안의 모든 쿠팡 구매가
내 수수료로 인정. 따라서 전략은 단순:
  → 클릭 수 극대화 (= 정확하고 매력적인 상품 추천 + 다수 노출 슬롯)

[수동 설정 방법 — 한 번만]
1. https://partners.coupang.com → 로그인
2. 좌측 메뉴 "링크 생성" 클릭
3. CATEGORY_SEARCH_HINTS 의 각 검색어로 검색
4. 마음에 드는 상품(또는 검색결과 페이지)에서 "링크 생성" 클릭
5. 단축링크(link.coupang.com/a/XXXX) 복사
6. data/coupang_shortlinks.csv 에 카테고리,URL 형식으로 붙여넣기
   (또는 CATEGORY_SHORTLINKS dict 에 직접 입력)
"""

import csv
import os
from pathlib import Path


COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받습니다."
)


# ─────────────────────────────────────────────────────────────────
# 토픽 ID → 카테고리 (랜딩 페이지·캡션 CTA 에서 묶음 표시)
# ─────────────────────────────────────────────────────────────────
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

    # 일상 / 기타
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


# ─────────────────────────────────────────────────────────────────
# 카테고리 메타 — 검색 힌트(파트너스 대시보드용) + 이모지
# ─────────────────────────────────────────────────────────────────
CATEGORY_META = {
    "캠핑·피크닉":      {"emoji": "⛺", "search_hint": "피크닉 매트 캠핑 의자"},
    "도시락·간편식":    {"emoji": "🍱", "search_hint": "도시락통 직장인 도시락"},
    "야식·치킨":        {"emoji": "🍗", "search_hint": "치킨 엽떡 닭발 안주"},
    "홈트·요가":        {"emoji": "🧘", "search_hint": "요가매트 홈트 덤벨"},
    "여행·캐리어":      {"emoji": "✈️", "search_hint": "여행 캐리어 28인치"},
    "K-POP 굿즈":       {"emoji": "💿", "search_hint": "케이팝 응원봉 앨범 포카 슬리브"},
    "트로트 굿즈":      {"emoji": "🎤", "search_hint": "임영웅 굿즈 트로트 응원도구"},
    "콘서트 굿즈":      {"emoji": "🎟️", "search_hint": "콘서트 야광봉 응원봉 배터리"},
    "데이트룩":         {"emoji": "💕", "search_hint": "데이트룩 원피스 향수"},
    "육아용품":         {"emoji": "👶", "search_hint": "유아 장난감 책 옷"},
    "축구·국대유니폼":  {"emoji": "⚽", "search_hint": "축구 유니폼 대한민국 손흥민"},
    "직장인 가전":      {"emoji": "💼", "search_hint": "사무용 모니터암 키보드 마우스 무선"},
    "두뇌 굿즈":        {"emoji": "🧠", "search_hint": "두뇌 트레이닝 퍼즐 보드게임"},
    "학용품·문구":      {"emoji": "✏️", "search_hint": "수험생 문구 다이어리 펜"},
    "선생님 선물":      {"emoji": "🍎", "search_hint": "스승의날 선물 텀블러 꽃다발"},
    "홈트·라운지웨어":  {"emoji": "🛋️", "search_hint": "라운지웨어 잠옷 파자마"},
    "재테크 도서":      {"emoji": "📚", "search_hint": "재테크 책 부동산 주식 베스트셀러"},
    "곰돌이 굿즈":      {"emoji": "🐻", "search_hint": "곰돌이 인형 캐릭터 굿즈"},
}


# ─────────────────────────────────────────────────────────────────
# CATEGORY_SHORTLINKS — 실제 수익 발생 단축링크
# ─────────────────────────────────────────────────────────────────
# 형식: { "카테고리": "https://link.coupang.com/a/XXXXXX" }
#
# 우선 순위:
#   1) data/coupang_shortlinks.csv 가 존재하면 그것에서 로드 (권장 — 코드 수정 없이 채움)
#   2) 아래 dict 에 직접 박힌 값
#
# 단축링크가 없는 카테고리는 랜딩 페이지에 안 노출 + 캡션 CTA 비활성화 →
# 끊긴 링크·수익 안 잡히는 가짜 링크 방지.
# ─────────────────────────────────────────────────────────────────
CATEGORY_SHORTLINKS: dict = {
    # "K-POP 굿즈": "https://link.coupang.com/a/XXXXXX",
    # "야식·치킨": "https://link.coupang.com/a/YYYYYY",
}


_CSV_PATH = Path(__file__).parent.parent / "data" / "coupang_shortlinks.csv"


def _load_csv_shortlinks() -> dict:
    """data/coupang_shortlinks.csv 에서 카테고리→단축링크 로드.
    # 으로 시작하는 행과 빈 행은 무시.
    """
    if not _CSV_PATH.exists():
        return {}
    out = {}
    with _CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cat = (row.get("category") or "").strip()
            url = (row.get("shortlink") or "").strip()
            if cat.startswith("#") or not cat:
                continue
            if url and url.startswith(("http://", "https://")):
                out[cat] = url
    return out


def get_shortlinks() -> dict:
    """전 카테고리 → 단축링크 dict. CSV 우선, dict fallback."""
    merged = dict(CATEGORY_SHORTLINKS)
    merged.update(_load_csv_shortlinks())  # CSV 가 dict 를 override (운영자 최신)
    return merged


def get_affiliate_url(category: str) -> str | None:
    """카테고리 → 단축링크. 없으면 None (= 노출 안 함, 수익 가짜 X)."""
    links = get_shortlinks()
    return links.get(category)


def get_topic_category(topic_id: str) -> str:
    """토픽 → 카테고리. 매핑 없으면 'K-POP 굿즈' 폴백."""
    return TOPIC_TO_CATEGORY.get(topic_id, "K-POP 굿즈")


def get_topic_affiliate_url(topic_id: str) -> str | None:
    """토픽 → 단축링크 (카테고리 거쳐서). 없으면 None."""
    return get_affiliate_url(get_topic_category(topic_id))


def category_emoji(category: str) -> str:
    return CATEGORY_META.get(category, {}).get("emoji", "🛒")


def caption_bio_cta(topic_id: str) -> str | None:
    """캡션 끝부분에 넣을 짧은 bio 유도 CTA.

    단축링크 미설정 → None (= 가짜 CTA 노출 방지).
    """
    if not get_topic_affiliate_url(topic_id):
        return None
    cat = get_topic_category(topic_id)
    emoji = category_emoji(cat)
    return f"{emoji} 추천 {cat} 보러가기 → 프로필 링크 ⬇️"


def comment_affiliate_line(topic_id: str) -> str | None:
    """auto_comment 에 붙일 단축링크 라인.

    IG 코멘트 URL 은 클릭 자동화는 안 되지만 텍스트로 노출됨 → 복사 + 24h 쿠키.
    bio 클릭률 외 추가 클릭 채널. 단축링크 미설정이면 None.
    """
    url = get_topic_affiliate_url(topic_id)
    if not url:
        return None
    cat = get_topic_category(topic_id)
    emoji = category_emoji(cat)
    return f"{emoji} {cat} 추천템 → {url}"


def coverage_report() -> dict:
    """설정 진단 — 몇 개 카테고리/토픽에 단축링크가 설정됐는지."""
    links = get_shortlinks()
    all_categories = sorted({c for c in TOPIC_TO_CATEGORY.values()})
    configured = [c for c in all_categories if c in links]
    missing = [c for c in all_categories if c not in links]
    total_topics = len(TOPIC_TO_CATEGORY)
    covered_topics = sum(
        1 for t in TOPIC_TO_CATEGORY.values() if t in links
    )
    return {
        "csv_path": str(_CSV_PATH),
        "csv_exists": _CSV_PATH.exists(),
        "total_categories": len(all_categories),
        "configured_categories": configured,
        "missing_categories": missing,
        "configured_topics": covered_topics,
        "total_topics": total_topics,
        "revenue_active": len(configured) > 0,
    }


if __name__ == "__main__":
    # python -m coupang_affiliate → 현재 설정 상태 점검
    rep = coverage_report()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("쿠팡 파트너스 — 단축링크 설정 상태")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"CSV 경로:   {rep['csv_path']}")
    print(f"CSV 존재:   {'✅' if rep['csv_exists'] else '❌ (생성 필요)'}")
    print(f"카테고리:   {len(rep['configured_categories'])}/{rep['total_categories']} 설정됨")
    print(f"토픽 커버:  {rep['configured_topics']}/{rep['total_topics']} 토픽 수익 활성")
    print(f"수익 활성:  {'✅ ON' if rep['revenue_active'] else '🚨 OFF — 단축링크 0개'}")
    if rep["missing_categories"]:
        print(f"\n미설정 카테고리 ({len(rep['missing_categories'])}):")
        for c in rep["missing_categories"]:
            hint = CATEGORY_META.get(c, {}).get("search_hint", "")
            print(f"  · {c:18s}  ← 검색어 힌트: {hint}")
    print("\n설정 방법:")
    print("  1) https://partners.coupang.com → 링크 생성")
    print("  2) 위 검색어로 검색 → 상품 또는 검색결과 페이지 링크 생성")
    print("  3) data/coupang_shortlinks.csv 에 카테고리,URL 추가")
