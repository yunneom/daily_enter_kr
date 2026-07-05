"""
웹앱(dailyenterkr.com/play) 홍보 5부작 릴스 — HP(HTML→Playwright→MP4).

IG 댓글 투표는 '한 경기 맛보기'. 웹은 32강부터 우승자까지 직접 토너먼트를 돌리고
내 픽이 실시간 순위에 반영됨 → 그 차별점을 5개 릴스로 자동 홍보.

  1 teaser    — "직접 뽑는 월드컵" 후킹 + URL
  2 howto     — 3-step 플레이 방법
  3 sample    — 실제 대결 카드(실물사진) 애니메이션 (히어로)
  4 live      — 내 픽이 실시간 TOP 순위에 반영 (참여 FOMO)
  5 tiein     — IG 결승(닝닝 vs 카리나)과 연결 → "당신의 우승자는?"

실행: python scripts/worldcup_web_promo.py <1-5> [--dry-run]
      python scripts/worldcup_web_promo.py auto     # 다음 미게시 wave 자동 선택
"""

import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from post_instagram import InstagramPublisher, upload_video  # noqa: E402
import post_ledger  # noqa: E402

PLAY_URL = "dailyenterkr.com/play"
UTM = "?utm_source=instagram&utm_medium=reels&utm_campaign=worldcup_web"

GROUP_COLORS = {
    "아이브": "#2563eb", "에스파": "#7c3aed", "블랙핑크": "#db2777",
    "소녀시대": "#d97706", "엔믹스": "#059669", "뉴진스": "#0891b2",
    "르세라핌": "#dc2626",
}


def _photo_data_uri(member: str) -> str:
    """idol_photo 로 실물사진 확보 → base64 data URI (Playwright 로컬 렌더용). 실패 시 ''."""
    try:
        import idol_photo
        rec = idol_photo.fetch_photo(member)
        if not rec or not rec.get("path"):
            return ""
        b = Path(rec["path"]).read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(b).decode()
    except Exception as e:
        print(f"  ⚠️ 사진 확보 실패({member}): {e}")
        return ""


def _duel_card(m: dict, side: str, picked: bool) -> str:
    col = GROUP_COLORS.get(m.get("group", ""), "#6b7280")
    uri = _photo_data_uri(m["member"])
    face = (f'<div class="face" style="background-image:url({uri});"></div>' if uri
            else f'<div class="face noimg" style="background:{col};">{m["member"][0]}</div>')
    cls = "card picked" if picked else "card"
    return f"""
    <div class="{cls} {side}" style="--c:{col};">
      {face}
      <div class="cap"><span class="grp" style="color:{col};">{m.get('group','')}</span>
        <span class="nm">{m['member']}</span></div>
      {'<div class="badge">PICK</div>' if picked else ''}
    </div>"""


