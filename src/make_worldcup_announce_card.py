"""
월드컵 라운드 결과 발표 카드 — 진출자 N명 그리드.

R32 → 16명 진출 (4x4 grid)
R16 → 8명 진출 (4x2 grid)
R8  → 4명 진출 (2x2 grid + "결승 진출!" 강조)
R4  → 2명 진출 (좌우 결승 라인업 + 3위전 라인업)
R1  → 🏆 1·2·3위 발표 (시상대 형식)
"""

import sys
from pathlib import Path
from typing import Dict, List
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
SILVER = (200, 200, 220)
BRONZE = (200, 130, 90)
RED = (236, 64, 102)
PINK = (255, 102, 184)
WHITE_DIM = (220, 215, 235)
CARD_BG = (255, 255, 255)


def _font(weight, size):
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _draw_centered(draw, text, font, cx, y, fill=WHITE, stroke=0, stroke_fill=None):
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kw = dict(font=font, fill=fill)
    if stroke:
        kw["stroke_width"] = stroke
        kw["stroke_fill"] = stroke_fill or INK
    draw.text((cx - w / 2, y), text, **kw)


def _member_mini(img, x, y, w, h, member: Dict):
    """진출자 미니 카드 — 그룹 emoji + 이름 + 그룹."""
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w, y + h], radius=18,
                        fill=CARD_BG, outline=GOLD, width=3)
    grp = member.get("group", "")
    em = _get_emoji_image(group_emoji_for(grp), max(48, w // 6))
    if em:
        es = em.size[0]
        img.alpha_composite(em, (x + (w - es) // 2, y + 18))
    nf = _font("Bold", max(28, w // 10))
    name = member.get("member", "")
    bb = nf.getbbox(name)
    nw = bb[2] - bb[0]
    d.text((x + (w - nw) / 2, y + h - 90), name, font=nf, fill=INK)
    gf = _font("Medium", max(20, w // 14))
    bb = gf.getbbox(grp)
    gw = bb[2] - bb[0]
    d.text((x + (w - gw) / 2, y + h - 48), grp, font=gf, fill=(120, 120, 130))


def make_round_announce_card(
    round_label: str,           # "32강 → 16강"
    title: str,                 # "🏆 16강 진출자!"
    sub: str,                   # "총 16명, 다음 라운드 6/24 21:00"
    members: List[Dict],
    output_path: Path,
    cols: int = 4,
    source_note: str = "출처: 한국기업평판연구소 2026.6.21",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
) -> Path:
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    rf = _font("Bold", 48)
    _draw_centered(d, round_label, rf, CANVAS[0] // 2, 60, fill=WHITE_DIM)
    tf = _font("Bold", 100)
    _draw_centered(d, title, tf, CANVAS[0] // 2, 130, fill=GOLD,
                   stroke=3, stroke_fill=INK)
    sf = _font("Medium", 36)
    _draw_centered(d, sub, sf, CANVAS[0] // 2, 256, fill=WHITE_DIM)

    # 진출자 grid
    n = len(members)
    rows = (n + cols - 1) // cols
    gap = 20
    grid_top = 340
    grid_bot = 1700
    avail_w = CANVAS[0] - 80 - (cols - 1) * gap
    avail_h = grid_bot - grid_top - (rows - 1) * gap
    cell_w = avail_w // cols
    cell_h = avail_h // rows
    grid_left = 40

    for i, m in enumerate(members):
        r = i // cols
        c = i % cols
        x = grid_left + c * (cell_w + gap)
        y = grid_top + r * (cell_h + gap)
        _member_mini(img, x, y, cell_w, cell_h, m)

    # 풋터
    d = ImageDraw.Draw(img)
    f = _font("Medium", 26)
    _draw_centered(d, source_note, f, CANVAS[0] // 2, 1820, fill=WHITE_DIM)
    _draw_centered(d, brand, f, CANVAS[0] // 2, 1862, fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


def make_podium_card(
    winner: Dict, second: Dict, third: Dict,
    output_path: Path,
    source_note: str = "출처: 한국기업평판연구소 2026.6.21",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
) -> Path:
    """우승 발표 카드 — 시상대 형식 (1·2·3위)."""
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    em = _get_emoji_image("🏆", 200)
    if em:
        img.alpha_composite(em, ((CANVAS[0] - 200) // 2, 60))
    tf = _font("Bold", 110)
    _draw_centered(d, "걸그룹 월드컵", tf, CANVAS[0] // 2, 280, fill=GOLD,
                   stroke=3, stroke_fill=INK)
    sf = _font("Bold", 88)
    _draw_centered(d, "최종 결과", sf, CANVAS[0] // 2, 410, fill=WHITE)

    # 시상대 — 가운데 1위(높음), 좌 2위, 우 3위
    podium = [
        ("🥇 1위", winner,  CANVAS[0] // 2 - 200, 580, 400, 580, GOLD),    # 중앙 우승
        ("🥈 2위", second,  60,                    760, 360, 480, SILVER),  # 좌측
        ("🥉 3위", third,   CANVAS[0] - 60 - 360,  760, 360, 480, BRONZE),  # 우측
    ]
    for label, m, x, y, w, h, color in podium:
        d.rounded_rectangle([x, y, x + w, y + h], radius=22,
                            fill=CARD_BG, outline=color, width=6)
        lf = _font("Bold", 56)
        _draw_centered(d, label, lf,
                       x + w // 2, y + 18, fill=color, stroke=2, stroke_fill=INK)
        em_sz = w // 4
        em = _get_emoji_image(group_emoji_for(m.get("group", "")), em_sz)
        if em:
            img.alpha_composite(em, (x + (w - em_sz) // 2, y + 100))
        nf = _font("Bold", w // 8)
        name = m.get("member", "")
        bb = nf.getbbox(name)
        nw = bb[2] - bb[0]
        d.text((x + (w - nw) / 2, y + h - 160), name, font=nf, fill=INK)
        gf = _font("Medium", w // 14)
        grp = m.get("group", "")
        bb = gf.getbbox(grp)
        gw = bb[2] - bb[0]
        d.text((x + (w - gw) / 2, y + h - 90), grp, font=gf, fill=(120, 120, 130))
        rk = m.get("rank")
        if rk:
            rf2 = _font("Bold", 24)
            rstr = f"BR #{rk}위"
            bb = rf2.getbbox(rstr)
            d.text((x + (w - bb[2]) / 2, y + h - 50), rstr,
                   font=rf2, fill=color)

    # CTA
    cta_f = _font("Bold", 48)
    _draw_centered(d, "🙌 우승 축하 댓글 ⬇️", cta_f, CANVAS[0] // 2, 1660,
                   fill=WHITE, stroke=2, stroke_fill=INK)

    # 풋터
    f = _font("Medium", 26)
    _draw_centered(d, source_note, f, CANVAS[0] // 2, 1820, fill=WHITE_DIM)
    _draw_centered(d, brand, f, CANVAS[0] // 2, 1862, fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path
