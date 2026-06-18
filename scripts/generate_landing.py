"""
GitHub Pages 랜딩 페이지 생성 — IG bio 링크 타겟.

`docs/index.html` 정적 HTML 출력. 매 cron 게시 후 publish_matrix.py 가 호출.

[v2 변경]
- 단축링크가 설정된 카테고리만 노출 (수익 안 잡히는 검색 URL fallback 제거)
- 오늘의 토픽 기반 "오늘의 추천템" 히어로 카드 — 최신 게시와 직결
- 24h 라스트클릭 쿠키 극대화: 모든 외부 링크에 rel="sponsored nofollow"
  + 새 탭 열기 + 명시적 CTA 버튼
- 설정 미완료 카테고리는 "준비 중" 표시 (사용자 신뢰 ↑)
- 푸터: 공정위 디스클로저 + 마지막 갱신 시각 + 채널 링크

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
    CATEGORY_META, COUPANG_DISCLOSURE,
    TOPIC_TO_CATEGORY, get_shortlinks, coverage_report,
)
from topic_registry import TOPICS


DOCS_DIR = ROOT / "docs"
INSIGHTS_PATH = ROOT / "insights.json"


def _recent_posts(limit: int = 6):
    """insights.json 마지막 스냅샷에서 최근 게시 N건."""
    if not INSIGHTS_PATH.exists():
        return []
    try:
        d = json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))
        snaps = d.get("snapshots", [])
        if not snaps:
            return []
        posts = sorted(snaps[-1].get("posts", []),
                       key=lambda x: x.get("timestamp", ""), reverse=True)
        return posts[:limit]
    except Exception:
        return []


def _latest_topic_id():
    """가장 최근 게시의 토픽 추측 — 캡션 첫줄과 TOPICS 의 title 매칭."""
    posts = _recent_posts(1)
    if not posts:
        return None
    cap = (posts[0].get("caption_excerpt") or "").split("\n")[0].strip()
    for tid, t in TOPICS.items():
        if t["title"] and t["title"] in cap:
            return tid
    return None


def _hero_html(topic_id: str | None, links: dict) -> str:
    """오늘의 추천 히어로 카드. 토픽 카테고리에 링크 있으면 prominent CTA."""
    if not topic_id:
        return ""
    cat = TOPIC_TO_CATEGORY.get(topic_id)
    if not cat or cat not in links:
        return ""
    url = links[cat]
    emoji = CATEGORY_META.get(cat, {}).get("emoji", "🛒")
    hint = CATEGORY_META.get(cat, {}).get("search_hint", "")
    title = TOPICS[topic_id]["title"]
    return f"""
<a class="hero" href="{url}" target="_blank" rel="noopener nofollow sponsored">
  <div class="hero-badge">🔥 오늘의 추천템</div>
  <div class="hero-emoji">{emoji}</div>
  <div class="hero-title">{cat}</div>
  <div class="hero-sub">방금 올라온 「{title}」 보러 오신 분들께 ⬇️</div>
  <div class="hero-cta">쿠팡에서 바로 보기 →</div>
  <div class="hero-keywords">{hint}</div>
