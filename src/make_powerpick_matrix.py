"""
초능력 픽 매트릭스 — 9-셀 단일 픽 그리드 (가격/합산 X, 그냥 하나 고르기).

@babydol.dori 의 "단 하나의 초능력만 고를 수 있다면?" 포맷을 코드로 재현.
손그림 cute 톤 — 셀별 파스텔 + 큰 이모지 + 짧은 라벨. 9개 모두 동급.
"""

import os
import sys
import random
from pathlib import Path
from typing import List
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image, _wrap_label


CANVAS = (1080, 1920)
BG = (253, 251, 246)            # 따뜻한 아이보리 — 흰색보다 손그림 노트 느낌
INK = (40, 38, 42)
MUTED = (140, 138, 142)

# 9-셀 파스텔 팔레트 (@babydol.dori 와 다른 톤 — sage/coral/sand 추가)
PASTEL_CELLS = [
    {"fill": (255, 226, 226), "stroke": (210, 140, 140)},  # rose
    {"fill": (220, 238, 252), "stroke": (130, 170, 210)},  # sky
    {"fill": (255, 240, 200), "stroke": (210, 175, 90)},   # butter
    {"fill": (224, 246, 224), "stroke": (130, 185, 130)},  # mint
    {"fill": (245, 226, 250), "stroke": (180, 130, 200)},  # lilac
    {"fill": (255, 220, 200), "stroke": (220, 140, 100)},  # peach
    {"fill": (235, 245, 220), "stroke": (160, 185, 110)},  # sage
    {"fill": (215, 235, 255), "stroke": (110, 155, 210)},  # baby blue
    {"fill": (250, 230, 215), "stroke": (200, 150, 110)},  # sand
]

# 손그림 느낌 — 카드 모서리에 미세 wobble
WOBBLE_AMP = 4


def _wobbly_rounded_rect(draw, rect, radius, fill=None, outline=None, width=3, seed=0):
    """라운드 사각형에 미세 wobble 추가 — 손그림 느낌. seed 로 wobble 패턴 고정."""
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)
    if outline:
        # outline 만 wobble — 4변 위에 jitter 점을 따라 선
        rng = random.Random(seed)
        # 상하좌우 각각 jittered polyline
        def jitter_line(pts):
            out = []
            for (x, y) in pts:
                out.append((x + rng.randint(-WOBBLE_AMP, WOBBLE_AMP),
                            y + rng.randint(-WOBBLE_AMP, WOBBLE_AMP)))
            return out
        n = 14  # 변당 점 수
        def lerp(a, b, t): return a + (b - a) * t
        # 4 변
        top = jitter_line([(lerp(x0 + radius, x1 - radius, i / n), y0)
                            for i in range(n + 1)])
        bot = jitter_line([(lerp(x0 + radius, x1 - radius, i / n), y1)
                            for i in range(n + 1)])
        lef = jitter_line([(x0, lerp(y0 + radius, y1 - radius, i / n))
                            for i in range(n + 1)])
        rig = jitter_line([(x1, lerp(y0 + radius, y1 - radius, i / n))
                            for i in range(n + 1)])
        for line in (top, bot, lef, rig):
            draw.line(line, fill=outline, width=width, joint="curve")
        # 4 모서리 호 (대략)
        for cx, cy, ang_start in [(x0 + radius, y0 + radius, 180),
                                    (x1 - radius, y0 + radius, 270),
                                    (x1 - radius, y1 - radius, 0),
                                    (x0 + radius, y1 - radius, 90)]:
            draw.arc([cx - radius, cy - radius, cx + radius, cy + radius],
                     start=ang_start, end=ang_start + 90,
                     fill=outline, width=width)


