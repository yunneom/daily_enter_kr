"""
비교 매트릭스 카드 — N×M 표 형식. IG static image post 용.

[디자인]
- 1080x1920 (9:16) — Reels/Stories 호환 또는 IG static post 가능
- 상단 제목 + 노란 형광 하이라이트 (특정 단어 강조)
- 격자: 행 라벨(좌) × 열 헤더(상)
- 각 셀: Twemoji 컬러 이모지 + 한국어 설명
- 손그림 느낌 테두리 (살짝 wobble)
- 하단 브랜드 라인

[Twemoji 컬러 이모지]
PIL 기본 폰트는 이모지를 outline 로만 그림 → Twemoji PNG 를 raw.githubusercontent.com 에서
다운로드해 캐시 → 셀에 합성. 컬러풀하고 통일감 있음 (트위터에서 사용하는 그 이모지).

[사용 예]
make_comparison_matrix(
    title="월급별 추천 절세 상품",
    highlight="절세 상품",
    col_headers=["300만원", "500만원", "1억"],
    row_headers=["청약저축", "ISA", "연금저축"],
    cells=[
        [{"emoji":"🏠","label":"한도 1.2M"},{"emoji":"🏠","label":"한도 2M"},{"emoji":"🏠","label":"최대"}],
        ...
    ],
    output_path=Path("matrix.jpg"),
)
"""

import math
import random
import re
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


CARD_SIZE = (1080, 1920)
BG = (255, 251, 240)              # 따뜻한 크림
INK = (17, 17, 17)
HIGHLIGHT = (255, 235, 70)         # 형광 노랑
ACCENT_GREEN = (90, 178, 90)       # 머니 그린
ACCENT_RED = (220, 60, 60)
SUBTLE = (140, 140, 140)
BORDER_W = 5

PRETENDARD_DIR = Path("/usr/share/fonts/truetype/pretendard")
PRETENDARD_DIR_ALT = Path("/usr/share/fonts/opentype/pretendard")
TWEMOJI_CACHE = Path("/tmp/twemoji_cache")
TWEMOJI_BASE = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72"


def _pretendard(weight: str = "Bold") -> Optional[str]:
    for d in (PRETENDARD_DIR, PRETENDARD_DIR_ALT):
        p = d / f"Pretendard-{weight}.otf"
        if p.exists():
            return str(p)
    return None


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    path = _pretendard(weight)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _emoji_to_codepoint(emoji: str) -> str:
    """이모지 → Twemoji 파일명용 hex codepoint (variation selector U+FE0F 제거)."""
    parts = [f"{ord(c):x}" for c in emoji if ord(c) != 0xfe0f]
    return "-".join(parts)


