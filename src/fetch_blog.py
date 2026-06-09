"""
티스토리 (또는 일반 RSS 2.0) 블로그 fetcher.

[설계]
- feedparser 로 RSS 가져오기 (User-Agent 필수: Tistory 등이 server-to-server 요청 차단)
- 각 포스트의 description HTML 에서 '핵심 요약' 블록 추출
- 블로그 글은 보통 doc 구조가 안정적 → 정규식으로 충분

[데이터 형태]
BlogPost(
    guid=str,          # 고유 ID (dedup 기준)
    url=str,           # 원문 링크
    title=str,
    pub_date=str,
    categories=list,   # 해시태그 변환 후보
    summary_bullets=list,  # 핵심 요약 (없으면 빈 list)
    body_excerpt=str,  # 본문 첫 200자 (없을 때 폴백 카드 콘텐츠)
)
"""

import os
import re
import time
import feedparser
import requests
from dataclasses import dataclass, field
from html import unescape
from typing import List, Optional


DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


@dataclass
class BlogPost:
    guid: str
    url: str
    title: str
    pub_date: str
    categories: List[str] = field(default_factory=list)
    summary_bullets: List[str] = field(default_factory=list)
    body_excerpt: str = ""


def _fetch_rss_raw(rss_url: str, timeout: int = 20) -> Optional[str]:
    """Tistory 등은 feedparser 기본 UA 거부 → 명시 UA 로 requests 가져와서 feedparser 에 전달.

    실패 시 None.
    """
    try:
        resp = requests.get(
            rss_url,
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=timeout,
        )
        if not resp.ok:
            print(f"  ❌ RSS HTTP {resp.status_code} from {rss_url}")
            print(f"     첫 200자: {resp.text[:200]}")
            return None
        return resp.text
    except Exception as e:
        print(f"  ❌ RSS fetch 예외: {type(e).__name__}: {e}")
        return None


_RE_HSUMMARY_BLOCK = re.compile(
    r"<blockquote[^>]*>.*?(?:핵심\s*요약|핵심요약|Summary).*?<ul[^>]*>(.*?)</ul>.*?</blockquote>",
    re.DOTALL | re.IGNORECASE,
)
_RE_LI = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL | re.IGNORECASE)
_RE_ALL_TAGS = re.compile(r"<[^>]+>")
_RE_NBSP_AND_WS = re.compile(r"[ \s]+")


def _strip_html(s: str) -> str:
    """HTML 태그 제거 + 공백 정리 + HTML entity 해제."""
    s = _RE_ALL_TAGS.sub("", s)
    s = unescape(s)
    s = _RE_NBSP_AND_WS.sub(" ", s).strip()
    return s


def _extract_summary_bullets(description_html: str) -> List[str]:
    """description HTML 에서 첫 'blockquote ... 핵심 요약 ... ul ... /ul ... /blockquote' 의 li 들 추출.

    없으면 빈 리스트.
    """
    m = _RE_HSUMMARY_BLOCK.search(description_html)
    if not m:
        return []
    ul_inner = m.group(1)
    bullets = []
    for li_m in _RE_LI.finditer(ul_inner):
        text = _strip_html(li_m.group(1))
        if text:
            bullets.append(text)
    return bullets


def _extract_body_excerpt(description_html: str, max_chars: int = 200) -> str:
    """blockquote 이후 첫 평문 부분 추출 — 핵심 요약 없을 때 카드 폴백용."""
    # blockquote 통째로 제거
    cleaned = re.sub(r"<blockquote[^>]*>.*?</blockquote>",
                     "", description_html, flags=re.DOTALL)
    # 이미지 태그 제거
    cleaned = re.sub(r"<img[^>]*>", "", cleaned)
    # 헤딩 제거 (제목성 텍스트는 제외)
    cleaned = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", cleaned, flags=re.DOTALL)
    text = _strip_html(cleaned)
    return text[:max_chars]


def fetch_blog_posts(rss_url: str, limit: int = 20) -> List[BlogPost]:
    """RSS 최신 N개 포스트 → BlogPost 리스트. About 페이지 같은 메타 항목은 제외."""
    raw = _fetch_rss_raw(rss_url)
    if not raw:
        return []

    feed = feedparser.parse(raw)
    if feed.bozo and not feed.entries:
        print(f"  ❌ RSS 파싱 실패: {feed.bozo_exception}")
        return []

    posts = []
    for entry in feed.entries[:limit]:
        guid = entry.get("id") or entry.get("guid") or entry.get("link", "")
        url = entry.get("link", "")
        title = (entry.get("title") or "").strip()

        # About 페이지 / 메타 페이지 제외 — URL 에 /pages/ 패턴
        if "/pages/" in url.lower() or title.lower() in ("about", "소개"):
            continue

        description = entry.get("description") or entry.get("summary") or ""
        bullets = _extract_summary_bullets(description)
        excerpt = _extract_body_excerpt(description) if not bullets else ""

        categories = []
        for tag in entry.get("tags", []) or []:
            term = tag.get("term") if isinstance(tag, dict) else None
            if term:
                categories.append(term)

        posts.append(BlogPost(
            guid=guid,
            url=url,
            title=title,
            pub_date=entry.get("published", ""),
            categories=categories,
            summary_bullets=bullets,
            body_excerpt=excerpt,
        ))
    return posts


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://editor60277.tistory.com/rss"
    print(f"🔍 RSS 가져오기: {url}")
    posts = fetch_blog_posts(url, limit=5)
    print(f"  → {len(posts)}건 (About 제외)")
    for i, p in enumerate(posts, 1):
        print(f"\n[{i}] {p.title}")
        print(f"  URL: {p.url}")
        print(f"  카테고리: {p.categories}")
        print(f"  핵심 요약 bullets ({len(p.summary_bullets)}개):")
        for b in p.summary_bullets:
            print(f"    • {b}")
        if not p.summary_bullets and p.body_excerpt:
            print(f"  본문 발췌: {p.body_excerpt[:120]}...")
