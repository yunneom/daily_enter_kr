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


SUMMARY_PROMPT = """다음 뉴스를 인스타그램 카드뉴스용으로 요약해줘.

[뉴스 제목] {title}
[뉴스 내용/설명] {summary}
[출처] {source}

다음 JSON 형식으로만 응답해줘 (다른 텍스트 절대 포함하지 말 것):
{{
  "card_title": "10-15자 이내의 강렬한 제목",
  "card_body": "60-100자 이내의 핵심 요약 2-3문장",
  "hashtags": ["#관련해시태그1", "#관련해시태그2", "#관련해시태그3"]
}}

규칙:
- card_title은 클릭을 유도하되 자극적이지 않게
- card_body는 객관적 사실 위주로, 추측이나 의견 배제
- 해시태그는 3-5개, 한국어 위주
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
            # 실패 시 원본 제목만이라도 사용
            results.append(SummarizedNews(
                original_title=item.title,
                card_title=item.title[:15],
                card_body=item.title,
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
