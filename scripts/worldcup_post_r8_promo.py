"""
8강 매치 홍보 Reel — HP(HTML→Playwright→MP4) 방식.

각 매치를 대형 배틀 카드로 시각화.
실행: python scripts/worldcup_post_r8_promo.py [--dry-run]
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

TOPIC_ID = "worldcup_r8_match_promo"

GROUP_COLORS = {
    "아이브":    "#2563eb",   # 블루
    "에스파":    "#7c3aed",   # 퍼플
    "블랙핑크":  "#db2777",   # 핑크
    "소녀시대":  "#d97706",   # 골드
    "엔믹스":    "#059669",   # 그린
    "뉴진스":    "#0891b2",   # 시안
    "르세라핌":  "#dc2626",   # 레드
}
DEFAULT_COLOR = "#6b7280"


def _group_color(group: str) -> str:
    return GROUP_COLORS.get(group, DEFAULT_COLOR)


def _match_card_html(m: dict, delay_ms: int) -> str:
    a = m["a"]
    b = m["b"]
    col_a = _group_color(a["group"])
    col_b = _group_color(b["group"])
    is_upset = (a["rank"] > 8 or b["rank"] > 8)  # 한 쪽이 9위 이하 = 업셋 가능성
    upset_html = '<div class="upset-tag">⚡ 업셋 주의!</div>' if is_upset else ""

    return f"""
<div class="match" style="animation-delay:{delay_ms}ms">
  {upset_html}
  <div class="side side-a" style="background:linear-gradient(135deg,{col_a}22,{col_a}08);">
    <div class="rank" style="color:{col_a};">#{a['rank']}</div>
    <div class="name">{a['member']}</div>
    <div class="group-tag" style="background:{col_a}33;color:{col_a};">{a['group']}</div>
  </div>
  <div class="vs-col">
    <div class="vs">VS</div>
  </div>
  <div class="side side-b" style="background:linear-gradient(135deg,{col_b}08,{col_b}22);">
    <div class="rank" style="color:{col_b};">#{b['rank']}</div>
    <div class="name">{b['member']}</div>
    <div class="group-tag" style="background:{col_b}33;color:{col_b};">{b['group']}</div>
  </div>
</div>"""


def _make_html(matches: list) -> str:
    cards = []
    for i, m in enumerate(matches):
        cards.append(_match_card_html(m, 150 + i * 220))
    cards_html = "\n".join(cards)
    footer_delay = 150 + len(matches) * 220 + 400

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box;
       font-family: 'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
  body {{
    width:1080px; height:1920px; overflow:hidden;
    background: linear-gradient(160deg, #080618 0%, #14063a 45%, #230947 100%);
    color:#fff; display:flex; flex-direction:column;
    align-items:center; padding:72px 52px 60px;
  }}

  /* ── 헤더 ── */
  .header {{
    text-align:center; margin-bottom:44px;
    animation:fadeDown .55s ease both;
  }}
  .live-pill {{
    display:inline-flex; align-items:center; gap:10px;
    background:#ef4444; color:#fff;
    font-size:28px; font-weight:800; letter-spacing:1px;
    padding:10px 32px; border-radius:40px; margin-bottom:22px;
  }}
  .live-dot {{
    width:14px; height:14px; background:#fff;
    border-radius:50%; animation:blink 1s ease infinite;
  }}
  .header h1 {{
    font-size:80px; font-weight:900; line-height:1.1;
    background:linear-gradient(90deg,#fff 0%,#c4b5fd 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }}
  .header .sub {{
    margin-top:14px; font-size:30px; color:rgba(255,255,255,.65);
    font-weight:500;
  }}

  /* ── 매치 카드 ── */
  .match {{
    width:100%; position:relative;
    background:rgba(255,255,255,.05);
    border:1px solid rgba(255,255,255,.12);
    border-radius:20px; margin-bottom:20px;
    display:flex; align-items:stretch;
    overflow:hidden;
    opacity:0; transform:translateY(36px);
    animation:slideUp .48s ease forwards;
  }}
  .side {{
    flex:1; padding:28px 24px;
    display:flex; flex-direction:column;
    align-items:center; justify-content:center; gap:10px;
    text-align:center;
  }}
  .rank {{
    font-size:26px; font-weight:800; letter-spacing:1px;
  }}
  .name {{
    font-size:48px; font-weight:900; line-height:1.1;
    word-break:keep-all;
  }}
  .group-tag {{
    font-size:22px; font-weight:700;
    padding:5px 18px; border-radius:20px; letter-spacing:.5px;
  }}
  .vs-col {{
    width:80px; display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }}
  .vs {{
    font-size:32px; font-weight:900;
    color:rgba(255,255,255,.9);
    text-shadow:0 0 20px rgba(255,255,255,.4);
  }}
  .upset-tag {{
    position:absolute; top:0; left:50%; transform:translateX(-50%);
    background:#f59e0b; color:#000;
    font-size:20px; font-weight:800;
    padding:4px 20px; border-radius:0 0 12px 12px;
    letter-spacing:.5px; white-space:nowrap;
  }}

  /* ── 푸터 ── */
  .footer {{
    margin-top:auto; text-align:center;
    opacity:0; animation:fadeUp .5s {footer_delay}ms ease both;
  }}
  .cta-box {{
    background:rgba(255,255,255,.1);
    border:1px solid rgba(255,255,255,.2);
    border-radius:16px; padding:22px 40px; margin-bottom:18px;
  }}
  .cta-main {{
    font-size:36px; font-weight:800; color:#fbbf24; margin-bottom:6px;
  }}
  .cta-sub {{
    font-size:24px; color:rgba(255,255,255,.7);
  }}
  .handle {{
    font-size:26px; color:rgba(255,255,255,.45); font-weight:500;
  }}

  @keyframes fadeDown {{
    from {{ opacity:0; transform:translateY(-28px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes slideUp {{
    to {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(20px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes blink {{
    0%,100% {{ opacity:1; }} 50% {{ opacity:.3; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <div class="live-pill"><span class="live-dot"></span>투표 진행중</div>
    <h1>8강<br>대진표</h1>
    <div class="sub">댓글로 투표 · 결과는 내일 발표!</div>
  </div>

{cards_html}

  <div class="footer">
    <div class="cta-box">
      <div class="cta-main">💬 지금 바로 댓글 투표!</div>
      <div class="cta-sub">각 경기 게시글에서 번호로 투표하세요</div>
    </div>
    <div class="handle">@daily_enter_kr</div>
  </div>
</body>
</html>"""


