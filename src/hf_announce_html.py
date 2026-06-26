"""
HyperFrames 호환 결과 발표 HTML 컴포지션 생성기.

라운드별 진출자 N명 → HTML (1080x1920 9:16 6초).
- R16: 16강→8강 진출 8명 (4×2 또는 큰 grid)
- R8:  8강→4강 진출 4명
- R4:  결승 라인업 2명
- R1:  🏆 우승+1·2·3위 시상대

[모션]
1. 트로피 펑 + 빛살 회전
2. 진출자 카드 stagger drop (그룹 시그니처 컬러)
3. 다음 라운드 박스 슬라이드업
"""

from typing import List, Dict, Optional

# 그룹 → CSS 클래스명 (영문 슬러그)
GROUP_SLUG = {
    "아이브": "ive", "블랙핑크": "blackpink", "에스파": "aespa", "뉴진스": "newjeans",
    "리센느": "lisenne", "아일릿": "illit", "르세라핌": "lesserafim", "엔믹스": "nmixx",
    "레드벨벳": "redvelvet", "트와이스": "twice", "ITZY": "itzy", "소녀시대": "snsd",
    "우주소녀": "wjsn", "시그니처": "sig", "마마무": "mamamoo", "위키미키": "wm",
    "프로미스나인": "fromis", "다이아": "dia", "베이비몬스터": "bm",
}

GROUP_EN = {
    "아이브": "IVE", "블랙핑크": "BLACKPINK", "에스파": "aespa", "뉴진스": "NewJeans",
    "리센느": "Lisenne", "아일릿": "ILLIT", "르세라핌": "LE SSERAFIM", "엔믹스": "NMIXX",
    "레드벨벳": "Red Velvet", "트와이스": "TWICE", "ITZY": "ITZY", "소녀시대": "SNSD",
    "우주소녀": "WJSN", "시그니처": "tripleS", "마마무": "MAMAMOO", "위키미키": "Weki Meki",
    "프로미스나인": "fromis_9", "다이아": "DIA", "베이비몬스터": "BABYMONSTER",
}

# 라운드별 그리드/카드 사이즈 (CSS columns × rows, 카드 폰트 크기)
ROUND_LAYOUT = {
    "R16": {"cols": 4, "rows": 2, "card_name_px": 44, "card_grp_px": 22, "label": "32강 → 16강", "title": "16강 진출!"},
    "R8":  {"cols": 4, "rows": 1, "card_name_px": 58, "card_grp_px": 28, "label": "16강 → 8강", "title": "8강 진출!"},
    "R4":  {"cols": 2, "rows": 1, "card_name_px": 96, "card_grp_px": 44, "label": "8강 → 결승 라인업", "title": "결승 진출!"},
}

# 공통 CSS — 그룹 시그니처 컬러
COMMON_CSS = """
.ive       { background: linear-gradient(180deg, #ff5a8c 0%, #c8286e 100%); }
.illit     { background: linear-gradient(180deg, #ff82aa 0%, #eb5a82 100%); }
.blackpink { background: linear-gradient(180deg, #ff50a0 0%, #1e1e24 100%); }
.aespa     { background: linear-gradient(180deg, #282c3c 0%, #781e78 100%); }
.lesserafim{ background: linear-gradient(180deg, #3c4660 0%, #c83c46 100%); }
.redvelvet { background: linear-gradient(180deg, #e63246 0%, #8c1428 100%); }
.twice     { background: linear-gradient(180deg, #ff78aa 0%, #fa505a 100%); }
.snsd      { background: linear-gradient(180deg, #ffa0be 0%, #e66e96 100%); }
.lisenne   { background: linear-gradient(180deg, #5aa0dc 0%, #285aaa 100%); }
.dia       { background: linear-gradient(180deg, #6eb4dc 0%, #4682be 100%); }
.nmixx     { background: linear-gradient(180deg, #5a46c8 0%, #c83c96 100%); }
.newjeans  { background: linear-gradient(180deg, #78c8ff 0%, #3c82e6 100%); }
.itzy      { background: linear-gradient(180deg, #ff465a 0%, #e6143c 100%); }
.bm        { background: linear-gradient(180deg, #3c3c46 0%, #c83246 100%); }
.fromis    { background: linear-gradient(180deg, #5aaae6 0%, #825adc 100%); }
.mamamoo   { background: linear-gradient(180deg, #ff8c3c 0%, #dc5a28 100%); }
.wm        { background: linear-gradient(180deg, #ff6e96 0%, #dc4678 100%); }
.wjsn      { background: linear-gradient(180deg, #785ad2 0%, #4632a0 100%); }
.sig       { background: linear-gradient(180deg, #5a6478 0%, #32374b 100%); }
.dflt      { background: linear-gradient(180deg, #5a3c96 0%, #321e64 100%); }
"""


