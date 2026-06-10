"""
엠블럼 카드 매트릭스 — FIFA Ultimate Team 스타일 카드 그리드.

각 셀 = 카드 (골드/실버/브론즈 티어 그라데이션 배경 + 역할 이모지 + 실명).
배경은 soccer (축구장 잔디 그라데이션) 또는 gradient_idol (보라/핑크 그라데이션).
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image, _wrap_label
from make_premium_matrix import HIGHLIGHT_YELLOW, INK, MUTED


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)

# 티어별 (위→아래: 골드/실버/브론즈) — fill_top, fill_bot, border, glow
TIER_STYLES = [
    {"fill_top": (255, 215, 0),   "fill_bot": (184, 134, 11),
     "border": (139, 100, 0),     "glow": (255, 215, 0, 80),
     "text_color": (40, 24, 0),   "tier_label": "GOLD"},
    {"fill_top": (232, 232, 232), "fill_bot": (168, 168, 168),
     "border": (110, 110, 110),   "glow": (200, 200, 200, 60),
     "text_color": (30, 30, 30),  "tier_label": "SILVER"},
    {"fill_top": (232, 168, 120), "fill_bot": (139, 69, 19),
     "border": (101, 50, 14),     "glow": (200, 110, 50, 60),
     "text_color": (40, 18, 0),   "tier_label": "BRONZE"},
]


def _vertical_gradient(size: Tuple[int, int],
                      top_color: Tuple[int, int, int],
                      bot_color: Tuple[int, int, int]) -> Image.Image:
    """위→아래 RGB 보간 그라데이션."""
    w, h = size
    img = Image.new("RGB", size, top_color)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_color[0] * (1 - t) + bot_color[0] * t)
        g = int(top_color[1] * (1 - t) + bot_color[1] * t)
        b = int(top_color[2] * (1 - t) + bot_color[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _background(style: str) -> Image.Image:
    """전체 배경 — 축구장 / 아이돌 그라데이션."""
    if style == "soccer":
        # 어두운 잔디 그린 → 밝은 잔디
        bg = _vertical_gradient(CANVAS, (45, 80, 22), (74, 139, 42))
        # 살짝 가로 라인 (잔디 줄무늬 효과)
        draw = ImageDraw.Draw(bg)
        for i in range(8):
            y = int(CANVAS[1] * (i + 1) / 9)
            band_color = (45, 90, 25) if i % 2 == 0 else (74, 135, 45)
            draw.rectangle([0, y, CANVAS[0], y + 14], fill=band_color)
        return bg
    elif style == "gradient_idol":
        # 보라/핑크 그라데이션 (K-pop 무대 느낌)
        return _vertical_gradient(CANVAS, (52, 30, 100), (200, 80, 160))
    elif style == "gradient_dark":
        # 어두운 네이비 → 보라
        return _vertical_gradient(CANVAS, (25, 30, 60), (90, 50, 130))
    else:
        return Image.new("RGB", CANVAS, WHITE)


def _draw_emblem_card(img: Image.Image, rect: Tuple[int, int, int, int],
                      tier_style: dict, role_emoji: str, name: str,
                      subtitle: str = "",
                      font_paths: dict = None):
    """단일 엠블럼 카드를 img 위에 그림 (in-place)."""
    x0, y0, x1, y1 = rect
    cw, ch = x1 - x0, y1 - y0

    # 1) 카드 내부 — 그라데이션 fill
    grad = _vertical_gradient((cw, ch), tier_style["fill_top"], tier_style["fill_bot"])

    # 2) 마스크 (라운드 모서리)
    mask = Image.new("L", (cw, ch), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, cw, ch], radius=24, fill=255)

    # 3) 외부 글로우 (티어 컬러 블러)
    glow_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    gdraw.rounded_rectangle([x0 - 4, y0 + 6, x1 + 4, y1 + 12], radius=28,
                            fill=tier_style["glow"])
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=18))
    img.alpha_composite(glow_layer)

    # 4) 카드 합성
    img.paste(grad.convert("RGBA"), (x0, y0), mask)

    # 5) 보더 (라운드 사각형)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24,
                           outline=tier_style["border"], width=4)

    # 6) 역할 이모지 (중앙 상단)
    bold = font_paths.get("Bold") if font_paths else _resolve_font("Bold")
    semi = font_paths.get("SemiBold") if font_paths else _resolve_font("SemiBold")
    medium = font_paths.get("Medium") if font_paths else _resolve_font("Medium")

    # 이모지 크기 — 셀 높이의 ~40%
    emoji_size = int(ch * 0.40)
    em_img = _get_emoji_image(role_emoji, emoji_size) if role_emoji else None
    if em_img:
        em_x = int(x0 + (cw - emoji_size) / 2)
        em_y = int(y0 + ch * 0.18)
        img.alpha_composite(em_img, (em_x, em_y))

    # 7) 실명 (Bold, 2줄 wrap 가능)
    name_font = ImageFont.truetype(bold, 42)
    name_color = tier_style["text_color"]
    max_name_w = cw - 30
    name_lines = _wrap_label(name, name_font, max_name_w)
    if len(name_lines) > 2:
        name_lines = name_lines[:2]
    name_block_h = name_font.size * len(name_lines) + 4 * (len(name_lines) - 1)
    name_y = y1 - 80 - name_block_h
    cx = x0 + cw / 2
    for line in name_lines:
        bbox = name_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw / 2, name_y), line, font=name_font, fill=name_color)
        name_y += name_font.size + 4

    # 8) 서브타이틀 (역할/등번호) — 카드 하단
    if subtitle:
        sub_font = ImageFont.truetype(medium, 26)
        bbox = sub_font.getbbox(subtitle)
        sw = bbox[2] - bbox[0]
        # 살짝 어둡게 (티어 컬러 대비)
        sub_color = (name_color[0], name_color[1], name_color[2], 180)
        draw.text((cx - sw / 2, y1 - 50), subtitle, font=sub_font, fill=sub_color)

    # 9) 티어 라벨 (좌상단 작은 칩)
    tier_label = tier_style["tier_label"]
    tier_font = ImageFont.truetype(bold, 18)
    tb = tier_font.getbbox(tier_label)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    pad_x, pad_y = 10, 4
    chip_x0 = x0 + 14
    chip_y0 = y0 + 14
    chip_x1 = chip_x0 + tw + pad_x * 2
    chip_y1 = chip_y0 + th + pad_y * 2 + 4
    draw.rounded_rectangle([chip_x0, chip_y0, chip_x1, chip_y1],
                           radius=8, fill=(255, 255, 255, 200))
    draw.text((chip_x0 + pad_x, chip_y0 + pad_y),
              tier_label, font=tier_font, fill=tier_style["border"])


def make_emblem_matrix(
    title: str,
    highlight: str,
    rule_hint: str,
    col_headers: List[str],
    row_prices: List[str],
    cells: List[List[dict]],
    output_path: Path,
    brand: str = "",
    background_style: str = "soccer",   # "soccer" / "gradient_idol" / "gradient_dark"
):
    """FIFA-카드 매트릭스. 각 셀은 {role_emoji, name, subtitle?} 딕트.

    행 인덱스 = TIER_STYLES 인덱스 (0=골드 5천원, 1=실버 3천원, 2=브론즈 2천원).
    """
    n_rows = len(row_prices)
    n_cols = len(col_headers)
    assert len(cells) == n_rows and all(len(r) == n_cols for r in cells)
    assert n_rows == 3, "3 가격 티어 전용 (골드/실버/브론즈)"

    img = _background(background_style).convert("RGBA")

    # 폰트
    bold_path = _resolve_font("Bold")
    semi_path = _resolve_font("SemiBold")
    medium_path = _resolve_font("Medium")
    regular_path = _resolve_font("Regular")
    font_paths = {"Bold": bold_path, "SemiBold": semi_path,
                  "Medium": medium_path, "Regular": regular_path}

    f_title = ImageFont.truetype(bold_path, 86)
    f_hint = ImageFont.truetype(medium_path, 36)
    f_col = ImageFont.truetype(bold_path, 44)
    f_price = ImageFont.truetype(bold_path, 38)
    f_brand = ImageFont.truetype(medium_path, 30)

    draw = ImageDraw.Draw(img)

    # ─── 1) 제목 (강조 단어 형광) ───
    title_y = 220
    title_w = draw.textlength(title, font=f_title)
    title_x = (CANVAS[0] - title_w) / 2
    if highlight and highlight in title:
        before = title.split(highlight, 1)[0]
        bw = draw.textlength(before, font=f_title)
        hw = draw.textlength(highlight, font=f_title)
        hl_x0 = int(title_x + bw - 6)
        hl_y0 = int(title_y + 16)
        hl_x1 = int(title_x + bw + hw + 6)
        hl_y1 = int(title_y + 100)
        draw.rounded_rectangle([hl_x0, hl_y0, hl_x1, hl_y1], radius=8,
                               fill=HIGHLIGHT_YELLOW)
    draw.text((title_x, title_y), title, font=f_title, fill=WHITE)

    # ─── 2) 룰 힌트 ───
    hint_y = title_y + 130
    hint_w = draw.textlength(rule_hint, font=f_hint)
    draw.text(((CANVAS[0] - hint_w) / 2, hint_y), rule_hint,
              font=f_hint, fill=(230, 230, 230))

    # ─── 3) 격자 영역 ───
    grid_top = hint_y + 90
    grid_bottom = CANVAS[1] - 360
    grid_left = 70
    grid_right = CANVAS[0] - 70
    header_h = 80

    cell_w = (grid_right - grid_left) / n_cols
    cell_h = (grid_bottom - grid_top - header_h) / n_rows

    # ─── 4) 컬럼 헤더 (역할/포지션) ───
    for c, hdr in enumerate(col_headers):
        cx = grid_left + c * cell_w + cell_w / 2
        bbox = f_col.getbbox(hdr)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((cx - w/2, grid_top + (header_h - h) / 2 - 4),
                  hdr, font=f_col, fill=WHITE)

    # ─── 5) 셀 카드 ───
    card_pad = 12
    for r in range(n_rows):
        tier = TIER_STYLES[r]
        for c in range(n_cols):
            x0 = int(grid_left + c * cell_w + card_pad)
            y0 = int(grid_top + header_h + r * cell_h + card_pad)
            x1 = int(grid_left + (c + 1) * cell_w - card_pad)
            y1 = int(grid_top + header_h + (r + 1) * cell_h - card_pad)

            cell = cells[r][c]
            _draw_emblem_card(
                img, (x0, y0, x1, y1), tier,
                role_emoji=cell.get("role_emoji", ""),
                name=cell.get("name", ""),
                subtitle=cell.get("subtitle", row_prices[r]),
                font_paths=font_paths,
            )

    # ─── 6) 브랜드 ───
    if brand:
        draw = ImageDraw.Draw(img)
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 220),
                  brand, font=f_brand, fill=(220, 220, 220))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92)
    return output_path