def make_powerpick_matrix(
    title: str,
    rule_hint: str,
    picks: List[dict],            # 9개: each {emoji, label}
    output_path: Path,
    brand: str = "",
    source_note: str = "",
):
    """9-셀 단일 픽 그리드 — 가격/티어 없음, 9개 동급.

    picks: [{emoji: "🪑", label: "출근길 빈자리"}, ...] 정확히 9개
    title: 큰 제목 (2줄까지)
    rule_hint: 부제 ("(직장인편)" 등)
    """
    assert len(picks) == 9, "9개 정확히 필요"
    img = Image.new("RGB", CANVAS, BG).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 폰트
    bold_path = _resolve_font("Bold")
    semi_path = _resolve_font("SemiBold")
    medium_path = _resolve_font("Medium")
    f_title = ImageFont.truetype(bold_path, 82)
    f_sub = ImageFont.truetype(medium_path, 42)
    f_label = ImageFont.truetype(semi_path, 32)
    f_brand = ImageFont.truetype(medium_path, 28)
    f_src = ImageFont.truetype(medium_path, 24)

    # ─── 제목 (Reels safe area 220 y) ──
    # 너무 길면 2줄 wrap
    title_y = 220
    title_w = draw.textlength(title, font=f_title)
    if title_w <= CANVAS[0] - 80:
        draw.text(((CANVAS[0] - title_w) / 2, title_y), title,
                  font=f_title, fill=INK)
        sub_y = title_y + 110
    else:
        # 단순 중간 분할
        words = title.split()
        half = len(words) // 2
        line1 = " ".join(words[:half + 1])
        line2 = " ".join(words[half + 1:])
        for i, line in enumerate([line1, line2]):
            lw = draw.textlength(line, font=f_title)
            draw.text(((CANVAS[0] - lw) / 2, title_y + i * 100), line,
                      font=f_title, fill=INK)
        sub_y = title_y + 210

    # 부제 (직장인편 등) — 괄호 스타일
    sw = draw.textlength(rule_hint, font=f_sub)
    draw.text(((CANVAS[0] - sw) / 2, sub_y), rule_hint,
              font=f_sub, fill=MUTED)

    # ─── 3×3 그리드 ───
    grid_top = sub_y + 90
    grid_bottom = CANVAS[1] - 320     # 하단 출처/브랜드 자리 확보
    grid_left = 70
    grid_right = CANVAS[0] - 70
    cell_w = (grid_right - grid_left) / 3
    cell_h = (grid_bottom - grid_top) / 3
    pad = 18

    for i, pick in enumerate(picks):
        r, c = divmod(i, 3)
        x0 = int(grid_left + c * cell_w + pad)
        y0 = int(grid_top + r * cell_h + pad)
        x1 = int(grid_left + (c + 1) * cell_w - pad)
        y1 = int(grid_top + (r + 1) * cell_h - pad)
        style = PASTEL_CELLS[i % len(PASTEL_CELLS)]

        # 부드러운 그림자
        sh = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle([x0 + 2, y0 + 8, x1 + 2, y1 + 14],
                             radius=28, fill=(0, 0, 0, 28))
        sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
        img.alpha_composite(sh)
        draw = ImageDraw.Draw(img)

        # 카드 본체 (손그림 wobble outline)
        _wobbly_rounded_rect(draw, (x0, y0, x1, y1), radius=28,
                              fill=style["fill"], outline=style["stroke"],
                              width=4, seed=i + 7)

        # 이모지 (큰 사이즈, 셀 상단 중앙)
        cw, ch = x1 - x0, y1 - y0
        em_size = int(min(cw, ch) * 0.46)
        em_img = _get_emoji_image(pick.get("emoji", ""), em_size)
        cx = (x0 + x1) // 2
        em_top = y0 + int(ch * 0.16)
        if em_img:
            img.alpha_composite(em_img, (cx - em_size // 2, em_top))

        # 라벨 (2줄까지 wrap, 셀 하단). \n 가 라벨에 명시돼 있으면 그 분할 사용.
        label = pick.get("label", "")
        if "\n" in label:
            label_lines = label.split("\n")[:2]
        else:
            label_lines = _wrap_label(label, f_label, cw - 20)[:2]
        line_h = f_label.size + 4
        label_block_h = line_h * len(label_lines)
        label_y = y1 - 28 - label_block_h
        for line in label_lines:
            draw_now = ImageDraw.Draw(img)
            lw = draw_now.textlength(line, font=f_label)
            draw_now.text((cx - lw / 2, label_y), line,
                          font=f_label, fill=INK)
            label_y += line_h

    draw = ImageDraw.Draw(img)

    # ─── 하단 CTA + 출처 + 브랜드 ───
    cta = "💬 단 하나만! 댓글로 ⬇️"
    f_cta = ImageFont.truetype(bold_path, 40)
    cw = draw.textlength(cta, font=f_cta)
    cta_y = CANVAS[1] - 260
    draw.rounded_rectangle([int((CANVAS[0] - cw) / 2 - 24), cta_y - 6,
                            int((CANVAS[0] + cw) / 2 + 24), cta_y + 56],
                           radius=14, fill=(255, 234, 0))
    draw.text(((CANVAS[0] - cw) / 2, cta_y), cta, font=f_cta, fill=INK)

    if source_note:
        sw = draw.textlength(source_note, font=f_src)
        draw.text(((CANVAS[0] - sw) / 2, cta_y + 78),
                  source_note, font=f_src, fill=MUTED)

    if brand:
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 130),
                  brand, font=f_brand, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    out = Path("/tmp/powerpick_test.jpg")
    make_powerpick_matrix(
        title="단 하나의 초능력만 고를 수 있다면?",
        rule_hint="(직장인편)",
        picks=[
            {"emoji": "🪑", "label": "출근길 빈자리\n자동 발견"},
            {"emoji": "🍻", "label": "회식 자동 패스"},
            {"emoji": "💰", "label": "매달 50만원\n부수입"},
            {"emoji": "✨", "label": "1초 코디 완성"},
            {"emoji": "🍱", "label": "점심값 0원"},
            {"emoji": "🚪", "label": "6시 자동 퇴근"},
            {"emoji": "☕", "label": "무한 카페인"},
            {"emoji": "🔮", "label": "상사 마음\n1분 보기"},
            {"emoji": "⏸️", "label": "회의 10초\n시간정지"},
        ],
        output_path=out,
        brand="@daily_enter_kr",
    )
    print("✓", out)
