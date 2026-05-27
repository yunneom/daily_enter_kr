"""
뉴스 요약 모듈
Claude API를 사용하여 K-연예 뉴스를 인스타그램 카드뉴스용으로 요약합니다.

[모델]
- Claude Haiku 4.5: 가성비 최고, 일 10건 ≈ $0.01

[보안/평판 안전장치]
- 민감 주제(자살/사망/미성년자/성형/연애 추측 등) 자동 분류 → skip
- 사망/질환/가족사 등은 respectful 톤으로 자동 전환
- 클릭베이트/황색 표현 금지
- 카드엔 제목만 노출 (본문 없음). 제목 자체는 원기사 문장 그대로 옮기지 않도록 변형 (저작권 안전선)
"""

import os
import json
from anthropic import Anthropic
from dataclasses import dataclass, field
from typing import List

# fetch_news.py의 NewsItem import
from fetch_news import NewsItem


@dataclass
class SummarizedNews:
    original_title: str
    card_title: str
    hashtags: list
    source: str
    link: str
    decision: str = "post"          # "post" | "respectful" | "skip"
    skip_reason: str = ""           # decision=="skip" 일 때만 사용
    visual_concept: str = ""        # 영문 Unsplash 검색 쿼리 (현재 카드엔 미사용; image_provider 보존용)


SUMMARY_PROMPT = """너는 {channel_label} 인스타그램 카드뉴스 카피라이터다. 다음 뉴스를 안전하고 품격 있는 카드뉴스로 만들어줘.

[채널] {channel_label} (이 채널의 주제 범위와 무관한 뉴스는 skip)
[뉴스 제목] {title}
[뉴스 내용/설명] {summary}
[출처] {source}

응답은 다음 JSON 형식 한 가지만. 다른 텍스트 절대 포함 금지:
{{
  "decision": "post" | "respectful" | "skip",
  "skip_reason": "skip일 때만 한 줄로 사유",
  "card_title": "16-28자 (제목만으로 핵심 사실이 전달돼야 함 — 카드엔 본문이 없음)",
  "hashtags": ["#태그1", "#태그2", "#태그3", "#태그4"],
  "visual_concept": "2-4 영문 단어 (예: 'concert stage lights', 'movie premiere red carpet', 'recording studio')"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STEP 1 — 분류 (decision)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 중 하나라도 해당하면 즉시 decision = "skip" (다른 필드는 빈 문자열/배열로):
- 자살/극단적 선택/유서/투신 관련 (인용·암시 포함)
- 폭력/성범죄/학대 피해자 신원이 추측 가능
- 만 18세 미만 미성년자의 외모/몸매/사생활/연애
- 의학적 진단명·정신건강 이슈를 가십화
- 동의 없는 연인 추측, 임신 루머, 결혼 강요 톤
- 신체/성형 비교 평가, 다이어트 강요
- 인종/성별/지역 차별 가능성 있는 표현
- 단순 광고/협찬/홍보
- 정치 정쟁 (선거/입법 갈등; 단, 채널 주제와 관련된 정책 뉴스는 OK)
- 채널 주제 범위와 명백히 무관한 뉴스 (예: 스포츠 채널에 연예 가십, 경제 채널에 스포츠 결과)
- 사실 확인이 안 된 단독 보도가 자극적인 경우

다음에 해당하면 decision = "respectful":
- 부고/별세 (공식 발표만 인용, 사인 추측 없이)
- 본인이 공개적으로 알린 가정사/투병/회복 이야기
- 사회적 메시지 있는 인터뷰/사회공헌
- 사회적 합의가 정리된 과거 사건 회고

그 외 일반 K-연예 소식은 decision = "post".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STEP 2 — 카드 내용 (decision != "skip"일 때만)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

★ 공통 규칙 (post / respectful 모두)
- 카드에는 본문이 없고 제목만 노출됨. 제목 하나로 핵심 사실이 전달돼야 함.
- 원기사 문장을 그대로 옮기지 말 것. 핵심 사실만 추출해 다른 표현으로 재구성.
- 이모지(🔥❤️ 등) 절대 사용 금지 (카드에서 두부박스로 깨짐)
- 따옴표 인용 안에 자극적 발화를 강조하지 말 것
- 추측/루머 금지. 보도된 사실만.

★ decision == "post" — 일반 카피
- 인물명/팀명/작품명/숫자를 앞에 배치. 한 문장으로 핵심 사실 + 맥락이 드러나도록.
- 좋은 예) "아이브, 5월 27일 정규 1집 'HER' 발매"
- 좋은 예) "박찬욱 감독 신작 '미스트리스', 칸영화제 경쟁 부문 출품"
- 허용 어휘: "공개", "예고", "포착", "출연", "콜라보", "달성", "기록", "선언", "발매", "확정"
- 금지 어휘: "충격", "발칵", "경악", "오열", "폭로", "이럴 수가", "결국", "도대체"
- 호기심 갭(?, ...)은 가능하되 남발 금지.

★ decision == "respectful" — 민감 주제 톤
- 호기심 갭/따옴표 인용/물음표/줄임표 모두 금지. 사실만 명확히.
- 좋은 예) "故 OOO 별세, 향년 OO세"
- 좋은 예) "OOO, 투병 사실 공개하며 위로 메시지 전달"
- 호기심 자극 어휘 금지.

[hashtags]
- 4-6개. 한국어 + 영문 혼합.
- 인물/팀/그룹/작품명 직접, 채널 분야 태그, 메타 태그 (예: #뉴스, #카드뉴스).
- 자극 키워드(#충격, #논란 등) 금지.

[visual_concept] — Unsplash 검색용 영문 키워드
- 2-4 단어. 보편적 영어 명사 위주. 구체적 한국 인물명/팀명 금지 (Unsplash엔 거의 없음).
- 뉴스 분위기/장면을 연상시키는 일반적 컨셉 (분야별 예시):
  * 음악/공연: "concert stage lights", "music studio recording", "microphone close up"
  * 영화/드라마: "movie premiere", "film set camera", "cinema theater"
  * 예능/방송: "tv studio lights", "broadcasting set"
  * 시상식: "red carpet event", "award ceremony"
  * 야구: "baseball stadium night", "baseball pitcher mound"
  * 축구: "soccer stadium crowd", "football match action"
  * 골프: "golf course green", "golf swing close up"
  * 농구/배구/기타: "basketball arena", "athlete training gym"
  * 경제/주식: "stock market chart", "trading floor screens", "skyscraper finance district"
  * 부동산: "city skyline real estate", "modern apartment building"
- respectful 톤 카드: 차분한 컨셉 ("candle light memorial", "flower bouquet white")
- skip 카드: 빈 문자열

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

자, 위 규칙을 엄격히 지켜서 JSON으로만 응답하라.
"""