</a>"""


def _category_card(cat: str, url: str) -> str:
    emoji = CATEGORY_META.get(cat, {}).get("emoji", "🛒")
    hint = CATEGORY_META.get(cat, {}).get("search_hint", "")
    return f"""
    <a href="{url}" target="_blank" rel="noopener nofollow sponsored" class="card">
      <div class="emoji">{emoji}</div>
      <div class="cat">{cat}</div>
      <div class="sub">{hint}</div>
    </a>"""


def _post_row(post: dict) -> str:
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
    links = get_shortlinks()
    rep = coverage_report()
    latest_tid = _latest_topic_id()

    # 단축링크 설정된 카테고리만 정렬해서 노출
    configured = sorted(rep["configured_categories"])
    cards = "".join(_category_card(c, links[c]) for c in configured)
    if not cards:
        cards = (
            '<div class="empty">'
            '추천템을 준비하고 있어요. 인스타에서 매일 새로운 시리즈로 만나요!'
            '</div>'
        )

    hero = _hero_html(latest_tid, links)
    posts = "".join(_post_row(p) for p in _recent_posts(5))
    if not posts:
        posts = '<div class="empty">아직 추적된 게시물이 없어요</div>'

    now = datetime.now().strftime("%Y-%m-%d %H:%M KST")
    coverage_pct = (
        f'{rep["configured_topics"]}/{rep["total_topics"]} 토픽'
        if rep["revenue_active"] else '준비 중'
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="@daily_enter_kr — K-연예 매트릭스 + 오늘의 추천템">
<meta name="robots" content="index, follow">
<title>daily_enter_kr · 오늘의 추천템</title>
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
    line-height: 1.55;
  }}
  .wrap {{ max-width: 560px; margin: 0 auto; }}
  header {{ text-align: center; margin-bottom: 24px; }}
  .avatar {{
    width: 96px; height: 96px; border-radius: 50%;
    background: linear-gradient(135deg, #ff7eb6 0%, #ffd166 50%, #06d6a0 100%);
    margin: 0 auto 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 42px; box-shadow: 0 8px 32px rgba(255, 126, 182, 0.4);
  }}
  h1 {{ font-size: 22px; font-weight: 800; margin-bottom: 4px; }}
  .handle {{ color: #b8b3c8; font-size: 14px; margin-bottom: 14px; }}
  .ig-link {{
    display: inline-block; padding: 10px 24px; border-radius: 12px;
    background: linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045);
    color: white; text-decoration: none; font-weight: 600; font-size: 14px;
  }}

  /* 히어로 */
  .hero {{
    display: block; margin-top: 26px; padding: 22px 20px 18px;
    background: linear-gradient(135deg, rgba(255, 126, 182, 0.18) 0%, rgba(252, 176, 69, 0.18) 100%);
    border: 1.5px solid rgba(255, 209, 102, 0.45);
    border-radius: 20px;
    text-decoration: none; color: inherit;
    box-shadow: 0 8px 28px rgba(255, 126, 182, 0.18);
  }}
  .hero-badge {{
    display: inline-block; background: #ffd166; color: #2a1f00;
    padding: 4px 10px; border-radius: 8px;
    font-size: 11px; font-weight: 800; margin-bottom: 12px;
    letter-spacing: 0.5px;
  }}
  .hero-emoji {{ font-size: 56px; line-height: 1; margin-bottom: 8px; }}
  .hero-title {{ font-size: 22px; font-weight: 800; }}
  .hero-sub {{ color: #d8d3e8; font-size: 13px; margin: 4px 0 16px; }}
  .hero-cta {{
    display: inline-block; background: #fff; color: #1a1530;
    padding: 10px 20px; border-radius: 10px;
    font-weight: 800; font-size: 14px;
  }}
  .hero-keywords {{ color: #a8a3b8; font-size: 11px; margin-top: 10px; }}

  h2 {{ font-size: 16px; font-weight: 800; margin: 32px 0 14px;
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
  .card .sub {{ color: #a8a3b8; font-size: 12px; line-height: 1.4; }}
  .post {{
    display: block; text-decoration: none; color: inherit;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px; padding: 12px 14px; margin-bottom: 8px;
  }}
  .post-title {{ font-size: 14px; font-weight: 600; }}
  .post-meta {{ font-size: 12px; color: #a8a3b8; margin-top: 4px; }}
  .empty {{ color: #888; padding: 24px; text-align: center; font-size: 13px;
            background: rgba(255, 255, 255, 0.03); border-radius: 12px; }}
  footer {{
    margin-top: 40px; padding: 20px 16px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    font-size: 11px; color: #8a8595; line-height: 1.6;
    text-align: center;
  }}
  .updated {{ color: #6a6580; font-size: 10px; margin-top: 12px; }}
  .badge-status {{ display: inline-block; padding: 2px 8px; border-radius: 6px;
                   background: rgba(6, 214, 160, 0.2); color: #06d6a0;
                   font-size: 10px; font-weight: 700; margin-top: 6px; }}
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

  {hero}

  <h2>🛒 카테고리별 추천템</h2>
  <div class="grid">
    {cards}
  </div>

  <h2>📌 최근 게시</h2>
  {posts}

  <footer>
    {COUPANG_DISCLOSURE}
    <div class="updated">최근 업데이트: {now} · 추천템 {coverage_pct} 활성</div>
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
    rep = coverage_report()
    print(f"✓ {out} ({len(html):,} bytes)")
    status = "✅ ON" if rep["revenue_active"] else "⚠️  OFF (단축링크 0개 — data/coupang_shortlinks.csv 채우기 필요)"
    print(f"  수익 활성 상태: {status}")
    print(f"  카테고리: {len(rep['configured_categories'])}/{rep['total_categories']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
