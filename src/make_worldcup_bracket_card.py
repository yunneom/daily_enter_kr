"""
걸그룹 월드컵 32강 대진표 카드 — 토너먼트 브라켓 트리.

[구조]
32명 → 4개 1/4 브라켓(Q0-Q3, 각 8명). 상반부(Q0·Q1)·하반부(Q2·Q3) 2장으로 분할.
각 반쪽 = 16명 → R32(8매치) → 16강(4) → 8강(2) → 4강(1) → 결승 진출.
TOP1-4 분산 시드 덕에 빅매치는 결승까지 안 만남 → 브라켓에 그대로 드러남.

[디자인]
좌측에 R32 16명 chip(시드순위 배지 + 이름 + 그룹), 우측으로 브라켓 라인 수렴.
컬럼 헤더(32강·16강·8강·4강·결승진출). 마지막 🏆. 하단 투표 안내.

[사용]
make_bracket_half("top"|"bottom", data, out)  — 반쪽 1장
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image
from make_worldcup_match_card import group_emoji_for


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)
BG_TOP = (28, 22, 68)
BG_BOT = (78, 28, 96)
GOLD = (255, 220, 120)
PINK = (255, 102, 184)
WHITE_DIM = (220, 215, 235)
CARD_BG = (255, 255, 255)
LINE = (255, 220, 120)
SLOT_DIM = (90, 78, 130)

# 컬럼 X (chip 좌측만 이름, 나머지는 라인 수렴 지점)
COL_HEADERS_X = [150, 392, 580, 760, 950]  # 32강/16강/8강/4강/결승
CHIP_X0, CHIP_X1 = 22, 282
ZONE_TOP, ZONE_BOT = 300, 1700


def _font(weight, size):
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[k] * (1 - t) + bot[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def _centered(draw, text, font, cx, y, fill=WHITE, stroke=0, sfill=None):
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kw = dict(font=font, fill=fill)
    if stroke:
        kw["stroke_width"] = stroke; kw["stroke_fill"] = sfill or INK
    draw.text((cx - w / 2, y), text, **kw)


def _chip(img, draw, cy, member: Dict):
    """R32 멤버 chip — 시드 배지 + 그룹 emoji + 이름 + 그룹."""
    h = 78
    y0, y1 = int(cy - h / 2), int(cy + h / 2)
    draw.rounded_rectangle([CHIP_X0, y0, CHIP_X1, y1], radius=14,
                           fill=CARD_BG, outline=GOLD, width=3)
    # 시드 배지 (좌)
    rk = member.get("rank", "")
    badge_d = 42
    bx, by = CHIP_X0 + 8, int(cy - badge_d / 2)
    draw.ellipse([bx, by, bx + badge_d, by + badge_d], fill=PINK)
    bf = _font("Bold", 24 if len(str(rk)) < 2 else 22)
    bb = bf.getbbox(str(rk))
    draw.text((bx + badge_d / 2 - (bb[2] - bb[0]) / 2 - 1,
               by + badge_d / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
              str(rk), font=bf, fill=WHITE)
    # 그룹 emoji (배지 옆)
    em = _get_emoji_image(group_emoji_for(member.get("group", "")), 34)
    ex = CHIP_X0 + 58
    if em:
        img.alpha_composite(em, (ex, int(cy - 17)))
    # 이름 + 그룹
    name = member.get("member", "")
    nf = _font("Bold", 34)
    tx = CHIP_X0 + 100
    draw.text((tx, cy - 30), name, font=nf, fill=INK)
    gf = _font("Medium", 19)
    draw.text((tx, cy + 8), member.get("group", ""), font=gf, fill=(120, 120, 130))


def _connect(draw, src_cys, src_x, tgt_cys, tgt_x):
    """src(2N) → tgt(N) 브라켓 라인. bar 는 src_x 와 tgt_x 중간."""
    bar = (src_x + tgt_x) // 2
    for j in range(len(tgt_cys)):
        ya, yb = src_cys[2 * j], src_cys[2 * j + 1]
        ty = tgt_cys[j]
        draw.line([(src_x, ya), (bar, ya)], fill=LINE, width=3)
        draw.line([(src_x, yb), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ya), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ty), (tgt_x, ty)], fill=LINE, width=3)


def make_bracket_half(half: str, data: dict, output_path: Path,
                      vote_note: str = "🔴 32강 투표 진행 중 — 프로필에서 매치 참여!",
                      source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> Path:
    """half = 'top'(Q0·Q1) | 'bottom'(Q2·Q3)."""
    quarters = (0, 1) if half == "top" else (2, 3)
    half_label = "상반부 (A조·B조)" if half == "top" else "하반부 (C조·D조)"

    matches = [m for m in data["rounds"]["R32"]["matches"]
               if m["quarter"] in quarters]
    matches.sort(key=lambda m: (m["quarter"], m["slot"]))
    # 16 chip (매치 8개 × 2)
    chips = []
    for m in matches:
        chips.append(m["a"]); chips.append(m["b"])
    assert len(chips) == 16, f"{len(chips)} chips"

    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    em = _get_emoji_image("🏆", 70)
    title = "걸그룹 월드컵 대진표"
    tf = _font("Bold", 66)
    bb = tf.getbbox(title); tw = bb[2] - bb[0]
    sx = (CANVAS[0] - tw - 84) // 2
    if em:
        img.alpha_composite(em, (sx, 40))
    d.text((sx + 84, 44), title, font=tf, fill=GOLD, stroke_width=3, stroke_fill=INK)
    sf = _font("Bold", 40)
    _centered(d, f"32강 · {half_label}", sf, CANVAS[0] // 2, 130, fill=WHITE)
    hint = _font("Medium", 24)
    _centered(d, "숫자 = 브랜드평판 시드순위 · 빅매치는 결승까지 안 만남",
              hint, CANVAS[0] // 2, 192, fill=WHITE_DIM)

    # 컬럼 헤더
    colf = _font("Bold", 30)
    for i, lbl in enumerate(["32강", "16강", "8강", "4강", "결승"]):
        _centered(d, lbl, colf, COL_HEADERS_X[i], 244, fill=GOLD)

    # y 좌표 계산
    H = ZONE_BOT - ZONE_TOP
    chip_cy = [ZONE_TOP + (k + 0.5) * H / 16 for k in range(16)]
    r16 = [(chip_cy[2 * j] + chip_cy[2 * j + 1]) / 2 for j in range(8)]
    qf = [(r16[2 * j] + r16[2 * j + 1]) / 2 for j in range(4)]
    sf_cy = [(qf[2 * j] + qf[2 * j + 1]) / 2 for j in range(2)]
    fin = (sf_cy[0] + sf_cy[1]) / 2

    # 브라켓 라인 (chip → r16 → qf → sf → fin)
    _connect(d, chip_cy, CHIP_X1, r16, 300)
    _connect(d, r16, 300, qf, 490)
    _connect(d, qf, 490, sf_cy, 670)
    _connect(d, sf_cy, 670, [fin], 850)

    # chip 그리기 (라인 위에)
    for k in range(16):
        _chip(img, d, chip_cy[k], chips[k])

    # 결승 진출 슬롯 (끝점)
    fy0, fy1 = int(fin - 50), int(fin + 50)
    d.rounded_rectangle([870, fy0, 1056, fy1], radius=18,
                        fill=None, outline=GOLD, width=4)
    ff = _font("Bold", 34)
    _centered(d, "🏆", _font("Bold", 44), 963, fin - 46)
    _centered(d, "결승 진출", ff, 963, fin + 6, fill=GOLD)

    # 하단 투표 안내 박스
    d.rounded_rectangle([40, 1740, CANVAS[0] - 40, 1830], radius=20, fill=GOLD)
    vf = _font("Bold", 36)
    _centered(d, vote_note, vf, CANVAS[0] // 2, 1762, fill=INK)

    # 풋터
    mf = _font("Medium", 24)
    _centered(d, source_note, mf, CANVAS[0] // 2, 1850, fill=WHITE_DIM)
    _centered(d, "@daily_enter_kr · 매일 새로운 픽", mf, CANVAS[0] // 2, 1884,
              fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent
    data = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "output_enter" / "publish" / "worldcup_bracket"
    for half in ("top", "bottom"):
        out = out_dir / f"bracket_{half}.jpg"
        make_bracket_half(half, data, out)
        print(f"✓ {out} ({out.stat().st_size // 1024}KB)")