def _get_emoji_image(emoji: str, size: int) -> Optional[Image.Image]:
    """이모지 → PNG → PIL Image. 캐시 사용. 실패 시 None."""
    if not emoji:
        return None
    TWEMOJI_CACHE.mkdir(parents=True, exist_ok=True)
    codepoint = _emoji_to_codepoint(emoji)
    cache_path = TWEMOJI_CACHE / f"{codepoint}.png"
    if not cache_path.exists():
        url = f"{TWEMOJI_BASE}/{codepoint}.png"
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                cache_path.write_bytes(resp.content)
            else:
                return None
        except Exception:
            return None
    try:
        img = Image.open(cache_path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        return img
    except Exception:
        return None


def _wobble_line(draw: ImageDraw.ImageDraw, p1: Tuple[int, int], p2: Tuple[int, int],
                 segments: int = 8, jitter: int = 3, width: int = BORDER_W, seed: int = 0):
    """직선을 미세하게 흔들어 손그림 느낌."""
    rng = random.Random(seed)
    x1, y1 = p1
    x2, y2 = p2
    pts = [(x1, y1)]
    for i in range(1, segments):
        t = i / segments
        x = x1 + (x2 - x1) * t + rng.randint(-jitter, jitter)
        y = y1 + (y2 - y1) * t + rng.randint(-jitter, jitter)
        pts.append((x, y))
    pts.append((x2, y2))
    for a, b in zip(pts[:-1], pts[1:]):
        draw.line([a, b], fill=INK, width=width)


def _draw_highlight_text(img: Image.Image, draw: ImageDraw.ImageDraw,
                         text: str, highlight: Optional[str],
                         x: int, y: int, font: ImageFont.FreeTypeFont,
                         pad_x: int = 8, pad_y: int = 6):
    """text 를 그리되 highlight 부분에 노란 형광 마커 박스를 뒤에 깔고 그 위에 텍스트."""
    # 측정용
    if highlight and highlight in text:
        # 분할
        idx = text.find(highlight)
        before = text[:idx]
        mid = highlight
        after = text[idx + len(highlight):]
    else:
        before, mid, after = text, "", ""

    cur_x = x
    # before
    if before:
        draw.text((cur_x, y), before, font=font, fill=INK)
        cur_x += int(draw.textlength(before, font=font))
    # highlight
    if mid:
        bbox = font.getbbox(mid)
        mid_w = bbox[2] - bbox[0]
        mid_h = bbox[3] - bbox[1]
        # 마커 박스 — 텍스트 윗부분만 살짝 살짝 노란 형광펜처럼
        marker = Image.new("RGBA", img.size, (0, 0, 0, 0))
        m_draw = ImageDraw.Draw(marker)
        m_draw.rounded_rectangle(
            [cur_x - pad_x, y + mid_h // 4,
             cur_x + mid_w + pad_x, y + mid_h + pad_y],
            radius=6, fill=(*HIGHLIGHT, 220),
        )
        img.alpha_composite(marker)
        draw = ImageDraw.Draw(img)
        draw.text((cur_x, y), mid, font=font, fill=INK)
        cur_x += mid_w
    # after
    if after:
        draw.text((cur_x, y), after, font=font, fill=INK)


def make_comparison_matrix(
    title: str,
    col_headers: List[str],
    row_headers: List[str],
    cells: List[List[Dict]],
    output_path: Path,
    highlight: Optional[str] = None,
    brand: str = "@daily_money_kr · 매일 절세·재테크 한 장 정리",
    accent_color: Tuple[int, int, int] = HIGHLIGHT,
):
    """비교 매트릭스 카드 1장 생성.

    cells: rows × cols 의 2D 리스트. 각 셀은 {"emoji": str, "label": str}.
    rows = len(row_headers), cols = len(col_headers) 와 일치해야 함.
    """
    n_rows = len(row_headers)
    n_cols = len(col_headers)
    assert len(cells) == n_rows, f"cells rows({len(cells)}) != row_headers({n_rows})"
    for r in cells:
        assert len(r) == n_cols, f"cells cols mismatch"

    # 알파 합성 위해 RGBA 로 시작
    img = Image.new("RGBA", CARD_SIZE, (*BG, 255))
    draw = ImageDraw.Draw(img)

    # === 제목 ===
    title_font = _font("Bold", 80)
    title_y = 130
    # title 너비 측정 + 가운데 정렬
    title_w = draw.textlength(title, font=title_font)
    title_x = (CARD_SIZE[0] - title_w) // 2
    _draw_highlight_text(img, draw, title, highlight, title_x, title_y, title_font)

    draw = ImageDraw.Draw(img)  # 합성 후 재바인딩

    # 부제 / 정렬용 라인
    subtitle_font = _font("Medium", 32)
    subtitle = "표 한 장으로 비교"
    sub_w = draw.textlength(subtitle, font=subtitle_font)
    draw.text(((CARD_SIZE[0] - sub_w) // 2, title_y + 110), subtitle,
              font=subtitle_font, fill=SUBTLE)

    # === 격자 영역 ===
    grid_top = 360
    grid_bottom = 1740
    grid_left = 70
    grid_right = CARD_SIZE[0] - 70
    grid_w = grid_right - grid_left
    grid_h = grid_bottom - grid_top

    # 첫 열은 행 라벨 → 약간 좁게
    label_col_w = 200
    cell_w = (grid_w - label_col_w) / n_cols

    # 첫 행은 열 헤더 → 약간 작게
    header_row_h = 120
    cell_h = (grid_h - header_row_h) / n_rows

    # === 격자 라인 (손그림 wobble) ===
    seed_base = hash(title) & 0xffff
    # 가로 라인
    for r in range(n_rows + 1):
        y = int(grid_top + header_row_h + r * cell_h) if r > 0 else int(grid_top + header_row_h)
        if r == 0:
            y = int(grid_top + header_row_h)
        _wobble_line(draw, (grid_left, y), (grid_right, y), seed=seed_base + r)
    # 격자 외곽 위/아래
    _wobble_line(draw, (grid_left, grid_top), (grid_right, grid_top), seed=seed_base + 100)
    _wobble_line(draw, (grid_left, grid_bottom), (grid_right, grid_bottom), seed=seed_base + 101)
    # 세로 라인
    for c in range(n_cols + 1):
        x = int(grid_left + label_col_w + c * cell_w) if c > 0 else int(grid_left + label_col_w)
        if c == 0:
            x = int(grid_left + label_col_w)
        _wobble_line(draw, (x, grid_top), (x, grid_bottom), seed=seed_base + 200 + c)
    # 외곽 좌/우
    _wobble_line(draw, (grid_left, grid_top), (grid_left, grid_bottom), seed=seed_base + 300)
    _wobble_line(draw, (grid_right, grid_top), (grid_right, grid_bottom), seed=seed_base + 301)

    # === 열 헤더 ===
    col_font = _font("Bold", 44)
    for c, hdr in enumerate(col_headers):
        x = grid_left + label_col_w + c * cell_w + cell_w / 2
        bbox = col_font.getbbox(hdr)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        # 헤더에 살짝 형광 박스
        marker = Image.new("RGBA", img.size, (0, 0, 0, 0))
        m_draw = ImageDraw.Draw(marker)
        m_draw.rounded_rectangle(
            [int(x - w/2 - 14), int(grid_top + header_row_h/2 - h/2 + 6),
             int(x + w/2 + 14), int(grid_top + header_row_h/2 + h/2 + 14)],
            radius=10, fill=(*accent_color, 200),
        )
        img.alpha_composite(marker)
        draw = ImageDraw.Draw(img)
        draw.text((x - w/2, grid_top + header_row_h/2 - h/2 - 8),
                  hdr, font=col_font, fill=INK)

    # === 행 헤더 ===
    row_font = _font("Bold", 42)
    for r, hdr in enumerate(row_headers):
        x_cx = grid_left + label_col_w / 2
        y_cy = grid_top + header_row_h + r * cell_h + cell_h / 2
        bbox = row_font.getbbox(hdr)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((x_cx - w/2, y_cy - h/2 - 6), hdr, font=row_font, fill=INK)

    # === 셀 내용 (이모지 + 라벨) ===
    cell_label_font = _font("Medium", 30)
    for r in range(n_rows):
        for c in range(n_cols):
            cell = cells[r][c]
            x_cx = grid_left + label_col_w + c * cell_w + cell_w / 2
            y_top = grid_top + header_row_h + r * cell_h
            y_bottom = y_top + cell_h
            cell_cy = (y_top + y_bottom) / 2

            emoji_size = int(cell_h * 0.45)
            emoji_img = _get_emoji_image(cell.get("emoji", ""), emoji_size) if cell.get("emoji") else None

            label = cell.get("label", "")
            # 라벨 줄바꿈 (셀 너비에 맞춤)
            max_label_w = int(cell_w - 30)
            label_lines = _wrap_label(label, cell_label_font, max_label_w)
            line_h = cell_label_font.size + 8
            label_block_h = line_h * len(label_lines)

            if emoji_img:
                em_x = int(x_cx - emoji_size / 2)
                em_y = int(y_top + cell_h * 0.10)
                img.alpha_composite(emoji_img, (em_x, em_y))
                label_y = em_y + emoji_size + 14
            else:
                label_y = int(cell_cy - label_block_h / 2)

            draw = ImageDraw.Draw(img)
            for line in label_lines:
                lw = draw.textlength(line, font=cell_label_font)
                draw.text((x_cx - lw / 2, label_y), line, font=cell_label_font, fill=INK)
                label_y += line_h

    # === 하단 브랜드 ===
    brand_font = _font("Medium", 28)
    bw = draw.textlength(brand, font=brand_font)
    draw.text(((CARD_SIZE[0] - bw) // 2, CARD_SIZE[1] - 80),
              brand, font=brand_font, fill=SUBTLE)

    # 출력
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path


def _wrap_label(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    """간단 단어 단위 wrap. 한글이면 글자 단위로 fallback."""
    if font.getbbox(text)[2] <= max_w:
        return [text]
    # 한글 어절은 공백 기준 wrap 시도
    words = re.split(r'(\s+)', text)
    lines, cur = [], ""
    for w in words:
        test = cur + w
        if font.getbbox(test)[2] <= max_w:
            cur = test
        else:
            if cur.strip():
                lines.append(cur.strip())
            cur = w
    if cur.strip():
        lines.append(cur.strip())
    # 그래도 한 줄 너무 길면 글자 단위 break
    final = []
    for line in lines:
        if font.getbbox(line)[2] <= max_w:
            final.append(line)
        else:
            buf = ""
            for ch in line:
                if font.getbbox(buf + ch)[2] > max_w and buf:
                    final.append(buf)
                    buf = ch
                else:
                    buf += ch
            if buf:
                final.append(buf)
    return final[:3]  # 셀당 최대 3줄


if __name__ == "__main__":
    sample = {
        "title": "월급별 추천 절세 상품",
        "highlight": "절세 상품",
        "col_headers": ["300만원", "500만원", "1억"],
        "row_headers": ["청약저축", "ISA", "연금저축"],
        "cells": [
            [
                {"emoji": "🏠", "label": "한도 300만 추천"},
                {"emoji": "🏠", "label": "한도 다 채우기"},
                {"emoji": "🏠", "label": "공제 우선순위"},
            ],
            [
                {"emoji": "💼", "label": "0순위 가입"},
                {"emoji": "💼", "label": "꾸준히 운용"},
                {"emoji": "💼", "label": "한도 200만"},
            ],
            [
                {"emoji": "📈", "label": "월 25만 권장"},
                {"emoji": "📈", "label": "월 50만"},
                {"emoji": "📈", "label": "최대 700만"},
            ],
        ],
    }
    out = Path(__file__).parent.parent / "output_money" / "sample_matrix" / "matrix_sample.jpg"
    print(f"🎨 매트릭스 카드 생성 → {out}")
    make_comparison_matrix(
        title=sample["title"],
        highlight=sample["highlight"],
        col_headers=sample["col_headers"],
        row_headers=sample["row_headers"],
        cells=sample["cells"],
        output_path=out,
    )
    print(f"✅ 완료 ({out.stat().st_size // 1024} KB)")
