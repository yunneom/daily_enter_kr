"""
월드컵 라운드별 HyperFrames HTML 동적 생성기.

대진표 데이터를 읽어 CSS 애니메이션 HTML 을 생성한다.
r16_announce.html 과 동일한 1080x1920 9:16 스타일.

[사용]
python scripts/make_worldcup_hf_html.py R8 output/r8_bracket.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

ROUND_LABELS = {
    "R8": "8강", "R4": "4강", "R2": "결승전", "R1": "🏆 우승 발표",
}

ZONE_COLORS = {
    0: "#7b2fbe",   # A조 보라
    1: "#1a6b4a",   # B조 초록
    2: "#b5451b",   # C조 주황
    3: "#1a3f8c",   # D조 파랑
}

ZONE_NAMES = ["A조", "B조", "C조", "D조"]
ZONE_EMOJIS = ["👑", "🌹", "🦋", "💎"]

# R2(결승 라운드)는 조(zone) 대신 매치 타입으로 라벨 — 결승전/3·4위전 명확 구분.
R2_TYPE_LABELS = {
    "final":       ("🏆 결승전",  "#c99a2e"),
    "third_place": ("🥉 3·4위전", "#8a5a2b"),
}


def _match_block(m, delay_ms: int, zone_idx: int) -> str:
    a = m.get("a", {})
    b = m.get("b", {})
    # R2 매치는 type 기반 라벨/색 (quarter 키가 없어 zone 이 모두 A조로 뭉치는 버그 방지)
    mtype = m.get("type")
    if mtype in R2_TYPE_LABELS:
        zone_label, color = R2_TYPE_LABELS[mtype]
    else:
        color = ZONE_COLORS.get(zone_idx, "#4e1c60")
        zone_label = f"{ZONE_EMOJIS[zone_idx]} {ZONE_NAMES[zone_idx]}"
    a_seed = a.get("seed") or a.get("rank", "")
    b_seed = b.get("seed") or b.get("rank", "")
    a_name = a.get("member", "?")
    b_name = b.get("member", "?")
    return f"""
  <div class="match-card" style="animation-delay:{delay_ms}ms; border-color:{color}80;">
    <div class="match-zone" style="background:{color};">{zone_label}</div>
    <div class="match-inner">
      <div class="fighter a">
        <span class="seed">#{a_seed}</span>
        <span class="name">{a_name}</span>
      </div>
      <div class="vs">⚡ VS ⚡</div>
      <div class="fighter b">
        <span class="seed">#{b_seed}</span>
        <span class="name">{b_name}</span>
      </div>
    </div>
  </div>"""


def _make_html(bracket: dict, round_key: str) -> str:
    rnd = bracket.get("rounds", {}).get(round_key, {})
    matches = rnd.get("matches", [])
    round_label = ROUND_LABELS.get(round_key, round_key)
    n_matches = len(matches)
    is_r2 = round_key == "R2"

    match_blocks = []
    delay = 200
    if is_r2:
        # R2: 조 그루핑 대신 결승전 먼저 → 3·4위전. 라벨은 _match_block 이 type 으로 처리.
        for m in sorted(matches, key=lambda mm: 0 if mm.get("type") == "final" else 1):
            match_blocks.append(_match_block(m, delay, 0))
            delay += 250
    else:
        # 조별 그루핑
        zone_map: dict = {}
        for m in matches:
            q = m.get("quarter", 0)
            zone_map.setdefault(q, []).append(m)
        for q in sorted(zone_map.keys()):
            for m in zone_map[q]:
                match_blocks.append(_match_block(m, delay, q))
                delay += 250

    blocks_html = "\n".join(match_blocks)
    total_anim_ms = delay + 800

    badge_text = "🏆 결승 라인업" if is_r2 else f"🏆 {round_label}"
    sub_text = ("결승전 · 3·4위전 — 지금 바로 투표!" if is_r2
                else f"{n_matches}경기 — 지금 바로 투표!")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>걸그룹 월드컵 {round_label} — Daily Enter</title>
<style>
  :root {{
    --gold: #ffdc78;
    --ink: #1c1c24;
    --bg-top: #1c1644;
    --bg-bot: #4e1c60;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box;
       font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; }}
  body {{
    width:1080px; height:1920px; overflow:hidden;
    background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bot) 100%);
    color:white; display:flex; flex-direction:column;
    align-items:center; padding:60px 48px 48px;
  }}

  /* ── 헤더 ── */
  .header {{
    text-align:center; margin-bottom:48px;
    animation: fadeDown .6s ease both;
  }}
  .header .round-badge {{
    display:inline-block; background:var(--gold);
    color:var(--ink); font-size:36px; font-weight:800;
    padding:10px 40px; border-radius:40px; margin-bottom:20px;
    letter-spacing:2px;
  }}
  .header h1 {{
    font-size:72px; font-weight:900; line-height:1.15;
    text-shadow:0 4px 24px rgba(0,0,0,.5);
  }}
  .header .sub {{
    margin-top:12px; font-size:30px; color:rgba(255,255,255,.75);
  }}

  /* ── 매치 카드 ── */
  .match-card {{
    width:100%; background:rgba(255,255,255,.07);
    border:2px solid rgba(255,255,255,.15);
    border-radius:20px; overflow:hidden; margin-bottom:24px;
    opacity:0; transform:translateY(40px);
    animation: slideUp .5s ease forwards;
  }}
  .match-zone {{
    font-size:26px; font-weight:700; text-align:center;
    padding:10px 0; letter-spacing:1px;
  }}
  .match-inner {{
    display:flex; align-items:center; padding:20px 28px; gap:16px;
  }}
  .fighter {{
    flex:1; text-align:center;
  }}
  .fighter .seed {{
    font-size:22px; color:var(--gold); font-weight:700;
    display:block; margin-bottom:4px;
  }}
  .fighter .name {{
    font-size:38px; font-weight:800; line-height:1.2;
    word-break:keep-all;
  }}
  .vs {{
    font-size:28px; font-weight:900; color:var(--gold);
    white-space:nowrap; flex-shrink:0;
  }}

  /* ── 푸터 ── */
  .footer {{
    margin-top:auto; text-align:center;
    animation: fadeUp .6s {total_anim_ms}ms ease both;
    opacity:0;
  }}
  .footer .cta {{
    font-size:32px; font-weight:700; color:var(--gold); margin-bottom:10px;
  }}
  .footer .handle {{
    font-size:26px; color:rgba(255,255,255,.6);
  }}

  @keyframes fadeDown {{
    from {{ opacity:0; transform:translateY(-30px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes slideUp {{
    to {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(20px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
</style>
</head>
<body>
  <div class="header">
    <div class="round-badge">{badge_text}</div>
    <h1>걸그룹<br>월드컵</h1>
    <div class="sub">{sub_text}</div>
  </div>

{blocks_html}

  <div class="footer">
    <div class="cta">💬 댓글로 투표! 지금 바로!</div>
    <div class="handle">@daily_enter_kr</div>
  </div>
</body>
</html>
"""


def generate(round_key: str, output_path: Path) -> Path:
    bracket_path = ROOT / "data" / "worldcup_bracket.json"
    bracket = json.loads(bracket_path.read_text(encoding="utf-8"))
    if round_key not in bracket.get("rounds", {}):
        raise ValueError(f"{round_key} 라운드가 bracket 에 없음")
    html = _make_html(bracket, round_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main():
    if len(sys.argv) < 3:
        print("usage: make_worldcup_hf_html.py R8 <output.html>")
        return 1
    round_key = sys.argv[1]
    out = Path(sys.argv[2])
    generate(round_key, out)
    print(f"✓ {out} 생성됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
