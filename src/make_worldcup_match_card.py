"""
걸그룹 월드컵 매치 카드 — 1080x1920 9:16. 게시글당 2매치 콤비 4지선다.

[레이아웃]
  상단: 🏆 걸그룹 월드컵 [라운드] · 게시글 N/M
  중상: 매치1 — 멤버A vs 멤버B (큰 카드 2개, VS 강조)
  중하: 매치2 — 멤버C vs 멤버D
  하단: 4지선다 (2x2 grid) — "1. A+C / 2. A+D / 3. B+C / 4. B+D"
        "💬 댓글에 번호로 투표 ⬇️"
  풋터: 출처 + brand

[디자인 톤]
브랜드평판 차트와 비슷한 다크 그라데이션 (네이비→마젠타). 빅매치 느낌.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)

# 색 — 빅매치 분위기
BG_TOP = (28, 22, 68)
BG_BOT = (78, 28, 96)
GOLD = (255, 220, 120)
RED = (236, 64, 102)
PINK = (255, 102, 184)
PINK_LIGHT = (255, 200, 224)
WHITE_DIM = (220, 215, 235)
CARD_BG = (255, 255, 255)
VS_RED = (220, 50, 90)


def _font(weight: str, size: int):
    p = _resolve_font(weight)
    return ImageFont.truetype(p, size)


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


def _member_card(img: Image.Image, x: int, y: int, w: int, h: int,
                 member: Dict, label_number: int,
                 role_emoji: str = "✨"):
    """단일 멤버 카드 — 흰 박스 + 이름 + 그룹 + 번호 배지."""
    d = ImageDraw.Draw(img)
    # 카드 박스
    d.rounded_rectangle([x, y, x + w, y + h], radius=24,
                        fill=CARD_BG, outline=GOLD, width=4)
    # 번호 배지 (좌상단)
    badge_r = 38
    bx, by = x + 14, y + 14
    d.ellipse([bx, by, bx + badge_r * 2, by + badge_r * 2], fill=RED)
    bf = _font("Bold", 48)
    nstr = str(label_number)
    bb = bf.getbbox(nstr)
    nw = bb[2] - bb[0]
    d.text((bx + badge_r - nw / 2 - 2, by + 4), nstr,
           font=bf, fill=WHITE)
    # 이모지 (중앙 상단)
    em = _get_emoji_image(role_emoji, 110)
    if em:
        img.alpha_composite(em, (x + (w - 110) // 2, y + 90))
    # 이름 (중앙)
    name = member.get("member", "")
    nf = _font("Bold", 58)
    bb = nf.getbbox(name)
    nw = bb[2] - bb[0]
    d.text((x + (w - nw) / 2, y + 220), name, font=nf, fill=INK)
    # 그룹 (이름 아래)
    grp = member.get("group", "")
    gf = _font("Medium", 32)
    bb = gf.getbbox(grp)
    gw = bb[2] - bb[0]
    d.text((x + (w - gw) / 2, y + 286), grp, font=gf, fill=(120, 120, 130))
    # BR 순위 (선택)
    rk = member.get("rank")
    if rk:
        rf = _font("Bold", 26)
        rstr = f"BR #{rk}위"
        bb = rf.getbbox(rstr)
        rw = bb[2] - bb[0]
        # 우하단
        d.rounded_rectangle([x + w - rw - 36, y + h - 50,
                             x + w - 14, y + h - 14],
                            radius=12, fill=GOLD)
        d.text((x + w - rw - 25, y + h - 46), rstr,
               font=rf, fill=INK)


def _match_block(img: Image.Image, x0: int, y0: int, width: int,
                 match_idx: int, a: Dict, b: Dict,
                 a_label: int, b_label: int):
    """매치 1개 — 두 멤버 카드 + 중앙 VS."""
    d = ImageDraw.Draw(img)
    # 매치 라벨
    lf = _font("Bold", 36)
    lbl = f"매치 {match_idx}"
    bb = lf.getbbox(lbl)
    lw = bb[2] - bb[0]
    # 배경 캡슐
    cap_x = x0 + (width - lw - 40) // 2
    d.rounded_rectangle([cap_x, y0, cap_x + lw + 40, y0 + 50],
                        radius=24, fill=PINK)
    d.text((cap_x + 20, y0 + 5), lbl, font=lf, fill=WHITE)

    # 멤버 카드 2개 + 중앙 VS
    card_y = y0 + 70
    card_h = 380
    gap = 24
    vs_w = 100
    card_w = (width - vs_w - 2 * gap) // 2
    left_x = x0
    right_x = x0 + card_w + gap + vs_w + gap

    role = "💃" if match_idx % 2 == 0 else "✨"
    _member_card(img, left_x, card_y, card_w, card_h, a, a_label, role_emoji=role)
    _member_card(img, right_x, card_y, card_w, card_h, b, b_label, role_emoji=role)

    # VS 텍스트 (중앙)
    vsf = _font("Bold", 120)
    vs_text = "VS"
    bb = vsf.getbbox(vs_text)
    vw = bb[2] - bb[0]
    vh = bb[3] - bb[1]
    vs_cx = x0 + card_w + gap + vs_w // 2
    vs_cy = card_y + card_h // 2
    d.text((vs_cx - vw / 2, vs_cy - vh / 2 - 18), vs_text,
           font=vsf, fill=VS_RED, stroke_width=4, stroke_fill=WHITE)


def _choice_grid(img: Image.Image, y_start: int,
                 a: Dict, b: Dict, c: Dict, d_m: Dict):
    """하단 4지선다 grid 2x2 — 콤비네이션 카드.
    1: A+C / 2: A+D / 3: B+C / 4: B+D
    """
    draw = ImageDraw.Draw(img)
    # 헤더
    hf = _font("Bold", 48)
    _draw_centered(draw, "💬 댓글에 번호로 투표 ⬇️", hf,
                   CANVAS[0] // 2, y_start, fill=WHITE,
                   stroke=2, stroke_fill=INK)

    combos = [
        (1, a, c),
        (2, a, d_m),
        (3, b, c),
        (4, b, d_m),
    ]
    grid_top = y_start + 70
    cell_w = 480
    cell_h = 110
    gap_x = 24
    gap_y = 18
    grid_x0 = (CANVAS[0] - 2 * cell_w - gap_x) // 2

    cf_num = _font("Bold", 64)
    cf_txt = _font("Bold", 36)

    for i, (n, m1, m2) in enumerate(combos):
        r = i // 2
        c = i % 2
        x = grid_x0 + c * (cell_w + gap_x)
        y = grid_top + r * (cell_h + gap_y)
        # 박스
        draw.rounded_rectangle([x, y, x + cell_w, y + cell_h],
                               radius=20, fill=CARD_BG,
                               outline=PINK, width=4)
        # 번호 배지
        d_ = ImageDraw.Draw(img)
        d_.ellipse([x + 12, y + 18, x + 12 + 74, y + 18 + 74], fill=RED)
        ns = str(n)
        bb = cf_num.getbbox(ns)
        nw = bb[2] - bb[0]
        d_.text((x + 12 + 37 - nw / 2 - 2, y + 22), ns,
                font=cf_num, fill=WHITE)
        # 콤비 텍스트 — "장원영 + 카리나"
        txt = f"{m1['member']} + {m2['member']}"
        bb = cf_txt.getbbox(txt)
        tw = bb[2] - bb[0]
        # 너비 초과 시 폰트 다운
        if tw > cell_w - 110:
            cf_txt2 = _font("Bold", 28)
            bb = cf_txt2.getbbox(txt)
            tw = bb[2] - bb[0]
            d_.text((x + 100 + (cell_w - 110 - tw) / 2, y + 38),
                    txt, font=cf_txt2, fill=INK)
        else:
            d_.text((x + 100 + (cell_w - 110 - tw) / 2, y + 30),
                    txt, font=cf_txt, fill=INK)


def make_worldcup_match_card(
    round_label: str,            # "32강" / "16강" ...
    post_index: int,             # 1-based
    post_total: int,
    match1: Dict,                # {"a": {rank,group,member}, "b": {...}}
    match2: Dict,
    output_path: Path,
    source_note: str = "출처: 한국기업평판연구소 2026.6.21",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
) -> Path:
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # === 헤더 ===
    title_f = _font("Bold", 80)
    sub_f = _font("Bold", 42)
    trophy = "🏆"
    em = _get_emoji_image(trophy, 80)
    title_text = f"걸그룹 월드컵 {round_label}"
    bb = title_f.getbbox(title_text)
    tw = bb[2] - bb[0]
    # 트로피 이모지 + 텍스트 중앙 정렬
    total_w = 90 + tw
    start_x = (CANVAS[0] - total_w) // 2
    if em:
        img.alpha_composite(em, (start_x, 56))
    d.text((start_x + 90, 56), title_text, font=title_f, fill=GOLD,
           stroke_width=3, stroke_fill=INK)

    # 게시글 인덱스
    sub_text = f"게시글 {post_index} / {post_total}"
    _draw_centered(d, sub_text, sub_f, CANVAS[0] // 2, 170,
                   fill=WHITE_DIM)

    # === 매치 1 ===
    _match_block(img, 30, 245, CANVAS[0] - 60, 1,
                 match1["a"], match1["b"], a_label=1, b_label=2)

    # === 매치 2 ===
    _match_block(img, 30, 765, CANVAS[0] - 60, 2,
                 match2["a"], match2["b"], a_label=3, b_label=4)

    # === 4지선다 ===
    _choice_grid(img, 1310, match1["a"], match1["b"],
                 match2["a"], match2["b"])

    # === 풋터 ===
    d = ImageDraw.Draw(img)
    sf = _font("Medium", 26)
    _draw_centered(d, source_note, sf, CANVAS[0] // 2, 1820,
                   fill=WHITE_DIM)
    _draw_centered(d, brand, sf, CANVAS[0] // 2, 1862,
                   fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    import json
    ROOT = Path(__file__).parent.parent
    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    posts = bracket["rounds"]["R32"]["posts"]
    out_dir = ROOT / "output_enter" / "publish" / "worldcup_r32"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 샘플: 게시글 1
    p = posts[0]
    out = out_dir / f"post_{p['post_idx']+1:02d}.jpg"
    make_worldcup_match_card(
        round_label="32강",
        post_index=p["post_idx"] + 1,
        post_total=len(posts),
        match1=p["match1"], match2=p["match2"],
        output_path=out,
    )
    print(f"✓ {out} ({out.stat().st_size // 1024} KB)")