# ── 공통 셸 ─────────────────────────────────────────────────────────────────
def _shell(inner: str, foot_delay_ms: int = 3600) -> str:
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box;
       font-family:'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
  body {{ width:1080px; height:1920px; overflow:hidden; color:#fff;
    background:linear-gradient(160deg,#080618 0%,#160845 46%,#2a0b52 100%);
    display:flex; flex-direction:column; align-items:center; padding:92px 60px 84px; }}
  .pill {{ display:inline-flex; background:#fbbf24; color:#160845; font-size:30px;
    font-weight:800; letter-spacing:2px; padding:12px 34px; border-radius:40px; }}
  .h1 {{ font-size:104px; font-weight:900; line-height:1.04; text-align:center; margin-top:22px;
    background:linear-gradient(90deg,#fff,#c4b5fd); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; }}
  .sub {{ font-size:36px; color:rgba(255,255,255,.72); font-weight:500; text-align:center;
    margin-top:18px; line-height:1.4; }}
  .mid {{ flex:1; width:100%; display:flex; flex-direction:column; justify-content:center;
    align-items:center; gap:30px; }}
  .urlcard {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.22);
    border-radius:22px; padding:30px 40px; text-align:center; }}
  .urlcard .u {{ font-size:52px; font-weight:900; color:#fbbf24; letter-spacing:.5px; }}
  .urlcard .t {{ font-size:28px; color:rgba(255,255,255,.7); margin-top:10px; }}
  .handle {{ font-size:28px; color:rgba(255,255,255,.5); text-align:center; }}
  /* 스텝 */
  .step {{ width:100%; display:flex; align-items:center; gap:26px; background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.12); border-radius:20px; padding:30px 34px; }}
  .step .n {{ font-size:46px; font-weight:900; color:#160845; background:#fbbf24; min-width:78px;
    height:78px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}
  .step .tx {{ font-size:42px; font-weight:700; line-height:1.25; word-break:keep-all; }}
  /* 듀얼 */
  .duel {{ display:flex; align-items:center; gap:20px; width:100%; }}
  .card {{ flex:1; background:rgba(255,255,255,.05); border:2px solid rgba(255,255,255,.14);
    border-radius:26px; padding:22px; text-align:center; position:relative; transition:.4s; }}
  .card.picked {{ border-color:var(--c); box-shadow:0 0 46px -6px var(--c); transform:translateY(-8px); }}
  .face {{ width:320px; height:320px; margin:0 auto; border-radius:50%; background-size:cover;
    background-position:center 22%; border:5px solid rgba(255,255,255,.9); }}
  .face.noimg {{ display:flex; align-items:center; justify-content:center; font-size:150px;
    font-weight:900; color:#fff; }}
  .cap {{ margin-top:20px; display:flex; flex-direction:column; gap:6px; }}
  .cap .grp {{ font-size:28px; font-weight:800; }}
  .cap .nm {{ font-size:56px; font-weight:900; }}
  .badge {{ position:absolute; top:16px; right:16px; background:var(--c); color:#fff;
    font-size:26px; font-weight:900; padding:8px 20px; border-radius:20px; letter-spacing:1px; }}
  .vs {{ font-size:44px; font-weight:900; color:rgba(255,255,255,.85); flex-shrink:0;
    text-shadow:0 0 22px rgba(255,255,255,.4); }}
  /* 실시간 순위 */
  .rankrow {{ width:100%; display:flex; align-items:center; gap:24px; background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.12); border-radius:20px; padding:26px 32px; }}
  .rankrow .r {{ font-size:52px; font-weight:900; color:#fbbf24; min-width:70px; }}
  .rankrow .nm {{ font-size:46px; font-weight:800; }}
  .rankrow .live {{ margin-left:auto; font-size:26px; font-weight:800; color:#22d3ee;
    display:flex; align-items:center; gap:10px; }}
  .dot {{ width:14px; height:14px; border-radius:50%; background:#22d3ee;
    box-shadow:0 0 0 0 #22d3ee; animation:pulse 1.6s infinite; }}
  @keyframes pulse {{ 0%{{box-shadow:0 0 0 0 rgba(34,211,238,.6);}} 70%{{box-shadow:0 0 0 20px rgba(34,211,238,0);}} 100%{{box-shadow:0 0 0 0 rgba(34,211,238,0);}} }}
  .fadeup {{ opacity:0; transform:translateY(28px); animation:fu .6s ease forwards; }}
  .foot {{ opacity:0; animation:fu .6s {foot_delay_ms}ms ease forwards; text-align:center; }}
  @keyframes fu {{ to {{ opacity:1; transform:translateY(0); }} }}
</style></head><body>{inner}</body></html>"""


def _cta(sub="지금 바로 플레이"):
    return f"""<div class="foot">
      <div class="urlcard"><div class="u">{PLAY_URL}</div><div class="t">{sub}</div></div>
      <div class="handle" style="margin-top:18px;">@daily_enter_kr</div></div>"""


def _cta_center(sub="지금 바로 플레이", delay_ms=1000):
    """텍스트-only wave 용 — URL 카드를 화면 중앙(.mid)에 크게 배치."""
    return (f'<div class="mid"><div class="urlcard fadeup" style="animation-delay:{delay_ms}ms; '
            f'padding:40px 56px;"><div class="u" style="font-size:60px;">{PLAY_URL}</div>'
            f'<div class="t" style="font-size:32px;">{sub}</div></div></div>'
            f'<div class="foot" style="animation-delay:{delay_ms+400}ms;">'
            f'<div class="handle">@daily_enter_kr</div></div>')


def build_html(wave: int) -> str:
    if wave == 1:  # 티저
        inner = f"""
      <div class="pill fadeup" style="animation-delay:.1s;">NEW · 웹 월드컵</div>
      <div class="h1 fadeup" style="animation-delay:.3s;">직접 뽑는<br>이상형 월드컵</div>
      <div class="sub fadeup" style="animation-delay:.6s;">댓글 투표는 맛보기 —<br>32강부터 우승자까지 내 손으로</div>
      {_cta_center("당신이 뽑는 우승자는?", 900)}"""
        return _shell(inner, 900)
    if wave == 2:  # 플레이 방법
        steps = [("1", "둘 중 더 좋은 한 명 선택"),
                 ("2", "32강 → 16강 → 8강 → 4강 → 결승"),
                 ("3", "나만의 우승자 완성 · 실시간 순위 확인")]
        rows = "\n".join(
            f'<div class="step fadeup" style="animation-delay:{0.3+i*0.25}s;">'
            f'<div class="n">{n}</div><div class="tx">{t}</div></div>'
            for i, (n, t) in enumerate(steps))
        inner = f"""
      <div class="pill fadeup" style="animation-delay:.1s;">플레이 방법</div>
      <div class="h1 fadeup" style="animation-delay:.25s; font-size:88px;">30초면 끝</div>
      <div class="mid" style="gap:30px;">{rows}</div>{_cta()}"""
        return _shell(inner, 1500)
    if wave == 3:  # 샘플 플레이 (사진)
        bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
        r32 = bracket.get("rounds", {}).get("R32", {}).get("matches", [])
        m = r32[0] if r32 else {"a": {"member": "카리나", "group": "에스파"},
                                "b": {"member": "윈터", "group": "에스파"}}
        duel = (f'<div class="duel">{_duel_card(m["a"], "a", True)}'
                f'<div class="vs">VS</div>{_duel_card(m["b"], "b", False)}</div>')
        inner = f"""
      <div class="pill fadeup" style="animation-delay:.1s;">이렇게 즐겨요</div>
      <div class="h1 fadeup" style="animation-delay:.25s; font-size:80px;">한 명씩<br>골라서 토너먼트</div>
      <div class="mid fadeup" style="animation-delay:.6s;">{duel}</div>{_cta("32강부터 직접 해보기")}"""
        return _shell(inner, 1600)
    if wave == 4:  # 실시간 인기 픽
        rows = "\n".join(
            f'<div class="rankrow fadeup" style="animation-delay:{0.35+i*0.2}s;">'
            f'<div class="r">{i+1}</div><div class="nm">? ? ?</div>'
            f'<div class="live"><span class="dot"></span>LIVE</div></div>'
            for i in range(3))
        inner = f"""
      <div class="pill fadeup" style="animation-delay:.1s;">실시간 순위</div>
      <div class="h1 fadeup" style="animation-delay:.25s; font-size:80px;">지금 1위는<br>누구일까?</div>
      <div class="sub fadeup" style="animation-delay:.5s;">내 픽이 실시간 TOP에 바로 반영</div>
      <div class="mid" style="gap:24px;">{rows}</div>{_cta("내 손으로 순위 만들기")}"""
        return _shell(inner, 1500)
    if wave == 5:  # IG 결승 연결
        inner = f"""
      <div class="pill fadeup" style="animation-delay:.1s;">결승 D-DAY</div>
      <div class="h1 fadeup" style="animation-delay:.25s; font-size:78px;">IG 결승은<br>닝닝 vs 카리나</div>
      <div class="sub fadeup" style="animation-delay:.55s;">그런데, 당신의 우승자는?<br>32강부터 직접 뽑아보세요</div>
      {_cta_center("나만의 우승자 뽑기", 900)}"""
        return _shell(inner, 900)
    raise SystemExit(f"❌ 알 수 없는 wave: {wave}")


CAPTIONS = {
    1: ("댓글로 한 경기씩 투표하셨죠? 이제 32강부터 우승자까지 직접 뽑아보세요.\n"
        f"{PLAY_URL} 에서 지금 바로.\n\n"
        "#걸그룹월드컵 #이상형월드컵 #케이팝 #kpop #아이돌 #월드컵게임"),
    2: ("두 명 중 한 명 고르기만 반복하면 30초 만에 나만의 우승자 완성.\n"
        f"{PLAY_URL}\n\n#걸그룹월드컵 #이상형월드컵 #케이팝 #kpop #밸런스게임"),
    3: ("이런 식으로 한 명씩 골라 토너먼트를 돌립니다. 실물사진으로 더 몰입되게.\n"
        f"{PLAY_URL} 에서 직접 해보기.\n\n#걸그룹월드컵 #이상형월드컵 #케이팝 #kpop #아이돌"),
    4: ("내가 뽑은 우승자가 실시간 순위에 바로 반영됩니다. 지금 1위는 누구일까요?\n"
        f"{PLAY_URL}\n\n#걸그룹월드컵 #이상형월드컵 #실시간순위 #케이팝 #kpop"),
    5: ("IG 결승 대진은 닝닝 vs 카리나. 당신만의 우승자는 다를 수 있어요.\n"
        f"32강부터 직접 뽑아보세요 — {PLAY_URL}\n\n#걸그룹월드컵 #이상형월드컵 #결승 #케이팝 #kpop"),
}

TITLES = {1: "티저", 2: "플레이 방법", 3: "샘플 플레이", 4: "실시간 순위", 5: "결승 연결"}


def _next_wave() -> int:
    ledger = post_ledger.load_ledger()
    done = {(e.get("topic_id") or "") for e in ledger.get("entries", [])}
    for w in range(1, 6):
        if f"worldcup_web_promo_{w}" not in done:
            return w
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if not args or args[0] == "auto":
        wave = _next_wave()
        if wave == 0:
            print("✅ 웹 홍보 5부작 모두 게시됨 — skip")
            return 0
    else:
        wave = int(args[0])
    topic_id = f"worldcup_web_promo_{wave}"

    if not dry_run:
        ledger = post_ledger.load_ledger()
        if any((e.get("topic_id") or "") == topic_id for e in ledger.get("entries", [])):
            print(f"✅ {topic_id} 이미 게시됨 — skip")
            return 0

    out_dir = ROOT / "output_enter" / "publish" / "worldcup_web_promo"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"web_promo_{wave}.html"
    html_path.write_text(build_html(wave), encoding="utf-8")
    print(f"✓ wave {wave} ({TITLES[wave]}) HTML: {html_path}")

    if dry_run:
        print(f"🔍 dry-run — HTML 만 생성: {html_path}")
        return 0

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    from render_hf import render_html_to_mp4  # noqa: E402
    mp4_path = out_dir / f"web_promo_{wave}.mp4"
    rc = render_html_to_mp4(html_path, mp4_path, duration=7.0, fps=30)
    if rc != 0 or not mp4_path.exists():
        print(f"❌ Playwright 렌더 실패 rc={rc}")
        return 1
    print(f"✓ MP4: {mp4_path} ({mp4_path.stat().st_size // 1024}KB)")

    video_url = upload_video(mp4_path)
    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1

    media_id = publisher.post_reel(video_url, CAPTIONS[wave], cover_url=None, share_to_feed=True)
    print(f"✅ 웹 홍보 wave {wave} 게시 완료! {media_id}")

    post_ledger.record_results([{
        "ok": True, "topic_id": topic_id,
        "title": f"웹 월드컵 홍보 {wave} ({TITLES[wave]})",
        "style": "worldcup_web_promo", "seed": None,
        "media_id": media_id, "platform": "instagram",
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
