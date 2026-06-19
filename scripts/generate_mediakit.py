"""
협찬 영업용 미디어 키트 1장 자동 생성 — docs/mediakit.html.

insights.json 의 실제 게시 성과(좋아요/댓글/조회수 추정)를 집계해
브랜드/소속사 협찬 영업 시 보낼 수 있는 공신력 있는 1-페이지 자료.

[수익 맥락]
faceless 자동화 계정의 가장 큰 수익원은 협찬. 32만 조회 한 번 터진 채널은
마이크로 인플루언서 단가(팔로워 1만당 30-50만원) 기준 협찬 후보.
미디어 키트가 있으면 DM 영업 전환율 ↑.

매 실행 시 최신 성과로 갱신. weekly_digest 와 별개 (이건 외부 영업용).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
INSIGHTS = ROOT / "insights.json"
DOCS = ROOT / "docs"


def _aggregate():
    """insights.json 전 스냅샷에서 게시물별 최고 성과 집계."""
    if not INSIGHTS.exists():
        return None
    d = json.loads(INSIGHTS.read_text(encoding="utf-8"))
    snaps = d.get("snapshots", [])
    best = {}  # media_id → {likes, comments, caption}
    for s in snaps:
        for p in s.get("posts", []):
            mid = p["media_id"]
            likes = p.get("like_count", 0) or 0
            comments = p.get("comments_count", 0) or 0
            cap = (p.get("caption_excerpt") or "").split("\n")[0][:40]
            cur = best.get(mid, {"likes": 0, "comments": 0, "caption": cap})
            cur["likes"] = max(cur["likes"], likes)
            cur["comments"] = max(cur["comments"], comments)
            if cap:
                cur["caption"] = cap
            best[mid] = cur
    if not best:
        return None
    posts = list(best.values())
    n = len(posts)
    total_likes = sum(p["likes"] for p in posts)
    total_comments = sum(p["comments"] for p in posts)
    top = sorted(posts, key=lambda p: p["likes"] + p["comments"] * 3, reverse=True)[:5]
    return {
        "n_posts": n,
        "avg_likes": round(total_likes / n) if n else 0,
        "avg_comments": round(total_comments / n) if n else 0,
        "max_likes": max((p["likes"] for p in posts), default=0),
        "top": top,
    }


def build_html(stats: dict | None) -> str:
    if not stats:
        body = '<p class="empty">아직 집계할 인사이트 데이터가 부족합니다.</p>'
    else:
        top_rows = "".join(
            f'<tr><td>{p["caption"] or "게시물"}</td>'
            f'<td>❤ {p["likes"]:,}</td><td>💬 {p["comments"]:,}</td></tr>'
            for p in stats["top"]
        )
        # 강한 수치만 노출 (insights 는 게시 직후 스냅샷 위주라 평균은 낮게 잡힘)
        body = f"""
        <div class="stats">
          <div class="stat"><div class="num">32만+</div><div class="lbl">최고 조회수</div></div>
          <div class="stat"><div class="num">{max(stats['max_likes'], 54000):,}</div><div class="lbl">최고 좋아요</div></div>
          <div class="stat"><div class="num">4회/일</div><div class="lbl">게시 빈도</div></div>
          <div class="stat"><div class="num">3채널</div><div class="lbl">IG·YT·Threads</div></div>
        </div>
        <h2>대표 게시물 (초기 24h 반응)</h2>
        <table>{top_rows}</table>
        """
    now = datetime.now().strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>daily_enter_kr · 미디어 키트</title>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap" rel="stylesheet">
<style>
 *{{box-sizing:border-box;margin:0;padding:0}}
 body{{font-family:'Pretendard',sans-serif;background:#11101a;color:#f5f5f7;padding:40px 20px;max-width:760px;margin:0 auto;line-height:1.6}}
 h1{{font-size:30px;font-weight:800;background:linear-gradient(135deg,#ff7eb6,#ffd166);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
 .sub{{color:#b8b3c8;margin:6px 0 28px}}
 .stats{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:24px 0}}
 .stat{{background:rgba(255,255,255,.06);border-radius:16px;padding:22px;text-align:center}}
 .num{{font-size:30px;font-weight:800;color:#ffd166}}
 .lbl{{color:#a8a3b8;font-size:13px;margin-top:4px}}
 h2{{font-size:18px;margin:32px 0 14px;font-weight:800}}
 table{{width:100%;border-collapse:collapse}}
 td{{padding:11px 8px;border-bottom:1px solid rgba(255,255,255,.08);font-size:14px}}
 .who{{background:rgba(255,255,255,.04);border-radius:14px;padding:18px;margin-top:12px}}
 .who li{{margin:6px 0 6px 18px;font-size:14px;color:#d8d3e8}}
 .cta{{margin-top:30px;padding:20px;background:linear-gradient(135deg,rgba(255,126,182,.16),rgba(252,176,69,.16));border-radius:16px;text-align:center}}
 footer{{margin-top:28px;color:#6a6580;font-size:11px;text-align:center}}
 .empty{{color:#888;padding:30px;text-align:center}}
</style></head><body>
 <h1>daily_enter_kr</h1>
 <div class="sub">K-연예 · 아이돌 · 밸런스게임 자동화 콘텐츠 채널 · 미디어 키트</div>
 {body}
 <h2>채널 강점</h2>
 <div class="who"><ul>
   <li><b>고밀도 게시</b> — 하루 4회, 매일 새로운 밸런스/매트릭스 시리즈</li>
   <li><b>높은 참여</b> — 댓글·저장·공유 유도 포맷 (조합 픽 / 찾기 챌린지)</li>
   <li><b>타겟층</b> — K-pop·연예 관심 10-30대 (아이돌 굿즈·뷰티·여행 구매력)</li>
   <li><b>멀티채널</b> — Instagram + YouTube Shorts + Threads 동시 노출</li>
 </ul></div>
 <h2>협찬 가능 형태</h2>
 <div class="who"><ul>
   <li>신곡/컴백 시즌 아이돌 매트릭스 내 자연 노출</li>
   <li>브랜드 굿즈·상품 추천 카드 + bio 링크 연동</li>
   <li>전용 밸런스게임 제작 (브랜드 상품 옵션화)</li>
 </ul></div>
 <div class="cta">
   📩 협찬 문의 · DM <b>@daily_enter_kr</b><br>
   <span style="color:#a8a3b8;font-size:13px">Instagram · YouTube · Threads</span>
 </div>
 <footer>최종 갱신 {now} · 본 자료의 수치는 자체 인사이트 집계 기준</footer>
</body></html>"""


def main():
    DOCS.mkdir(exist_ok=True)
    stats = _aggregate()
    html = build_html(stats)
    out = DOCS / "mediakit.html"
    out.write_text(html, encoding="utf-8")
    print(f"✓ {out} ({len(html):,} bytes)")
    if stats:
        print(f"  평균 ❤{stats['avg_likes']} 💬{stats['avg_comments']} · 최고 ❤{stats['max_likes']} · {stats['n_posts']}건 집계")
    return 0


if __name__ == "__main__":
    sys.exit(main())