def _grp_slug(g: str) -> str:
    return GROUP_SLUG.get(g, "dflt")


def _grp_en(g: str) -> str:
    return GROUP_EN.get(g, g)


def render_round_announce_html(round_key: str, members: List[Dict],
                                next_hint: str = "",
                                source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> str:
    """R16/R8/R4 결과 발표 HTML."""
    layout = ROUND_LAYOUT.get(round_key, ROUND_LAYOUT["R16"])
    cols = layout["cols"]
    n = len(members)

    # 카드 stagger delay — 0.8s 시작, 0.12s 간격
    cards_html = []
    for i, m in enumerate(members):
        slug = _grp_slug(m.get("group", ""))
        grp_en = _grp_en(m.get("group", ""))
        name = m.get("member", "")
        rank = m.get("rank", "")
        delay = 0.8 + i * 0.12
        cards_html.append(f"""
    <div class="card {slug}" style="animation-delay: {delay:.2f}s">
      <span class="badge">{rank}위</span>
      <span class="grp">{grp_en}</span>
      <span class="name">{name}</span>
    </div>""")
    cards_str = "\n".join(cards_html)

    grid_template = f"repeat({cols}, 1fr)"
    name_px = layout["card_name_px"]
    grp_px = layout["card_grp_px"]
    title = layout["title"]
    label = layout["label"]

    # R4 는 카드가 2개라 grid 비율 다름 → 큼직하게
    grid_max_w = "1000px" if cols >= 4 else "900px"

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, 'Pretendard', 'Apple SD Gothic Neo', sans-serif; }}
body {{ width:1080px; height:1920px; overflow:hidden;
  background: linear-gradient(180deg, #1c1644 0%, #4e1c60 100%); color:white; }}
.scene {{ width:100%; height:100%; position:relative; }}
.rays {{
  position:absolute; top:0; left:50%; transform:translateX(-50%);
  width:600px; height:600px; opacity:0;
  background: conic-gradient(from 0deg, transparent 0deg, #ffdc78 6deg, transparent 12deg, transparent 30deg, #ffdc78 36deg, transparent 42deg);
  mask: radial-gradient(circle, transparent 80px, black 120px);
  -webkit-mask: radial-gradient(circle, transparent 80px, black 120px);
  animation: raysSpin 4s linear 0.5s infinite, raysIn 0.5s ease-out 0.5s forwards;
  z-index:-1;
}}
.trophy {{ position:absolute; top:40px; left:50%; transform:translateX(-50%) scale(0);
  font-size:120px; filter: drop-shadow(0 0 18px #ffdc78);
  animation: trophyPop 0.6s cubic-bezier(.34,1.56,.64,1) 0.2s forwards; }}
.label {{ text-align:center; padding-top:200px; font-size:46px; color:#dcd6f0; font-weight:700;
  opacity:0; animation: fadeIn 0.4s ease-out 0.1s forwards; }}
.title {{ text-align:center; margin-top:14px; font-size:114px; color:#ffdc78; font-weight:900;
  text-shadow: -3px -3px 0 #1c1c24, 3px 3px 0 #1c1c24;
  opacity:0; transform: scale(0.6);
  animation: pop 0.5s cubic-bezier(.34,1.56,.64,1) 0.3s forwards; }}
.grid {{ margin: 80px auto 0; max-width:{grid_max_w};
  display:grid; grid-template-columns: {grid_template}; gap: 22px; padding: 0 30px; }}
.card {{ aspect-ratio: 1/1.2; border-radius:18px; border: 3px solid #ffdc78;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  position:relative; overflow:hidden;
  opacity:0; transform: translateY(-80px) scale(0.7);
  animation: cardDrop 0.55s cubic-bezier(.34,1.56,.64,1) forwards;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3); }}
.card .grp {{ font-size:{grp_px}px; font-weight:800; background:white; color:#1c1c24;
  padding:6px 14px; border-radius:8px; margin-bottom:6px; max-width:90%;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card .name {{ font-size:{name_px}px; font-weight:900; background:white; color:#1c1c24;
  padding:6px 14px; border-radius:8px; max-width:90%;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.badge {{ position:absolute; top:8px; left:8px; background:#ffdc78; color:#1c1c24;
  padding:4px 10px; border-radius:8px; font-size:18px; font-weight:800; }}
.next {{ position:absolute; bottom:90px; left:40px; right:40px;
  background:#ffdc78; color:#1c1c24; padding:24px; border-radius:24px; text-align:center;
  border: 4px solid #1c1c24; opacity:0; transform: translateY(60px);
  animation: slideUp 0.6s cubic-bezier(.34,1.56,.64,1) {0.8 + n * 0.12 + 0.4:.2f}s forwards; }}
.next .nl {{ font-size:36px; font-weight:800; }}
.next .nt {{ font-size:38px; font-weight:900; margin-top:8px; }}
.next .nc {{ font-size:26px; margin-top:8px; color:#783c64; }}
.footer {{ position:absolute; bottom:30px; left:0; right:0; text-align:center;
  font-size:22px; color:#bdb4d4; }}
{COMMON_CSS}
@keyframes fadeIn {{ to {{ opacity:1; }} }}
@keyframes pop {{ to {{ opacity:1; transform: scale(1); }} }}
@keyframes trophyPop {{ 50% {{ transform: translateX(-50%) scale(1.15); }}
  100% {{ transform: translateX(-50%) scale(1); }} }}
@keyframes raysIn {{ to {{ opacity:0.35; }} }}
@keyframes raysSpin {{ to {{ transform: translateX(-50%) rotate(360deg); }} }}
@keyframes cardDrop {{ to {{ opacity:1; transform: translateY(0) scale(1); }} }}
@keyframes slideUp {{ to {{ opacity:1; transform: translateY(0); }} }}
</style></head>
<body><div class="scene" data-duration="6">
  <div class="rays"></div>
  <div class="trophy">🏆</div>
  <div class="label">{label}</div>
  <div class="title">{title}</div>
  <div class="grid">{cards_str}
  </div>
  <div class="next">
    <div class="nl">⏰ 다음 라운드</div>
    <div class="nt">{next_hint}</div>
    <div class="nc">🔔 팔로우 + 알림 ON 으로 놓치지 마세요!</div>
  </div>
  <div class="footer">{source_note} · @daily_enter_kr</div>
</div></body></html>"""


def render_podium_html(winner: Dict, second: Dict, third: Dict,
                       source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> str:
    """우승 발표 시상대 HTML — 1위 중앙(높음) / 2위 좌 / 3위 우."""
    def card(slug, grp_en, name, place, color):
        return f"""<div class="podium-card {slug}" data-place="{place}">
      <div class="medal" style="background:{color}">{place}</div>
      <div class="grp">{grp_en}</div>
      <div class="name">{name}</div>
    </div>"""

    w_card = card(_grp_slug(winner["group"]), _grp_en(winner["group"]), winner["member"], "🥇 1위", "#ffdc78")
    s_card = card(_grp_slug(second["group"]), _grp_en(second["group"]), second["member"], "🥈 2위", "#c8c8dc")
    t_card = card(_grp_slug(third["group"]), _grp_en(third["group"]), third["member"], "🥉 3위", "#c8825a")

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, 'Pretendard', 'Apple SD Gothic Neo', sans-serif; }}
body {{ width:1080px; height:1920px; overflow:hidden;
  background: linear-gradient(180deg, #1c1644 0%, #4e1c60 100%); color:white; }}
.scene {{ width:100%; height:100%; position:relative; }}
.rays {{
  position:absolute; top:200px; left:50%; transform:translateX(-50%);
  width:800px; height:800px; opacity:0;
  background: conic-gradient(from 0deg, transparent 0deg, #ffdc78 8deg, transparent 16deg, transparent 36deg, #ffdc78 44deg, transparent 52deg);
  mask: radial-gradient(circle, transparent 100px, black 150px);
  -webkit-mask: radial-gradient(circle, transparent 100px, black 150px);
  animation: raysSpin 5s linear 0.3s infinite, raysIn 0.6s ease-out 0.3s forwards;
  z-index:-1;
}}
.trophy {{ position:absolute; top:80px; left:50%; transform:translateX(-50%) scale(0);
  font-size:200px; filter: drop-shadow(0 0 24px #ffdc78);
  animation: trophyPop 0.7s cubic-bezier(.34,1.56,.64,1) 0.2s forwards; }}
.label {{ text-align:center; padding-top:300px; font-size:52px; color:#dcd6f0; font-weight:700;
  opacity:0; animation: fadeIn 0.5s ease-out 0.4s forwards; }}
.title {{ text-align:center; margin-top:14px; font-size:132px; color:#ffdc78; font-weight:900;
  text-shadow: -4px -4px 0 #1c1c24, 4px 4px 0 #1c1c24;
  opacity:0; transform: scale(0.5);
  animation: pop 0.6s cubic-bezier(.34,1.56,.64,1) 0.6s forwards; }}
.podium {{ position:absolute; top:680px; left:0; right:0;
  display:flex; justify-content:center; align-items:flex-end; gap:24px; padding:0 30px; }}
.podium-card {{ width:300px; border-radius:24px; border:4px solid #ffdc78;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  padding:36px 20px; position:relative; box-shadow: 0 12px 32px rgba(0,0,0,0.4);
  opacity:0; transform: translateY(120px) scale(0.7); }}
.podium-card[data-place^="🥇"] {{ height:560px; animation: podiumPop 0.6s cubic-bezier(.34,1.56,.64,1) 1.5s forwards; }}
.podium-card[data-place^="🥈"] {{ height:460px; animation: podiumPop 0.6s cubic-bezier(.34,1.56,.64,1) 1.1s forwards; }}
.podium-card[data-place^="🥉"] {{ height:400px; animation: podiumPop 0.6s cubic-bezier(.34,1.56,.64,1) 1.3s forwards; }}
.medal {{ font-size:40px; font-weight:900; color:#1c1c24; padding:10px 20px;
  border-radius:16px; margin-bottom:16px; }}
.podium-card .grp {{ font-size:34px; font-weight:800; background:white; color:#1c1c24;
  padding:8px 16px; border-radius:10px; margin-bottom:10px; }}
.podium-card .name {{ font-size:64px; font-weight:900; background:white; color:#1c1c24;
  padding:8px 16px; border-radius:10px; }}
.cta {{ position:absolute; bottom:90px; left:40px; right:40px;
  background:#ffdc78; color:#1c1c24; padding:28px; border-radius:24px; text-align:center;
  border: 4px solid #1c1c24; opacity:0; transform: translateY(60px);
  animation: slideUp 0.6s cubic-bezier(.34,1.56,.64,1) 2.4s forwards; }}
.cta .ct {{ font-size:42px; font-weight:900; }}
.cta .cs {{ font-size:28px; margin-top:8px; color:#783c64; }}
.footer {{ position:absolute; bottom:30px; left:0; right:0; text-align:center;
  font-size:22px; color:#bdb4d4; }}
{COMMON_CSS}
@keyframes fadeIn {{ to {{ opacity:1; }} }}
@keyframes pop {{ to {{ opacity:1; transform: scale(1); }} }}
@keyframes trophyPop {{ 50% {{ transform: translateX(-50%) scale(1.2); }}
  100% {{ transform: translateX(-50%) scale(1); }} }}
@keyframes raysIn {{ to {{ opacity:0.4; }} }}
@keyframes raysSpin {{ to {{ transform: translateX(-50%) rotate(360deg); }} }}
@keyframes podiumPop {{ to {{ opacity:1; transform: translateY(0) scale(1); }} }}
@keyframes slideUp {{ to {{ opacity:1; transform: translateY(0); }} }}
</style></head>
<body><div class="scene" data-duration="6">
  <div class="rays"></div>
  <div class="trophy">🏆</div>
  <div class="label">걸그룹 월드컵 — 최종 결과</div>
  <div class="title">🏆 우승!</div>
  <div class="podium">{s_card}{w_card}{t_card}</div>
  <div class="cta">
    <div class="ct">🙌 우승 축하 댓글 ⬇️</div>
    <div class="cs">팔로우 + 알림 ON → 다음 시즌 안내</div>
  </div>
  <div class="footer">{source_note} · @daily_enter_kr</div>
</div></body></html>"""