def summarize_news(news_items: List[NewsItem], api_key: str = None,
                   channel_label: str = "K-연예") -> List[SummarizedNews]:
    """
    뉴스 리스트를 카드뉴스용으로 요약 + 안전 분류.

    Args:
        channel_label: 채널 정체성 (예: "K-연예", "K-스포츠", "K-경제").
                       프롬프트에 주입돼 채널 주제와 맞지 않는 뉴스를 skip 판단에 활용.
    decision=="skip"인 항목도 포함해서 반환하므로, 호출자가 필터링해야 함.
    """
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    results = []
    for item in news_items:
        prompt = SUMMARY_PROMPT.format(
            channel_label=channel_label,
            title=item.title,
            summary=item.summary[:500],
            source=item.source,
        )

        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()
            # 마크다운 코드펜스 제거
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            parsed = json.loads(response_text.strip())

            decision = parsed.get("decision", "post").lower()
            if decision not in ("post", "respectful", "skip"):
                decision = "post"

            results.append(SummarizedNews(
                original_title=item.title,
                card_title=parsed.get("card_title", "") if decision != "skip" else "",
                hashtags=parsed.get("hashtags", []) if decision != "skip" else [],
                source=item.source,
                link=item.link,
                decision=decision,
                skip_reason=parsed.get("skip_reason", "") if decision == "skip" else "",
                visual_concept=parsed.get("visual_concept", "") if decision != "skip" else "",
            ))
        except Exception as e:
            print(f"⚠️  요약 실패 ({item.title[:30]}...): {e}")
            # API 실패 시: 보수적으로 skip 처리 (안전 우선).
            # 원제목을 그대로 카드로 만드는 폴백은 안전 분류를 거치지 않아 위험.
            results.append(SummarizedNews(
                original_title=item.title,
                card_title="",
                hashtags=[],
                source=item.source,
                link=item.link,
                decision="skip",
                skip_reason=f"summarization_error: {type(e).__name__}",
            ))

    return results


def filter_postable(summaries: List[SummarizedNews]) -> List[SummarizedNews]:
    """skip된 항목 제거 + 결과 로깅"""
    postable = []
    for s in summaries:
        if s.decision == "skip":
            print(f"  ⊘ SKIP: {s.original_title[:50]} ({s.skip_reason})")
        else:
            postable.append(s)
    return postable


if __name__ == "__main__":
    from fetch_news import fetch_google_news_korea

    news = fetch_google_news_korea(limit=5)
    summaries = summarize_news(news)

    print("=" * 60)
    print("📝 요약 결과 (안전 분류 포함)")
    print("=" * 60)
    for i, s in enumerate(summaries, 1):
        print(f"\n[{i}] decision={s.decision}")
        print(f"    원제목: {s.original_title[:60]}")
        if s.decision == "skip":
            print(f"    SKIP 사유: {s.skip_reason}")
        else:
            print(f"    카드 제목: {s.card_title}")
            print(f"    해시태그: {' '.join(s.hashtags)}")
