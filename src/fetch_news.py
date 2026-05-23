"""
뉴스 수집 모듈
네이버 뉴스 검색 RSS를 활용하여 핫토픽 뉴스를 수집합니다.

[중요] 네이버는 직접 크롤링을 차단하고 있으므로,
공식적으로 제공하는 RSS 피드 또는 검색 API를 사용해야 합니다.

방법 1: 네이버 검색 OpenAPI (권장) - 클라이언트 ID 필요
방법 2: 주요 언론사의 RSS 피드 직접 구독
방법 3: 구글 뉴스 RSS (한국어 필터)
"""

import feedparser
import requests
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    published: str
    source: str


# ============================================================
# 옵션 A: 구글 뉴스 RSS (한국어, 즉시 사용 가능 - 추천)
# ============================================================
def fetch_google_news_korea(topic: str = "entertainment", limit: int = 10) -> List[NewsItem]:
    """
    구글 뉴스 한국판 RSS에서 핫토픽 뉴스 수집.
    별도 API 키 불필요, 즉시 사용 가능.

    Args:
        topic: 카테고리. "entertainment"(연예), "sports", "technology", "headlines"(종합)
        limit: 최대 수집 건수
    """
    # 카테고리별 Google News RSS URL
    TOPIC_URLS = {
        "headlines":     "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "entertainment": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ko&gl=KR&ceid=KR:ko",
        "sports":        "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
        "technology":    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko",
        "business":      "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    }
    url = TOPIC_URLS.get(topic, TOPIC_URLS["entertainment"])

    feed = feedparser.parse(url)
    items = []

    for entry in feed.entries[:limit]:
        # 구글뉴스 제목은 "제목 - 언론사" 형식
        title_parts = entry.title.rsplit(" - ", 1)
        title = title_parts[0]
        source = title_parts[1] if len(title_parts) > 1 else "Unknown"

        items.append(NewsItem(
            title=title,
            link=entry.link,
            summary=entry.get("summary", ""),
            published=entry.get("published", ""),
            source=source,
        ))

    return items


# ============================================================
# 옵션 B: 네이버 검색 OpenAPI (공식, 클라이언트 ID 필요)
# https://developers.naver.com/apps/ 에서 발급
# ============================================================
def fetch_naver_news_api(
    client_id: str,
    client_secret: str,
    query: str = "오늘 뉴스",
    limit: int = 10,
) -> List[NewsItem]:
    """
    네이버 검색 OpenAPI를 사용한 뉴스 검색 (공식 방식)
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": limit,
        "sort": "date",  # 또는 "sim" (정확도순)
    }
    
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    
    items = []
    for item in data.get("items", []):
        # HTML 태그 제거
        title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        desc = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        
        items.append(NewsItem(
            title=title,
            link=item["link"],
            summary=desc,
            published=item["pubDate"],
            source="네이버 뉴스",
        ))
    
    return items


# ============================================================
# 옵션 C: 주요 언론사 RSS 직접 구독
# ============================================================
KOREAN_NEWS_RSS = {
    "연합뉴스": "https://www.yonhapnewstv.co.kr/feed/",
    "한겨레": "https://www.hani.co.kr/rss/",
    "조선일보": "https://www.chosun.com/arc/outboundfeeds/rss/",
    "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "SBS": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01",
}


def fetch_from_multiple_sources(limit_per_source: int = 3) -> List[NewsItem]:
    """여러 언론사 RSS에서 균형 있게 수집"""
    all_items = []
    for source_name, rss_url in KOREAN_NEWS_RSS.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:limit_per_source]:
                all_items.append(NewsItem(
                    title=entry.title,
                    link=entry.link,
                    summary=entry.get("summary", ""),
                    published=entry.get("published", ""),
                    source=source_name,
                ))
        except Exception as e:
            print(f"⚠️  {source_name} 수집 실패: {e}")
    
    return all_items


if __name__ == "__main__":
    # 테스트: 구글 뉴스로 핫토픽 10건 가져오기
    print("=" * 60)
    print("📰 구글 뉴스 한국판 핫토픽 TOP 10")
    print("=" * 60)
    news = fetch_google_news_korea(limit=10)
    for i, item in enumerate(news, 1):
        print(f"\n[{i}] {item.title}")
        print(f"    출처: {item.source}")
        print(f"    링크: {item.link[:80]}...")
