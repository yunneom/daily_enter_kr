"""
주간 인사이트 다이제스트 — insights.json 의 최근 7일 스냅샷을 분석해 HTML 보고서 생성.

[입력] insights.json (fetch_insights.py 가 매 실행마다 누적)
[출력] docs/digests/YYYY-WNN.html (한 주 단위)
[알림] Discord webhook (있을 때만)

[측정 메트릭 — Reels v2 인사이트 기준]
- plays (재생 횟수)
- reach (도달 — 고유 시청자)
- saved (저장 — retention 신호)
- shares (공유 — 2026 알고리즘 최상위 신호)
- like_count / comments_count (기본)
- total_interactions (종합)

[분석 차원]
- 24h 시점의 평균값 (게시 직후 안정화된 지표)
- 베스트 / 워스트 게시 5건 (reach 기준)
- 시계열 트렌드 (일별 평균 plays 추이)
- 캐시된 buckets (오전/오후, 요일별 — 자료 쌓이면 의미 있음)

다이제스트는 매주 일요일 또는 manual dispatch 시 생성. CI 워크플로우에서 호출.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent / "src"))
from notify import notify_discord  # noqa: E402


KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).parent
INSIGHTS_PATH = ROOT / "insights.json"
DIGEST_DIR = ROOT / "docs" / "digests"
WEEK_DAYS = 7


def _load_snapshots() -> List[Dict]:
    if not INSIGHTS_PATH.exists():
        return []
    try:
        data = json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))
        return data.get("snapshots", [])
    except Exception:
        return []


def _flatten_posts_last_n_days(snapshots: List[Dict], days: int) -> Dict[str, Dict]:
    """가장 최근의 각 media_id 별 인사이트 데이터를 반환.

    같은 게시물이 여러 스냅샷에 등장 → 가장 최근 스냅샷의 값을 채택 (안정화된 수치).
    """
    now = datetime.now(KST)
    cutoff = now - timedelta(days=days)
    latest_by_id: Dict[str, Dict] = {}
    for snap in snapshots:
        snap_at = snap.get("snapshot_at", "")
        try:
            snap_dt = datetime.fromisoformat(snap_at)
        except Exception:
            continue
        if snap_dt < cutoff:
            continue
        for p in snap.get("posts", []):
            mid = p.get("media_id")
            if not mid:
                continue
            existing = latest_by_id.get(mid)
            if existing is None:
                latest_by_id[mid] = {**p, "_snap_at": snap_at}
            else:
                # 더 최신 스냅샷의 데이터 채택
                if snap_at > existing.get("_snap_at", ""):
                    latest_by_id[mid] = {**p, "_snap_at": snap_at}
    return latest_by_id


def _safe(v, default=0):
    return v if isinstance(v, (int, float)) else default


def _summary_stats(posts: List[Dict]) -> Dict:
    """평균 / 중앙 / max / sum."""
    fields = ["plays", "reach", "saved", "shares", "total_interactions",
              "like_count", "comments_count"]
    out = {}
    for f in fields:
        vals = [_safe(p.get(f)) for p in posts if p.get(f) is not None]
        if not vals:
            out[f] = {"avg": 0, "median": 0, "max": 0, "sum": 0, "n": 0}
            continue
        out[f] = {
            "avg": round(mean(vals), 1),
            "median": round(median(vals), 1),
            "max": max(vals),
            "sum": sum(vals),
            "n": len(vals),
        }
    return out


def _top_n(posts: List[Dict], metric: str, n: int = 5) -> List[Dict]:
    return sorted(posts, key=lambda p: _safe(p.get(metric)), reverse=True)[:n]


def _format_post_line(p: Dict) -> str:
    title = (p.get("caption_excerpt") or "")[:60].replace("\n", " ")
    return (
        f"plays={p.get('plays','-')} reach={p.get('reach','-')} "
        f"saved={p.get('saved','-')} shares={p.get('shares','-')} "
        f"❤={p.get('like_count','-')} 💬={p.get('comments_count','-')} | {title}"
    )


def _iso_week(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _render_html(week_label: str, posts: List[Dict], stats: Dict) -> str:
    now = datetime.now(KST)

    def fmt_post_row(p: Dict) -> str:
        ts = p.get("timestamp", "")[:10]
        title = (p.get("caption_excerpt") or "").split("\n")[0][:70]
        link = p.get("permalink", "")
        return f"""
          <tr>
            <td class="num">{p.get('plays','-')}</td>
            <td class="num">{p.get('reach','-')}</td>
            <td class="num">{p.get('saved','-')}</td>
            <td class="num">{p.get('shares','-')}</td>
            <td class="num">{p.get('like_count','-')}</td>
            <td class="num">{p.get('comments_count','-')}</td>
            <td><span class="mono">{ts}</span></td>
            <td><a href="{link}" target="_blank">{title}</a></td>
          </tr>"""

    best = _top_n(posts, "reach", 5)
    worst = sorted(posts, key=lambda p: _safe(p.get("reach")))[:5]
    by_shares = _top_n(posts, "shares", 5)
    by_saved = _top_n(posts, "saved", 5)

    s = stats
    def sm(k, sub="avg"): return s.get(k, {}).get(sub, 0)

    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>주간 인사이트 — {week_label}</title>
<style>
  :root{{--bg:#0f1115;--panel:#161a22;--line:#262c38;--text:#e7e9ee;
    --muted:#9aa3b2;--accent:#7c9cff;--ok:#5dd39e;--warn:#ffb86b;--bad:#ff7a7a}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--text);
    font:14px/1.55 'Pretendard','Apple SD Gothic Neo',-apple-system,sans-serif}}
  .wrap{{max-width:1100px;margin:0 auto;padding:48px 24px}}
  h1{{font-size:30px;margin:0;letter-spacing:-.02em}}
  h2{{font-size:20px;margin:40px 0 14px;border-top:1px solid var(--line);padding-top:28px}}
  .sub{{color:var(--muted);margin-top:6px}}
  .kicker{{color:var(--accent);font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:700}}
  .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}
  @media(max-width:760px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
  .stat{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}}
  .stat .label{{color:var(--muted);font-size:11px;letter-spacing:.06em;text-transform:uppercase}}
  .stat .v{{font-size:24px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}}
  .stat .extra{{color:var(--muted);font-size:11.5px;margin-top:4px}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 20px}}
  th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
  th{{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
  td a{{color:var(--accent);text-decoration:none}} td a:hover{{text-decoration:underline}}
  .num{{font-variant-numeric:tabular-nums;text-align:right;width:64px}}
  .mono{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--muted);font-size:12px}}
  .footnote{{color:var(--muted);font-size:12px;margin-top:48px;border-top:1px solid var(--line);padding-top:18px}}
</style></head>
<body><div class="wrap">

<div class="kicker">weekly insights · 자동 생성</div>
<h1>{week_label} 주간 다이제스트</h1>
<div class="sub">@daily_enter_kr · 최근 7일 게시물 {len(posts)}건 분석 · 생성 {now.strftime('%Y-%m-%d %H:%M KST')}</div>

<h2>주요 지표 (게시별 평균)</h2>
<div class="grid">
  <div class="stat"><div class="label">평균 plays</div><div class="v">{sm('plays')}</div>
    <div class="extra">중앙값 {sm('plays','median')} · max {sm('plays','max')}</div></div>
  <div class="stat"><div class="label">평균 reach</div><div class="v">{sm('reach')}</div>
    <div class="extra">중앙값 {sm('reach','median')} · max {sm('reach','max')}</div></div>
  <div class="stat"><div class="label">평균 shares ⭐</div><div class="v">{sm('shares')}</div>
    <div class="extra">2026 알고리즘 최상위 신호 — 클수록 도달 ↑</div></div>
  <div class="stat"><div class="label">평균 saved</div><div class="v">{sm('saved')}</div>
    <div class="extra">retention 신호. 알고리즘 가점</div></div>
  <div class="stat"><div class="label">평균 ❤ likes</div><div class="v">{sm('like_count')}</div>
    <div class="extra">기본 engagement 지표</div></div>
  <div class="stat"><div class="label">평균 💬 댓글</div><div class="v">{sm('comments_count')}</div>
    <div class="extra">댓글 = 토론 유발 시그널</div></div>
  <div class="stat"><div class="label">총 interactions</div><div class="v">{sm('total_interactions','sum')}</div>
    <div class="extra">반응 모든 종류 합산 (주간)</div></div>
  <div class="stat"><div class="label">측정 게시물</div><div class="v">{len(posts)}</div>
    <div class="extra">최근 7일 (Reels 한정)</div></div>
</div>

<h2>도달(reach) 베스트 5</h2>
<table>
<thead><tr><th class="num">plays</th><th class="num">reach</th><th class="num">saved</th>
<th class="num">shares</th><th class="num">likes</th><th class="num">댓글</th>
<th>일자</th><th>제목</th></tr></thead>
<tbody>{''.join(fmt_post_row(p) for p in best)}</tbody>
</table>

<h2>공유(shares) 베스트 5 — 알고리즘 강한 시그널</h2>
<table>
<thead><tr><th class="num">plays</th><th class="num">reach</th><th class="num">saved</th>
<th class="num">shares</th><th class="num">likes</th><th class="num">댓글</th>
<th>일자</th><th>제목</th></tr></thead>
<tbody>{''.join(fmt_post_row(p) for p in by_shares)}</tbody>
</table>

<h2>저장(saved) 베스트 5</h2>
<table>
<thead><tr><th class="num">plays</th><th class="num">reach</th><th class="num">saved</th>
<th class="num">shares</th><th class="num">likes</th><th class="num">댓글</th>
<th>일자</th><th>제목</th></tr></thead>
<tbody>{''.join(fmt_post_row(p) for p in by_saved)}</tbody>
</table>

<h2>도달 워스트 5 — 약했던 게시</h2>
<table>
<thead><tr><th class="num">plays</th><th class="num">reach</th><th class="num">saved</th>
<th class="num">shares</th><th class="num">likes</th><th class="num">댓글</th>
<th>일자</th><th>제목</th></tr></thead>
<tbody>{''.join(fmt_post_row(p) for p in worst)}</tbody>
</table>

<h2>해석 가이드</h2>
<ul>
<li>📈 plays/reach 가 평균 300+ → P2(썸네일·다이제스트) 진행 권장</li>
<li>📊 100-300 → 콘텐츠는 OK, 수동 운영(스토리 리포스트·지인 DM) 병행 필요</li>
<li>📉 100 이하 → 포맷 피보팅 검토 (실제 영상 클립 / 다른 채널 분리 등)</li>
<li>⭐ shares 가 높은 게시의 카피 패턴을 다른 게시에 적용 — A/B 테스트로 검증</li>
<li>🔖 saved 높은 = "나중에 보고 싶다" 의도. 정보성 / 리스트형 콘텐츠 성과</li>
</ul>

<div class="footnote">
자동 생성 · weekly_digest.py · {now.isoformat()} · 데이터 소스: insights.json (fetch_insights.py)
</div>
</div></body></html>
"""


