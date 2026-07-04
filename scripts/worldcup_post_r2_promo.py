"""
결승 대진 홍보 Reel — HP(HTML→Playwright→MP4).

4강 결과로 확정된 결승·3·4위전 대진을 대형 배틀 카드로 시각화.
결승 게시 이후 실행되므로 "지금 투표 진행중" CTA 사용.
실행: python scripts/worldcup_post_r2_promo.py [--dry-run]
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from post_instagram import InstagramPublisher, upload_video  # noqa
import post_ledger  # noqa

TOPIC_ID = "worldcup_r2_finals_promo"

GROUP_COLORS = {
    "아이브":    "#2563eb",
    "에스파":    "#7c3aed",
    "블랙핑크":  "#db2777",
    "소녀시대":  "#d97706",
    "엔믹스":    "#059669",
    "뉴진스":    "#0891b2",
    "르세라핌":  "#dc2626",
}
DEFAULT_COLOR = "#6b7280"

# 매치 타입별 배지 (결승전 vs 3·4위전 명확 구분 — "결승 두경기" 혼동 방지)
TYPE_BADGE = {
    "final":       ("결승전",   "#fbbf24", "#1a1206"),
    "third_place": ("3·4위전",  "#cd8f52", "#1a1206"),
}


def _group_color(group: str) -> str:
    return GROUP_COLORS.get(group, DEFAULT_COLOR)


def _order_matches(matches: list) -> list:
    """결승전 먼저, 3·4위전 뒤 (사용자 요청 순서)."""
    return sorted(matches, key=lambda m: 0 if m.get("type") == "final" else 1)


def _match_card_html(m: dict, delay_ms: int) -> str:
    a = m["a"]
    b = m["b"]
    col_a = _group_color(a["group"])
    col_b = _group_color(b["group"])
    b_label, b_bg, b_fg = TYPE_BADGE.get(m.get("type", ""), ("대진", "#6b7280", "#fff"))
    return f"""
<div class="match" style="animation-delay:{delay_ms}ms">
  <div class="match-badge" style="background:{b_bg};color:{b_fg};">{b_label}</div>
  <div class="match-body">
    <div class="side side-a" style="background:linear-gradient(135deg,{col_a}22,{col_a}08);">
      <div class="rank" style="color:{col_a};">#{a['rank']}</div>
      <div class="name">{a['member']}</div>
      <div class="group-tag" style="background:{col_a}33;color:{col_a};">{a['group']}</div>
    </div>
    <div class="vs-col"><div class="vs">VS</div></div>
    <div class="side side-b" style="background:linear-gradient(135deg,{col_b}08,{col_b}22);">
      <div class="rank" style="color:{col_b};">#{b['rank']}</div>
      <div class="name">{b['member']}</div>
      <div class="group-tag" style="background:{col_b}33;color:{col_b};">{b['group']}</div>
    </div>
  </div>
