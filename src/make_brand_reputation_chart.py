"""
브랜드평판지수 TOP30 차트 — 한국기업평판연구소 발표 기준의 월간 차트 카드.

[디자인 의도]
공신력 있는 외부 데이터(한국기업평판연구소)를 시드로 사용해서 "팬덤 분쟁" 회피.
순위는 우리가 매기는 게 아니라 "출처: 한국기업평판연구소" — 게시글은 차트 시각화일 뿐.
이 구조면 "왜 우리 최애가 N위?" 같은 시비가 공식 발표에 흡수됨.

[규격]
- 1080x1920 (9:16) — Reels/static post 호환
- 어두운 그라데이션(네이비 → 마젠타) — 차트/공신력 톤
- 헤더: ⭐ 기간 ⭐ + 큰 제목 + TOP30
- 본문: 2열 × 15행 (1-15 좌, 16-30 우). 행마다 [순위 | 이름]
- highlight_keyword 포함된 행은 👑 + 핑크 배경 강조 (예: "리센느")
- 하단: 핑크 callout 박스 + 출처 + 날짜

[데이터]
data/brand_reputation_*.json 에서 읽음. 월간 user manual 갱신.
구조: {title, period, source, source_date, highlight_keyword, callout, rankings:[{rank,name}, ...]}
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_comparison_matrix import _get_emoji_image


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)

PRETENDARD_DIR = Path("/usr/share/fonts/truetype/pretendard")
PRETENDARD_DIR_ALT = Path("/usr/share/fonts/opentype/pretendard")

C_HEADER_TOP = (24, 26, 72)
C_HEADER_BOT = (102, 28, 96)
C_BG_TOP = (28, 22, 68)
C_BG_BOT = (60, 24, 88)
C_GOLD = (255, 220, 120)
C_PINK = (255, 102, 184)
C_PINK_DEEP = (220, 60, 150)
C_CALLOUT_TOP = (255, 90, 170)
C_CALLOUT_BOT = (240, 60, 130)
C_ROW_BG = (255, 255, 255)
C_ROW_BG_ALT = (244, 244, 248)
C_HIGHLIGHT_BG = (255, 220, 232)
C_RANK_TEXT = (40, 36, 70)
C_NAME_TEXT = (24, 24, 32)


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


def _vgrad(size: Tuple[int, int], top: Tuple[int, int, int],
           bot: Tuple[int, int, int]) -> Image.Image:
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


def _draw_centered(draw: ImageDraw.ImageDraw, text: str,
                   font: ImageFont.FreeTypeFont, cx: int, y: int,
                   fill: Tuple[int, int, int] = WHITE,
                   stroke_width: int = 0,
                   stroke_fill: Optional[Tuple[int, int, int]] = None) -> int:
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kwargs = dict(font=font, fill=fill)
    if stroke_width:
        kwargs["stroke_width"] = stroke_width
        kwargs["stroke_fill"] = stroke_fill or INK
    draw.text((cx - w / 2, y), text, **kwargs)
    return bb[3] - bb[1]


def make_brand_reputation_chart(
    data_path: Path,
    output_path: Path,
    brand: str = "@daily_enter_kr · 매일 K-연예 인사이트",
):
    """JSON 데이터 → 1080x1920 차트 jpg. 출력 path 반환."""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "브랜드평판")
    period = data.get("period", "")
    source = data.get("source", "한국기업평판연구소")
    source_date = data.get("source_date", "")
    hkw = data.get("highlight_keyword", "")
    callout = data.get("callout", "")
    rankings = data.get("rankings", [])

    if len(rankings) < 30:
        raise ValueError(f"rankings 30개 필요 — 현재 {len(rankings)}개")

    img = _vgrad(CANVAS, C_BG_TOP, C_BG_BOT)
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # ─── 헤더 영역 (0–460) — 그라데이션 박스 ───
    hdr_h = 460
    hdr = _vgrad((CANVAS[0], hdr_h), C_HEADER_TOP, C_HEADER_BOT).convert("RGBA")
    img.paste(hdr, (0, 0))
    draw = ImageDraw.Draw(img)

    f_period = _font("Bold", 56)
    f_title = _font("Bold", 78)
    f_top = _font("Bold", 200)

    # 기간 + 별 장식
    star = " ✦ "
    period_text = f"{star}{period}{star}"
    _draw_centered(draw, period_text, f_period, CANVAS[0] // 2, 36, fill=C_GOLD)

    # 메인 제목
    _draw_centered(draw, title, f_title, CANVAS[0] // 2, 120, fill=WHITE,
                   stroke_width=3, stroke_fill=(80, 30, 90))

    # TOP30 거대 텍스트
    _draw_centered(draw, "TOP30", f_top, CANVAS[0] // 2, 220, fill=WHITE,
                   stroke_width=6, stroke_fill=(160, 40, 120))

    # ─── 본문 ranking 그리드 (490–1620) ───
    grid_top = 480
    grid_bottom = 1640
    row_h = (grid_bottom - grid_top) / 15  # 15개 행
    col_gap = 24
    col_w = (CANVAS[0] - 60 - col_gap) / 2  # 좌우 30px 마진
    col_x = [30, 30 + col_w + col_gap]

    f_rank = _font("Bold", 36)
    f_name = _font("SemiBold", 36)
    f_crown_name = _font("Bold", 36)

    for idx, entry in enumerate(rankings[:30]):
        rank = entry.get("rank", idx + 1)
        name = entry.get("name", "")
        col = 0 if idx < 15 else 1
        row = idx if idx < 15 else idx - 15
        x = col_x[col]
        y = grid_top + row * row_h

        highlighted = bool(hkw) and hkw in name
        if highlighted:
            bg = C_HIGHLIGHT_BG
            stroke = C_PINK_DEEP
        else:
            bg = C_ROW_BG if (row % 2 == 0) else C_ROW_BG_ALT
            stroke = None

        # 행 박스 (둥근 사각형)
        box = (int(x), int(y + 4), int(x + col_w), int(y + row_h - 4))
        draw.rounded_rectangle(box, radius=14, fill=bg,
                               outline=stroke, width=3 if stroke else 0)

        # 순위 텍스트 (왼쪽)
        rank_str = f"{rank}위"
        rank_x = x + 22
        rank_y = y + row_h / 2 - f_rank.size / 2 - 4
        draw.text((rank_x, rank_y), rank_str, font=f_rank, fill=C_RANK_TEXT)

        # 이름 텍스트 (rank 옆 시작점)
        name_x = x + 130
        name_font = f_crown_name if highlighted else f_name
        name_fill = C_PINK_DEEP if highlighted else C_NAME_TEXT

        # 👑 이모지 (highlighted)
        if highlighted:
            em = _get_emoji_image("👑", 44)
            if em:
                img.alpha_composite(em, (int(name_x), int(y + row_h / 2 - 22)))
                draw = ImageDraw.Draw(img)
                name_x += 56

        draw.text((name_x, rank_y), name, font=name_font, fill=name_fill)

    # ─── 하단 callout 박스 (1660–1820) ───
    if callout:
        co_top = 1660
        co_h = 130
        co_box = _vgrad((CANVAS[0] - 60, co_h),
                        C_CALLOUT_TOP, C_CALLOUT_BOT).convert("RGBA")
        # 둥근 마스크
        mask = Image.new("L", co_box.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, co_box.size[0], co_box.size[1]], radius=28, fill=255)
        img.paste(co_box, (30, co_top), mask)
        draw = ImageDraw.Draw(img)

        f_callout = _font("Bold", 56)
        _draw_centered(draw, callout, f_callout, CANVAS[0] // 2,
                       co_top + (co_h - f_callout.size) // 2 - 6,
                       fill=WHITE, stroke_width=2, stroke_fill=(140, 30, 100))

    # ─── 출처 + 브랜드 (1820–1920) ───
    f_meta = _font("Medium", 26)
    src_line = f"출처: {source}  ·  {source_date}"
    _draw_centered(draw, src_line, f_meta, CANVAS[0] // 2, 1825,
                   fill=(220, 210, 240))
    _draw_centered(draw, brand, f_meta, CANVAS[0] // 2, 1870,
                   fill=(200, 190, 220))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    data = root / "data" / "brand_reputation_girlgroup.json"
    out = root / "output_enter" / "publish" / "brand_rep_girlgroup.jpg"
    make_brand_reputation_chart(data, out)
    print(f"✓ {out} ({out.stat().st_size // 1024} KB)")