def main() -> int:
    snapshots = _load_snapshots()
    if not snapshots:
        print("⚠️  insights.json 비어있음 — 다이제스트 생성 스킵")
        return 0

    posts_map = _flatten_posts_last_n_days(snapshots, WEEK_DAYS)
    posts = list(posts_map.values())
    if not posts:
        print(f"⚠️  최근 {WEEK_DAYS}일 게시 없음 — 스킵")
        return 0

    stats = _summary_stats(posts)
    now = datetime.now(KST)
    week_label = _iso_week(now)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIGEST_DIR / f"{week_label}.html"
    out_path.write_text(_render_html(week_label, posts, stats), encoding="utf-8")

    # Discord 알림 — 핵심 지표만 요약
    s = stats
    msg = (
        f"📊 **{week_label} 주간 다이제스트**\n"
        f"게시 {len(posts)}건 분석 (최근 7일)\n"
        f"• 평균 plays: **{s['plays']['avg']}** · reach: **{s['reach']['avg']}**\n"
        f"• 평균 shares: **{s['shares']['avg']}** (알고리즘 최상위 신호)\n"
        f"• 평균 saved: **{s['saved']['avg']}** · likes: **{s['like_count']['avg']}**\n"
        f"📄 보고서: `docs/digests/{week_label}.html`"
    )
    sent = notify_discord(msg, username="daily_enter_kr digest")
    print(f"✓ 다이제스트 저장 → {out_path.relative_to(ROOT)}  ({len(posts)}건)")
    print(f"  Discord 알림: {'✅' if sent else '⏭️ 스킵 (DISCORD_WEBHOOK_URL 없음)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