</div>"""


def _make_html(matches: list) -> str:
    matches = _order_matches(matches)
    cards = "\n".join(_match_card_html(m, 200 + i * 260) for i, m in enumerate(matches))
    footer_delay = 200 + len(matches) * 260 + 400
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box;
       font-family:'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
  body {{
    width:1080px; height:1920px; overflow:hidden;
    background:linear-gradient(160deg,#080618 0%,#14063a 45%,#230947 100%);
    color:#fff; display:flex; flex-direction:column;
    align-items:center; padding:88px 56px 68px;
  }}
  .header {{ text-align:center; animation:fadeDown .55s ease both; }}
  .pill {{
    display:inline-flex; align-items:center; gap:10px;
    background:#fbbf24; color:#000; font-size:30px; font-weight:800;
    letter-spacing:1px; padding:12px 34px; border-radius:40px; margin-bottom:24px;
  }}
  .header h1 {{
    font-size:100px; font-weight:900; line-height:1.05;
    background:linear-gradient(90deg,#fff 0%,#c4b5fd 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }}
  .header .sub {{ margin-top:18px; font-size:34px; color:rgba(255,255,255,.7); font-weight:500; }}
  /* 매치 그룹을 헤더~푸터 사이 중앙에 배치 → 하단 빈 공간 제거 */
  .matches {{ flex:1; width:100%; display:flex; flex-direction:column;
              justify-content:center; gap:34px; }}
  .match {{
    width:100%; position:relative; background:rgba(255,255,255,.05);
    border:1px solid rgba(255,255,255,.12); border-radius:24px; overflow:hidden;
    opacity:0; transform:translateY(38px); animation:slideUp .5s ease forwards;
  }}
  .match-badge {{
    font-size:34px; font-weight:900; letter-spacing:2px; text-align:center;
    padding:16px 0;
  }}
  .match-body {{ display:flex; align-items:stretch; }}
  .side {{ flex:1; padding:40px 24px; display:flex; flex-direction:column;
           align-items:center; justify-content:center; gap:14px; text-align:center; }}
  .rank {{ font-size:28px; font-weight:800; letter-spacing:1px; }}
  .name {{ font-size:64px; font-weight:900; line-height:1.1; word-break:keep-all; }}
  .group-tag {{ font-size:25px; font-weight:700; padding:6px 22px; border-radius:22px; }}
  .vs-col {{ width:100px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
  .vs {{ font-size:42px; font-weight:900; color:rgba(255,255,255,.9);
         text-shadow:0 0 20px rgba(255,255,255,.4); }}
  .footer {{ text-align:center; opacity:0;
             animation:fadeUp .5s {footer_delay}ms ease both; }}
  .cta-box {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.2);
              border-radius:18px; padding:28px 44px; margin-bottom:20px; }}
  .cta-main {{ font-size:42px; font-weight:800; color:#fbbf24; margin-bottom:8px; }}
  .cta-sub {{ font-size:27px; color:rgba(255,255,255,.7); }}
  .handle {{ font-size:28px; color:rgba(255,255,255,.45); font-weight:500; }}
  @keyframes fadeDown {{ from {{opacity:0;transform:translateY(-28px);}} to {{opacity:1;transform:translateY(0);}} }}
  @keyframes slideUp {{ to {{opacity:1;transform:translateY(0);}} }}
  @keyframes fadeUp {{ from {{opacity:0;transform:translateY(20px);}} to {{opacity:1;transform:translateY(0);}} }}
</style>
</head>
<body>
  <div class="header">
    <div class="pill">대진 확정</div>
    <h1>결승 라인업</h1>
    <div class="sub">결승전 · 3·4위전 동시 투표 · 우승 발표 내일 낮 12시 30분</div>
  </div>
  <div class="matches">
{cards}
  </div>
  <div class="footer">
    <div class="cta-box">
      <div class="cta-main">지금 게시글에서 댓글 투표</div>
      <div class="cta-sub">팔로우 + 알림 ON → 우승 발표 즉시 알림</div>
    </div>
    <div class="handle">@daily_enter_kr</div>
  </div>
</body>
</html>"""


def main():
    dry_run = "--dry-run" in sys.argv

    if not dry_run:
        ledger = post_ledger.load_ledger()
        if any((e.get("topic_id") or "") == TOPIC_ID for e in ledger.get("entries", [])):
            print(f"✅ {TOPIC_ID} 이미 게시됨 — skip")
            return 0

    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    matches = bracket.get("rounds", {}).get("R2", {}).get("matches", [])
    if not matches:
        print("❌ R2 매치 없음 (fix_bracket_r4_winners 먼저 실행 필요)")
        return 1

    out_dir = ROOT / "output_enter" / "publish" / "worldcup_r2_promo"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "r2_promo.html"
    html_path.write_text(_make_html(matches), encoding="utf-8")
    print(f"✓ HTML 생성: {html_path}")
    print("  준결승:", " / ".join(f"{m['a']['member']} vs {m['b']['member']}" for m in matches))

    if dry_run:
        print(f"🔍 dry-run — HTML만 생성, 게시 안 함: {html_path}")
        return 0

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    from render_hf import render_html_to_mp4  # noqa
    mp4_path = out_dir / "r2_promo.mp4"
    rc = render_html_to_mp4(html_path, mp4_path, duration=7.0, fps=30)
    if rc != 0 or not mp4_path.exists():
        print(f"❌ Playwright 렌더 실패 rc={rc}")
        return 1
    print(f"✓ MP4: {mp4_path} ({mp4_path.stat().st_size // 1024}KB)")

    video_url = upload_video(mp4_path)
    print(f"✓ Cloudinary: {video_url}")

    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1

    ordered = _order_matches(matches)
    names = [m["a"]["member"] for m in ordered] + [m["b"]["member"] for m in ordered]
    pair_lines = "\n".join(
        f"{TYPE_BADGE.get(m.get('type', ''), ('대진',))[0]}: "
        f"{m['a']['member']} vs {m['b']['member']}"
        for m in ordered
    )
    caption = (
        "걸그룹 월드컵 결승 라인업 확정!\n\n"
        f"{pair_lines}\n\n"
        "각 경기 게시글에서 지금 댓글로 투표할 수 있습니다.\n"
        "팔로우 + 알림 ON → 우승 발표 즉시 알림\n\n"
        "#걸그룹월드컵 #결승전 #케이팝 #kpop #아이돌투표 "
        + " ".join("#" + n for n in names)
    )
    media_id = publisher.post_reel(video_url, caption, cover_url=None, share_to_feed=True)
    print(f"✅ 결승 대진 홍보 릴스 게시 완료! {media_id}")

    post_ledger.record_results([{
        "ok": True,
        "topic_id": TOPIC_ID,
        "title": "걸그룹 월드컵 결승 대진 홍보",
        "style": "worldcup_r2_promo",
        "seed": None,
        "media_id": media_id,
        "platform": "instagram",
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
