"""
GitHub Pages 랜딩 페이지 생성 — IG bio 링크 타겟.

`docs/index.html` 정적 HTML 출력. 매 cron 게시 후 publish_matrix.py 가 호출.
- 토픽별 카테고리 → 쿠팡 어필리에이트 링크 그리드
- 최근 게시 5건(insights.json 기반) 하이라이트
- 모바일 우선 (다크 톤 + 부드러운 그라데이션)
- 필수 공지: 쿠팡 파트너스 디스클로저 푸터

GitHub Pages 활성화:
  Repo Settings → Pages → Source: Deploy from a branch → Branch: main /docs
  → 결과 URL: https://yunneom.github.io/daily_enter_kr/
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from coupang_affiliate import (
    CATEGORY_EMOJI, CATEGORY_QUERIES, COUPANG_DISCLOSURE,
    TOPIC_TO_CATEGORY, get_affiliate_url,
)
from topic_registry import TOPICS


DOCS_DIR = ROOT / "docs"


def _recent_posts(limit: int = 5):
    """insights.json 마지막 스냅샷에서 최근 게시 5건."""
    p = ROOT / "insights.json"
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        snaps = d.get("snapshots", [])
        if not snaps:
            return []
        posts = sorted(snaps[-1].get("posts", []),
                       key=lambda x: x.get("timestamp", ""), reverse=True)
        return posts[:limit]
    except Exception:
        return []


def _category_card(category: str) -> str:
    """카테고리 1개 카드 HTML."""
    emoji = CATEGORY_EMOJI.get(category, "🛒")
    query = CATEGORY_QUERIES.get(category, category)
    url = get_affiliate_url(category)
    return f"""
    <a href="{url}" target="_blank" rel="noopener nofollow sponsored" class="card">
      <div class="emoji">{emoji}</div>
      <div class="cat">{category}</div>
      <div class="sub">{query} 추천</div>
    </a>"""


def _recent_post_row(post: dict) -> str:
    """최근 게시 1개 행 HTML."""
    cap = (post.get("caption_excerpt") or "").strip().split("\n")[0][:36]
    link = post.get("permalink", "#")
    likes = post.get("like_count", 0)
    comments = post.get("comments_count", 0)
    return f"""
    <a href="{link}" target="_blank" rel="noopener" class="post">
      <div class="post-title">{cap or '게시물'}</div>
      <div class="post-meta">❤ {likes:,} · 💬 {comments:,}</div>
    </a>"""


def build_html() -> str:
    """전체 HTML 빌드."""
    # 고유 카테고리 (중복 제거, 순서 유지)
    seen, categories = set(), []
    for tid in TOPICS:
        cat = TOPIC_TO_CATEGORY.get(tid)
        if cat and cat not in seen:
            seen.add(cat)
            categories.append(cat)

    cards = "".join(_category_card(c) for c in categories)
    posts = "".join(_recent_post_row(p) for p in _recent_posts(5))
    if not posts:
        posts = '<div class="empty">아직 추적된 게시물이 없어요</div>'

    now = datetime.now().strftime("%Y-%m-%d %H:%M KST")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="@daily_enter_kr — K-연예 매트릭스 + 추천 쇼핑">
<title>daily_enter_kr · 추천템 모음</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(180deg, #0f0e14 0%, #1a1530 100%);
    color: #f5f5f7;
    min-height: 100vh;
    padding: 24px 16px 80px;
    line-height: 1.5;
  }}
  .wrap {{ max-width: 560px; margin: 0 auto; }}
  header {{ text-align: center; margin-bottom: 32px; }}
  .avatar {{
    width: 96px; height: 96px; border-radius: 50%;
    background: linear-gradient(135deg, #ff7eb6 0%, #ffd166 50%, #06d6a0 100%);
    margin: 0 auto 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 42px; box-shadow: 0 8px 32px rgba(255, 126, 182, 0.4);
  }}
  h1 {{ font-size: 22px; font-weight: 800; margin-bottom: 4px; }}
  .handle {{ color: #b8b3c8; font-size: 14px; margin-bottom: 16px; }}
  .ig-link {{
    display: inline-block; padding: 10px 24px; border-radius: 12px;
    background: linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045);
    color: white; text-decoration: none; font-weight: 600; font-size: 14px;
  }}
  h2 {{ font-size: 16px; font-weight: 800; margin: 28px 0 14px;
        color: #fff; display: flex; align-items: center; gap: 8px; }}
  h2::before {{ content: ''; width: 4px; height: 16px; background: #ff7eb6;
                border-radius: 2px; display: inline-block; }}
  .grid {{
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
  }}
  .card {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px; padding: 18px 14px;
    text-decoration: none; color: inherit;
    transition: transform 0.15s, background 0.15s;
    display: block;
  }}
  .card:hover, .card:active {{
    transform: translateY(-2px);
    background: rgba(255, 255, 255, 0.10);
  }}
  .card .emoji {{ font-size: 32px; margin-bottom: 8px; }}
  .card .cat {{ font-weight: 800; font-size: 15px; margin-bottom: 2px; }}
  .card .sub {{ color: #a8a3b8; font-size: 12px; }}
  .post {{
    display: block; text-decoration: none; color: inherit;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px; padding: 12px 14px; margin-bottom: 8px;
  }}
  .post-title {{ font-size: 14px; font-weight: 600; }}
  .post-meta {{ font-size: 12px; color: #a8a3b8; margin-top: 4px; }}
  .empty {{ color: #888; padding: 16px; text-align: center; font-size: 13px; }}
  footer {{
    margin-top: 40px; padding: 20px 16px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    font-size: 11px; color: #8a8595; line-height: 1.6;
    text-align: center;
  }}
  .updated {{ color: #6a6580; font-size: 10px; margin-top: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="avatar">📰</div>
    <h1>daily_enter_kr</h1>
    <div class="handle">매일 새로운 밸런스 시리즈</div>
    <a class="ig-link" href="https://www.instagram.com/daily_enter_kr/" target="_blank" rel="noopener">📷 인스타 팔로우</a>
  </header>

  <h2>🛒 오늘의 추천템</h2>
  <div class="grid">
    {cards}
  </div>

  <h2>📌 최근 게시</h2>
  {posts}

  <footer>
    {COUPANG_DISCLOSURE}
    <div class="updated">최근 업데이트: {now}</div>
  </footer>
</div>
</body>
</html>
"""


def main():
    DOCS_DIR.mkdir(exist_ok=True)
    html = build_html()
    out = DOCS_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✓ {out} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
