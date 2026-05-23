"""
뉴스 요약 모듈
Claude API를 사용하여 뉴스를 인스타그램 카드뉴스용으로 요약합니다.

[비용 비교]
- Claude Haiku 4.5: 가장 저렴, 일 10건 ≈ $0.01
- Claude Sonnet 4.5: 품질↑, 일 10건 ≈ $0.05
- 추천: Haiku 4.5 (요약은 충분히 잘 함)
"""

import os
import json
from anthropic import Anthropic
from dataclasses import dataclass
from typing import List

# fetch_news.py의 NewsItem import
from fetch_news import NewsItem


@dataclass
class SummarizedNews:
    original_title: str
    card_title: str       # 카드 제목 (짧고 강렬하게)
    card_body: str        # 카드 본문 (2-3문장 요약)
    hashtags: list        # 추천 해시태그
    source: str
    link: str


SUMMARY_PROMPT = """너는 K-연예 인스타그램 카드뉴스 카피라이터다. 다음 뉴스를 인스타에서 스크롤을 멈추게 하는 카드뉴스로 만들어줘.

[뉴스 제목] {title}
[뉴스 내용/설명] {summary}
[출처] {source}

다음 JSON 형식으로만 응답해줘 (다른 텍스트 절대 포함하지 말 것):
{{
  "card_title": "12-20자, 호기심 자극하는 후킹 제목",
  "card_body": "70-110자 핵심 요약. 첫 문장은 후킹, 마지막 문장은 여운/궁금증.",
  "hashtags": ["#관련해시태그1", "#관련해시태그2", "#관련해시태그3", "#관련해시태그4"]
}}

[card_title 작성 규칙 — SEO 최적화]
- 인물명/작품명/숫자를 제목 앞쪽에 배치 (검색 최적화)
- 호기심 갭(curiosity gap) 활용: "왜", "결국", "충격", "전격", "최초", "갑자기" 같은 단어
- 줄임표(...)나 물음표(?)로 다음 슬라이드 클릭 욕구 자극 가능
- 단, '경악', '발칵' 같은 황색 표현, 허위 과장, 자극적 어휘는 금지 (인스타 정책 위반)
- 이모지(🔥❤️ 등)는 카드에서 두부박스로 깨지므로 절대 사용 금지. 텍스트만 사용

[card_body 작성 규칙]
- 객관적 사실 위주, 추측 금지
- 1문장: 핵심 사건/팩트를 강하게
- 2문장: 맥락 또는 반응
- 3문장(선택): 향후 전개/궁금증으로 마무리

[hashtags 작성 규칙]
- 한국어 + 영문 혼합 (검색 노출 확대)
- 인물/그룹명 직접 태그 (예: #뉴진스 #NewJeans)
- 장르 태그 (예: #K팝 #드라마 #영화 #예능)
- 메타 태그 (예: #핫이슈 #연예뉴스 #오늘의이슈)
- 4개 이상

[톤]
- "이거 안 보면 손해" 느낌이지만 품격 있게
- 팬들이 공유하고 싶게
"""


def summarize_news(news_items: List[NewsItem], api_key: str = None) -> List[SummarizedNews]:
    """뉴스 리스트를 카드뉴스용으로 요약"""
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    
    results = []
    for item in news_items:
        prompt = SUMMARY_PROMPT.format(
            title=item.title,
            summary=item.summary[:500],  # 너무 길면 토큰 낭비
            source=item.source,
        )
        
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",  # 가성비 최고
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            
            response_text = message.content[0].text.strip()
            # JSON만 추출 (혹시 ```json 같은 게 붙은 경우 제거)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            parsed = json.loads(response_text.strip())
            
            results.append(SummarizedNews(
                original_title=item.title,
                card_title=parsed["card_title"],
                card_body=parsed["card_body"],
                hashtags=parsed.get("hashtags", []),
                source=item.source,
                link=item.link,
            ))
        except Exception as e:
            print(f"⚠️  요약 실패 ({item.title[:30]}...): {e}")
            # 실패 시 원제목을 카드 제목으로, 본문은 비워서 깔끔하게 표시
            results.append(SummarizedNews(
                original_title=item.title,
                card_title=item.title,
                card_body="",
                hashtags=["#뉴스"],
                source=item.source,
                link=item.link,
            ))
    
    return results


if __name__ == "__main__":
    from fetch_news import fetch_google_news_korea
    
    # 테스트: 3건만
    news = fetch_google_news_korea(limit=3)
    summaries = summarize_news(news)
    
    print("=" * 60)
    print("📝 요약 결과")
    print("=" * 60)
    for i, s in enumerate(summaries, 1):
        print(f"\n[{i}] {s.card_title}")
        print(f"    본문: {s.card_body}")
        print(f"    해시태그: {' '.join(s.hashtags)}")
        print(f"    출처: {s.source}")
