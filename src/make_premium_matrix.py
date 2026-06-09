"""
프리미엄 비교 매트릭스 — 3D 카드 룩 (드롭섀도우 + 행별 가격티어 컬러).

"XX원으로 ~하기" 게임 포맷 전용. 각 셀이 raised 카드처럼 보임.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image, _wrap_label


CANVAS = (1080, 1920)
BG = (255, 255, 255)
INK = (24, 24, 28)
MUTED = (150, 150, 158)
HIGHLIGHT_YELLOW = (255, 234, 0)

# 행별 가격 티어 — 위(고액)부터 아래(저액). 부드러운 톤.
TIER_TOPS = [
    {"badge": (218, 165, 32), "card": (255, 248, 230), "tint": (255, 248, 230)},   # 고액 — 골드
    {"badge": (130, 140, 150), "card": (245, 247, 250), "tint": (245, 247, 250)},  # 중간 — 실버 / 뉴트럴
    {"badge": (130, 90, 50), "card": (250, 244, 235), "tint": (250, 244, 235)},    # 저액 — 브론즈/코퍼
]

SHADOW_OFFSET = (0, 8)
SHADOW_BLUR = 14
SHADOW_ALPHA = 70  # 0-255


def _draw_shadow(canvas_size, rect, radius):
    """rect 모양의 블러 처리된 그림자 레이어를 반환 (RGBA Image)."""
    sh = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    x0, y0, x1, y1 = rect
    x0 += SHADOW_OFFSET[0]; y0 += SHADOW_OFFSET[1]
    x1 += SHADOW_OFFSET[0]; y1 += SHADOW_OFFSET[1]
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(0, 0, 0, SHADOW_ALPHA))
    return sh.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))


def make_premium_matrix(
    title: str,
    highlight: str,
    rule_hint: str,
    col_headers: List[str],            # 카테고리 (3개)
    row_prices: List[str],             # 가격 위→아래 (고→저)
    cells: List[List[dict]],           # cells[row][col] — {emoji, label}
    output_path: Path,
    brand: str = "",
):
    img = Image.new("RGB", CANVAS, BG).convert("RGBA")
    n_rows = len(row_prices)
    n_cols = len(col_headers)
    assert len(cells) == n_rows and all(len(r) == n_cols for r in cells)
    assert n_rows == len(TIER_TOPS) == 3, "3 가격 티어 전용"

    # 폰트
    bold_path = _resolve_font("Bold")
    semi_path = _resolve_font("SemiBold")
    medium_path = _resolve_font("Medium")
    f_title = ImageFont.truetype(bold_path, 86)
    f_hint = ImageFont.truetype(medium_path, 36)
    f_col = ImageFont.truetype(bold_path, 48)
    f_price = ImageFont.truetype(bold_path, 52)
    f_cell = ImageFont.truetype(semi_path, 38)
    f_brand = ImageFont.truetype(medium_path, 30)

    # ─── 1) 제목 (강조 단어 노란 형광) ───
    draw = ImageDraw.Draw(img)
    title_y = 120
    title_w = draw.textlength(title, font=f_title)
    title_x = (CANVAS[0] - title_w) / 2
    # 강조 형광
    if highlight and highlight in title:
        before = title.split(highlight, 1)[0]
        bw = draw.textlength(before, font=f_title)
        hw = draw.textlength(highlight, font=f_title)
        # 형광 사각형 (글자 뒤에)
        hl_x0 = int(title_x + bw - 6)
        hl_y0 = int(title_y + 16)
        hl_x1 = int(title_x + bw + hw + 6)
        hl_y1 = int(title_y + 100)
        draw.rounded_rectangle([hl_x0, hl_y0, hl_x1, hl_y1], radius=8, fill=HIGHLIGHT_YELLOW)
    draw.text((title_x, title_y), title, font=f_title, fill=INK)

    # ─── 2) 룰 힌트 ───
    hint_y = title_y + 130
    hint_w = draw.textlength(rule_hint, font=f_hint)
    draw.text(((CANVAS[0] - hint_w) / 2, hint_y), rule_hint, font=f_hint, fill=MUTED)

    # ─── 3) 격자 영역 ───
    grid_top = hint_y + 90
    grid_bottom = CANVAS[1] - 220
    grid_left = 70
    grid_right = CANVAS[0] - 70
    header_h = 80

    cell_w = (grid_right - grid_left) / n_cols
    cell_h = (grid_bottom - grid_top - header_h) / n_rows

    # ─── 4) 컬럼 헤더 (카테고리) ───
    for c, hdr in enumerate(col_headers):
        cx = grid_left + c * cell_w + cell_w / 2
        bbox = f_col.getbbox(hdr)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((cx - w/2, grid_top + (header_h - h) / 2 - 4), hdr, font=f_col, fill=INK)

    # ─── 5) 셀 그리기 — 드롭섀도우 → 카드 → 콘텐츠 ───
    card_pad = 14
    radius = 30
    for r in range(n_rows):
        tier = TIER_TOPS[r]
        for c in range(n_cols):
            x0 = int(grid_left + c * cell_w + card_pad)
            y0 = int(grid_top + header_h + r * cell_h + card_pad)
            x1 = int(grid_left + (c + 1) * cell_w - card_pad)
            y1 = int(grid_top + header_h + (r + 1) * cell_h - card_pad)

            # 그림자
            shadow = _draw_shadow(CANVAS, (x0, y0, x1, y1), radius)
            img = Image.alpha_composite(img, shadow)
            draw = ImageDraw.Draw(img)

            # 카드 본체
            draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                                   fill=tier["card"], outline=INK, width=3)

            # 가격 배지 — 우측 상단 작은 pill
            price_text = row_prices[r]
            pb = f_price.getbbox(price_text)
            pw = pb[2] - pb[0]
            ph = pb[3] - pb[1]
            badge_pad_x = 16
            badge_pad_y = 10
            badge_w = pw + badge_pad_x * 2
            badge_h = ph + badge_pad_y * 2 + 8
            badge_x1 = x1 - 16
            badge_x0 = badge_x1 - badge_w
            badge_y0 = y0 + 16
            badge_y1 = badge_y0 + badge_h
            draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1],
                                   radius=badge_h // 2, fill=tier["badge"])
            draw.text((badge_x0 + badge_pad_x, badge_y0 + badge_pad_y),
                      price_text, font=f_price, fill=(255, 255, 255))

            # 이모지 (큰 사이즈, 중앙)
            cell = cells[r][c]
            emoji_size = int(cell_h * 0.42)
            em_img = _get_emoji_image(cell.get("emoji", ""), emoji_size) if cell.get("emoji") else None
            cx = (x0 + x1) // 2
            label = cell.get("label", "")
            label_lines = _wrap_label(label, f_cell, x1 - x0 - 40)
            line_h = f_cell.size + 6
            label_block_h = line_h * len(label_lines)

            content_top = y0 + 90  # 가격 배지 아래
            content_bottom = y1 - 30
            content_h = content_bottom - content_top
            stack_h = (emoji_size if em_img else 0) + 14 + label_block_h
            stack_top = content_top + (content_h - stack_h) // 2

            if em_img:
                em_x = int(cx - emoji_size / 2)
                em_y = int(stack_top)
                img.alpha_composite(em_img, (em_x, em_y))
                label_y = em_y + emoji_size + 14
            else:
                label_y = int(stack_top)

            draw = ImageDraw.Draw(img)
            for line in label_lines:
                lw = draw.textlength(line, font=f_cell)
                draw.text((cx - lw / 2, label_y), line, font=f_cell, fill=INK)
                label_y += line_h

    # ─── 6) 브랜드 ───
    if brand:
        draw = ImageDraw.Draw(img)
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 80), brand, font=f_brand, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path