def main():
    dry_run = "--dry-run" in sys.argv

    # 중복 체크
    if not dry_run:
        ledger = post_ledger.load_ledger()
        if any((e.get("topic_id") or "") == TOPIC_ID
               for e in ledger.get("entries", [])):
            print(f"✅ {TOPIC_ID} 이미 게시됨 — skip")
            return 0

    bracket_path = ROOT / "data" / "worldcup_bracket.json"
    bracket = json.loads(bracket_path.read_text(encoding="utf-8"))
    r8 = bracket.get("rounds", {}).get("R8", {})
    matches = r8.get("matches", [])
    if not matches:
        print("❌ R8 매치 없음")
        return 1

    out_dir = ROOT / "output_enter" / "publish" / "worldcup_r8_promo"
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "r8_promo.html"
    html_path.write_text(_make_html(matches), encoding="utf-8")
    print(f"✓ HTML 생성: {html_path}")

    if dry_run:
        print(f"🔍 dry-run — HTML만 생성, 게시 안 함: {html_path}")
        return 0

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and
            os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    from render_hf import render_html_to_mp4  # noqa
    mp4_path = out_dir / "r8_promo.mp4"
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

    caption = (
        "🏆 걸그룹 월드컵 8강 대진표!\n\n"
        "장원영 vs 닝닝 ⚡\n"
        "안유진 vs 윈터 🔥\n"
        "카리나 vs 태연 ⚡\n"
        "제니 vs 설윤 💫\n\n"
        "각 경기 게시글에서 댓글로 번호 투표! 💬\n"
        "🔔 팔로우 + 알림 ON → 결과 즉시 알림\n\n"
        "#걸그룹월드컵 #8강 #케이팝 #kpop #아이돌투표 "
        "#장원영 #닝닝 #안유진 #윈터 #카리나 #태연 #제니 #설윤"
    )
    media_id = publisher.post_reel(video_url, caption,
                                   cover_url=None, share_to_feed=True)
    print(f"✅ R8 홍보 릴스 게시 완료! {media_id}")

    post_ledger.record_results([{
        "ok": True,
        "topic_id": TOPIC_ID,
        "title": "걸그룹 월드컵 8강 매치 홍보",
        "style": "worldcup_r8_promo",
        "seed": None,
        "media_id": media_id,
        "platform": "instagram",
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
