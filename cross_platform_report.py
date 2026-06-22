"""
크로스플랫폼 통합 분석 — 같은 콘텐츠(topic_id)가 IG Reels vs YouTube Shorts 에서
어떻게 다르게 도는지 비교 + abc 송 음원 퍼널/효과 추적.

[조인 구조]
  post_ledger.json   topic_id ↔ ig_media_id ↔ youtube_id ↔ bgm   (조인 키)
        ├── insights.json          ig_media_id → reach/shares/saved/plays/likes
        │     └── account 스냅샷    profile_views / website_clicks (abc 송 퍼널 프록시)
        └── insights_youtube.json  youtube_id  → views/retention   [#1, 2주 뒤 점등]

[출력]
  docs/digests/cross_platform.html  — 통합 대시보드
  Discord 요약 (webhook 있을 때)

[3개 섹션]
  1. abc 송 퍼널 — profile_views·website_clicks 일별 추세 (음원→프로필→bio→YT)
  2. 토픽별 IG↔YT 성과 비교 — 어느 플랫폼이 이 콘텐츠에 더 강한가
  3. BGM A/B — 음원별 평균 IG reach/shares/saved (abc_song vs 기존 ambient)

YouTube 인사이트 파일이 아직 없으면(=#1 미구현) YT 컬럼은 "대기" 로 표기하고
IG·퍼널·BGM 섹션만 채움 → 2주 뒤 #1 이 insights_youtube.json 을 만들면 자동 점등.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent / "src"))
from notify import notify_discord  # noqa: E402

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).parent
LEDGER_PATH = ROOT / "post_ledger.json"
IG_INSIGHTS_PATH = ROOT / "insights.json"
YT_INSIGHTS_PATH = ROOT / "insights_youtube.json"
DIGEST_DIR = ROOT / "docs" / "digests"
WINDOW_DAYS = 14


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe(v, default=0):
    return v if isinstance(v, (int, float)) else default


def _latest_ig_by_media(snapshots: List[Dict], days: int) -> Dict[str, Dict]:
    """media_id → 가장 최신 스냅샷의 게시물 인사이트 (window 내)."""
    now = datetime.now(KST)
    cutoff = now - timedelta(days=days)
    latest: Dict[str, Dict] = {}
    for snap in snapshots:
        sa = snap.get("snapshot_at", "")
        try:
            if datetime.fromisoformat(sa) < cutoff:
                continue
        except Exception:
            continue
        for p in snap.get("posts", []):
            mid = p.get("media_id")
            if not mid:
                continue
            if mid not in latest or sa > latest[mid].get("_snap_at", ""):
                latest[mid] = {**p, "_snap_at": sa}
    return latest


def _latest_yt_by_video(snapshots: List[Dict], days: int) -> Dict[str, Dict]:
    """video_id → 가장 최신 YT 인사이트. insights_youtube.json 구조:
    {snapshots:[{snapshot_at, videos:[{video_id, views, likes, comments,
                 average_view_percentage, avg_view_duration_sec}]}]}
    파일 없으면 빈 dict (= #1 미구현)."""
    now = datetime.now(KST)
    cutoff = now - timedelta(days=days)
    latest: Dict[str, Dict] = {}
    for snap in snapshots:
        sa = snap.get("snapshot_at", "")
        try:
            if datetime.fromisoformat(sa) < cutoff:
                continue
        except Exception:
            continue
        for v in snap.get("videos", []):
            vid = v.get("video_id")
            if not vid:
                continue
            if vid not in latest or sa > latest[vid].get("_snap_at", ""):
                latest[vid] = {**v, "_snap_at": sa}
    return latest


def _account_trend(snapshots: List[Dict], days: int) -> List[Dict]:
    """일별 account 인사이트 추세 (abc 송 퍼널). 스냅샷의 account 블록 사용."""
    now = datetime.now(KST)
    cutoff = now - timedelta(days=days)
    # 날짜별 마지막 스냅샷 값
    by_day: Dict[str, Dict] = {}
    for snap in snapshots:
        sa = snap.get("snapshot_at", "")
        acc = snap.get("account")
        if not acc:
            continue
        try:
            dt = datetime.fromisoformat(sa)
        except Exception:
            continue
        if dt < cutoff:
            continue
        day = dt.date().isoformat()
        if day not in by_day or sa > by_day[day].get("_snap_at", ""):
            by_day[day] = {**acc, "_snap_at": sa, "day": day}
    return [by_day[d] for d in sorted(by_day.keys())]


def build_report() -> Optional[Dict]:
    """조인 + 집계. 데이터 없으면 None."""
    ledger = _load_json(LEDGER_PATH, {"entries": []}).get("entries", [])
    ig = _load_json(IG_INSIGHTS_PATH, {"snapshots": []}).get("snapshots", [])
    yt_raw = _load_json(YT_INSIGHTS_PATH, {"snapshots": []})
    yt = yt_raw.get("snapshots", [])
    yt_available = YT_INSIGHTS_PATH.exists() and bool(yt)

    if not ledger:
        return None

    ig_by_media = _latest_ig_by_media(ig, WINDOW_DAYS)
    yt_by_video = _latest_yt_by_video(yt, WINDOW_DAYS)
    acct_trend = _account_trend(ig, WINDOW_DAYS)

    # window 내 원장 엔트리
    cutoff = (datetime.now(KST) - timedelta(days=WINDOW_DAYS)).isoformat()
    recent = [e for e in ledger if e.get("posted_at", "") >= cutoff]

    # ── 섹션 2: 토픽별 IG↔YT 조인 ──
    rows = []
    for e in recent:
        mid = e.get("ig_media_id")
        vid = e.get("youtube_id")
        ig_m = ig_by_media.get(mid, {})
        yt_m = yt_by_video.get(vid, {}) if vid else {}
        rows.append({
            "topic_id": e.get("topic_id"),
            "title": e.get("title", ""),
            "posted_at": e.get("posted_at", "")[:10],
            "bgm": e.get("bgm"),
            "ig_reach": _safe(ig_m.get("reach")),
            "ig_plays": _safe(ig_m.get("plays")),
            "ig_shares": _safe(ig_m.get("shares")),
            "ig_saved": _safe(ig_m.get("saved")),
            "ig_likes": _safe(ig_m.get("like_count")),
            "yt_id": vid,
            "yt_views": _safe(yt_m.get("views")) if yt_m else None,
            "yt_retention": _safe(yt_m.get("average_view_percentage")) if yt_m else None,
            "has_ig": bool(ig_m),
            "has_yt": bool(yt_m),
        })
    rows.sort(key=lambda r: r["ig_reach"], reverse=True)

    # ── 섹션 3: BGM A/B ──
    by_bgm = defaultdict(list)
    for r in rows:
        by_bgm[r["bgm"] or "(없음)"].append(r)
    bgm_stats = {}
    for bgm, group in by_bgm.items():
        def avg(f):
            vals = [g[f] for g in group if g[f] is not None]
            return round(mean(vals), 1) if vals else 0
        bgm_stats[bgm] = {
            "n": len(group),
            "ig_reach": avg("ig_reach"),
            "ig_shares": avg("ig_shares"),
            "ig_saved": avg("ig_saved"),
            "ig_likes": avg("ig_likes"),
        }

    return {
        "rows": rows,
        "bgm_stats": bgm_stats,
        "acct_trend": acct_trend,
        "yt_available": yt_available,
        "n_posts": len(recent),
        "n_yt_joined": sum(1 for r in rows if r["has_yt"]),
    }


def _render_html(rep: Dict) -> str:
    now = datetime.now(KST)
    rows = rep["rows"]
    bgm_stats = rep["bgm_stats"]
    acct = rep["acct_trend"]
    yt_on = rep["yt_available"]

    def yt_cell(r):
        if not yt_on:
            return '<td class="num muted">대기</td><td class="num muted">대기</td>'
        if not r["has_yt"]:
            return '<td class="num muted">—</td><td class="num muted">—</td>'
        ret = f'{r["yt_retention"]}%' if r["yt_retention"] is not None else "—"
        return f'<td class="num">{r["yt_views"]}</td><td class="num">{ret}</td>'

    topic_rows = "".join(f"""
      <tr>
        <td><span class="mono">{r['posted_at']}</span></td>
        <td>{(r['title'] or r['topic_id'])[:34]}</td>
        <td class="num">{r['ig_reach']}</td>
        <td class="num">{r['ig_shares']}</td>
        <td class="num">{r['ig_saved']}</td>
        {yt_cell(r)}
        <td class="bgm">{(r['bgm'] or '—')[:18]}</td>
      </tr>""" for r in rows[:40])

    bgm_rows = "".join(f"""
      <tr>
        <td><strong>{bgm[:24]}</strong>{' (표본 적음)' if m['n']<3 else ''}</td>
        <td class="num">{m['n']}</td>
        <td class="num">{m['ig_reach']}</td>
        <td class="num">{m['ig_shares']}</td>
        <td class="num">{m['ig_saved']}</td>
        <td class="num">{m['ig_likes']}</td>
      </tr>""" for bgm, m in sorted(bgm_stats.items(), key=lambda kv: -kv[1]["ig_reach"]))

    if acct:
        acct_rows = "".join(f"""
      <tr>
        <td><span class="mono">{a['day']}</span></td>
        <td class="num">{a.get('profile_views','—')}</td>
        <td class="num">{a.get('website_clicks','—')}</td>
        <td class="num">{a.get('reach','—')}</td>
        <td class="num">{a.get('follower_count','—')}</td>
      </tr>""" for a in acct)
        acct_section = f"""
<h2>1. abc 송 퍼널 — 계정 단위 추세</h2>
<p class="sub">오디오 → 프로필 방문(profile_views) → bio 링크 클릭(website_clicks=YT 도착).
IG API 는 오디오별 클릭을 노출하지 않으므로 이 계정 단위 추세가 음원 퍼널의 근사치입니다.</p>
<table>
<thead><tr><th>일자</th><th class="num">👤 프로필조회</th><th class="num">🔗 bio클릭</th>
<th class="num">📡 reach</th><th class="num">팔로워</th></tr></thead>
<tbody>{acct_rows}</tbody>
</table>
<p class="sub" style="font-size:12px">abc 송 도입일 전후로 profile_views·website_clicks 가 오르면 음원 효과 신호.</p>"""
    else:
        acct_section = """
<h2>1. abc 송 퍼널 — 계정 단위 추세</h2>
<p class="sub">아직 계정 인사이트 스냅샷이 없습니다. fetch_insights.py 가 v3 로 한 번 이상
실행되면 profile_views·website_clicks 추세가 여기 채워집니다.</p>"""

    yt_banner = ("" if yt_on else """
<div class="banner">⏳ YouTube 인사이트 미연동 — <code>insights_youtube.json</code> 이 생기면
(2주 뒤 #1 YT Shorts 인사이트 수집) YT views·retention 컬럼이 자동 점등됩니다.
현재는 IG·퍼널·BGM 섹션만 활성.</div>""")

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>크로스플랫폼 통합 분석 — @daily_enter_kr</title>
<style>
  :root{{--bg:#0f1115;--panel:#161a22;--line:#262c38;--text:#e7e9ee;
    --muted:#9aa3b2;--accent:#7c9cff;--ok:#5dd39e;--warn:#ffb86b}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--text);
    font:14px/1.55 'Pretendard','Apple SD Gothic Neo',-apple-system,sans-serif}}
  .wrap{{max-width:1100px;margin:0 auto;padding:48px 24px}}
  h1{{font-size:30px;margin:0;letter-spacing:-.02em}}
  h2{{font-size:20px;margin:40px 0 8px;border-top:1px solid var(--line);padding-top:28px}}
  .sub{{color:var(--muted);margin:6px 0 14px}}
  .kicker{{color:var(--accent);font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:700}}
  .banner{{background:#2a2410;border:1px solid var(--warn);border-radius:10px;
    padding:12px 16px;margin:18px 0;color:var(--warn);font-size:13px}}
  .banner code{{color:#ffd9a0}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 20px}}
  th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
  th{{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
  .num{{font-variant-numeric:tabular-nums;text-align:right;width:78px}}
  .muted{{color:var(--muted)}}
  .bgm{{font-size:11px;color:var(--muted)}}
  .mono{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--muted);font-size:12px}}
  .footnote{{color:var(--muted);font-size:12px;margin-top:48px;border-top:1px solid var(--line);padding-top:18px}}
</style></head><body><div class="wrap">

<div class="kicker">cross-platform · 자동 생성</div>
<h1>크로스플랫폼 통합 분석</h1>
<div class="sub">@daily_enter_kr · 최근 {WINDOW_DAYS}일 · 게시 {rep['n_posts']}건 ·
YT 조인 {rep['n_yt_joined']}건 · 생성 {now.strftime('%Y-%m-%d %H:%M KST')}</div>
{yt_banner}
{acct_section}

<h2>2. 토픽별 IG ↔ YouTube 성과</h2>
<p class="sub">같은 mp4 가 두 플랫폼에서 어떻게 다른지. reach 내림차순.</p>
<table>
<thead><tr><th>일자</th><th>토픽</th>
<th class="num">IG reach</th><th class="num">IG shares</th><th class="num">IG saved</th>
<th class="num">YT views</th><th class="num">YT retention</th><th>BGM</th></tr></thead>
<tbody>{topic_rows}</tbody>
</table>

<h2>3. BGM A/B — 음원별 평균 성과</h2>
<p class="sub">abc 송(전용 전환 후) vs 기존 ambient 의 IG 평균 reach/shares/saved 비교.</p>
<table>
<thead><tr><th>BGM</th><th class="num">n</th>
<th class="num">avg reach</th><th class="num">avg shares</th>
<th class="num">avg saved</th><th class="num">avg likes</th></tr></thead>
<tbody>{bgm_rows}</tbody>
</table>
<p class="sub" style="font-size:12px">전용 모드면 모든 게시가 같은 BGM → A/B 비교는
도입 전 기존 ambient 데이터가 window 에 남아있는 동안만 의미. 효과 보려면
초기엔 혼합 권장.</p>

<div class="footnote">
자동 생성 · cross_platform_report.py · {now.isoformat()}<br/>
소스: post_ledger.json (조인) · insights.json (IG) · insights_youtube.json (YT{' ✓' if yt_on else ' ⏳대기'})
</div>
</div></body></html>"""


def main() -> int:
    rep = build_report()
    if rep is None:
        print("⚠️  post_ledger.json 비어있음 — 크로스플랫폼 분석 스킵 "
              "(게시가 한 번 이상 원장에 기록되면 생성됨)")
        return 0

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    out = DIGEST_DIR / "cross_platform.html"
    out.write_text(_render_html(rep), encoding="utf-8")

    yt_state = "✓ 연동" if rep["yt_available"] else "⏳ 대기 (#1, 2주 뒤)"
    # BGM 요약 한 줄
    bgm_line = " · ".join(
        f"{k[:14]}:reach{v['ig_reach']}(n{v['n']})"
        for k, v in sorted(rep["bgm_stats"].items(), key=lambda kv: -kv[1]["ig_reach"])[:3]
    ) or "데이터 없음"
    msg = (
        f"📊 **크로스플랫폼 통합 분석**\n"
        f"최근 {WINDOW_DAYS}일 · 게시 {rep['n_posts']}건 · YT 조인 {rep['n_yt_joined']}건\n"
        f"• YouTube 인사이트: {yt_state}\n"
        f"• BGM A/B (avg reach): {bgm_line}\n"
        f"📄 보고서: `docs/digests/cross_platform.html`"
    )
    sent = notify_discord(msg, username="daily_enter_kr cross-platform")
    print(f"✓ 크로스플랫폼 보고서 → {out.relative_to(ROOT)}")
    print(f"  게시 {rep['n_posts']}건 · YT 조인 {rep['n_yt_joined']}건 · YT {yt_state}")
    print(f"  Discord: {'✅' if sent else '⏭️ 스킵'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
