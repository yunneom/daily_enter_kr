"""
사진 매트릭스 — 각 셀에 Unsplash 사진 배경 + 어두운 그라데이션 + 라벨 + 가격 배지.

[설계]
- 1080×1920 (9:16)
- 제목 / 룰 힌트 / 컬럼 헤더 (premium 과 동일)
- 셀 = 사진(center-crop, cover) + 하단 dark gradient + 상단 우측 가격 pill
- Unsplash 미설정 또는 다운 실패 시 그 셀만 단색 폴백 (이모지 대체)

사진 라이센스: Unsplash 라이센스 (상업 사용 가능, attribution 불필요).
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from image_provider import search_and_download
from make_premium_matrix import TIER_TOPS, HIGHLIGHT_YELLOW, INK, MUTED


CANVAS = (1080, 1920)
BG = (255, 255, 255)


def _cover_crop(src: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """target 영역을 완전히 덮도록 비율 유지 center-crop (CSS background-size: cover)."""
    sw, sh = src.size
    src_ratio = sw / sh
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        # 소스가 더 wide → 높이에 맞추고 좌우 잘라냄
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    src = src.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return src.crop((left, top, left + target_w, top + target_h))


def _gradient_overlay(w: int, h: int, top_alpha: int = 0, bot_alpha: int = 200) -> Image.Image:
    """위→아래로 알파 증가 그라데이션 (검정). 텍스트 가독성용."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(h):
        # 아래쪽 60% 만 어둡게 (텍스트 영역)
        if y < h * 0.4:
            a = top_alpha
        else:
            t = (y - h * 0.4) / (h * 0.6)
            a = int(top_alpha + (bot_alpha - top_alpha) * t)
        for x in range(w):
            px[x, y] = (0, 0, 0, a)
    return overlay


def make_photo_matrix(
    title: str,
    highlight: str,
    rule_hint: str,
    col_headers: List[str],
    row_prices: List[str],
    cells: List[List[dict]],   # cells[row][col] = {photo_query, label, fallback_emoji?}
    output_path: Path,
    brand: str = "",
):
    img = Image.new("RGB", CANVAS, BG).convert("RGBA")
    n_rows = len(row_prices)
    n_cols = len(col_headers)
    assert len(cells) == n_rows and all(len(r) == n_cols for r in cells)

    bold_path = _resolve_font("Bold")
    semi_path = _resolve_font("SemiBold")
    medium_path = _resolve_font("Medium")
    f_title = ImageFont.truetype(bold_path, 86)
    f_hint = ImageFont.truetype(medium_path, 36)
    f_col = ImageFont.truetype(bold_path, 48)
    f_price = ImageFont.truetype(bold_path, 44)
    f_cell = ImageFont.truetype(bold_path, 38)
    f_brand = ImageFont.truetype(medium_path, 30)

    draw = ImageDraw.Draw(img)

    # ─── 1) 제목 + 하이라이트 ───
    title_y = 120
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

    # 컬럼 헤더
    for c, hdr in enumerate(col_headers):
        cx = grid_left + c * cell_w + cell_w / 2
        bbox = f_col.getbbox(hdr)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((cx - w/2, grid_top + (header_h - h) / 2 - 4), hdr, font=f_col, fill=INK)

    # ─── 4) 셀 ───
    card_pad = 14
    radius = 30
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    for r in range(n_rows):
        tier = TIER_TOPS[r] if r < len(TIER_TOPS) else TIER_TOPS[-1]
        for c in range(n_cols):
            x0 = int(grid_left + c * cell_w + card_pad)
            y0 = int(grid_top + header_h + r * cell_h + card_pad)
            x1 = int(grid_left + (c + 1) * cell_w - card_pad)
            y1 = int(grid_top + header_h + (r + 1) * cell_h - card_pad)
            cw, ch = x1 - x0, y1 - y0

            cell = cells[r][c]
            query = cell.get("photo_query") or ""
            label = cell.get("label", "")

            # 사진 또는 단색 폴백
            photo_path = search_and_download(query, access_key) if query and access_key else None
            cell_layer = Image.new("RGBA", (cw, ch), (240, 240, 240, 255))
            if photo_path and Path(photo_path).exists():
                try:
                    src = Image.open(photo_path).convert("RGB")
                    cropped = _cover_crop(src, cw, ch)
                    cell_layer.paste(cropped.convert("RGBA"), (0, 0))
                except Exception as e:
                    print(f"  ⚠️  사진 로드 실패 ({query}): {e}")
                    # 폴백 — 티어 컬러
                    cell_layer = Image.new("RGBA", (cw, ch), (*tier["card"], 255))
            else:
                # 폴백 — 티어 컬러 + 이모지
                cell_layer = Image.new("RGBA", (cw, ch), (*tier["card"], 255))

            # 어두운 그라데이션 (라벨 가독성)
            grad = _gradient_overlay(cw, ch, top_alpha=20, bot_alpha=200)
            cell_layer = Image.alpha_composite(cell_layer, grad)

            # 라운드 마스크
            mask = Image.new("L", (cw, ch), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.rounded_rectangle([0, 0, cw, ch], radius=radius, fill=255)

            # 그림자
            sh = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
            sd = ImageDraw.Draw(sh)
            sd.rounded_rectangle([x0, y0 + 8, x1, y1 + 8], radius=radius, fill=(0, 0, 0, 70))
            sh = sh.filter(ImageFilter.GaussianBlur(radius=14))
            img = Image.alpha_composite(img, sh)

            # 셀 합성 (마스크 적용)
            img.paste(cell_layer, (x0, y0), mask)

            # 셀 outline
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=INK, width=3)

            # 가격 배지 — 우상단
            price_text = row_prices[r] if r < len(row_prices) else ""
            if price_text:
                pb = f_price.getbbox(price_text)
                pw = pb[2] - pb[0]
                ph = pb[3] - pb[1]
                badge_pad_x = 14
                badge_pad_y = 8
                badge_w = pw + badge_pad_x * 2
                badge_h = ph + badge_pad_y * 2 + 6
                badge_x1 = x1 - 14
                badge_x0 = badge_x1 - badge_w
                badge_y0 = y0 + 14
                badge_y1 = badge_y0 + badge_h
                draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1],
                                       radius=badge_h // 2, fill=tier["badge"])
                draw.text((badge_x0 + badge_pad_x, badge_y0 + badge_pad_y),
                          price_text, font=f_price, fill=(255, 255, 255))

            # 라벨 — 하단 흰 글자 (그라데이션 위)
            lbl_y = y1 - 70
            lw = draw.textlength(label, font=f_cell)
            cx = (x0 + x1) // 2
            # 흰 글자 + 검정 약간 outline
            draw.text((cx - lw/2 + 2, lbl_y + 2), label, font=f_cell, fill=(0, 0, 0, 200))
            draw.text((cx - lw/2, lbl_y), label, font=f_cell, fill=(255, 255, 255))

    # 브랜드
    if brand:
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 80), brand, font=f_brand, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92)
    return output_path
