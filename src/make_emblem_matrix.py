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

# 티어별 (위→아래: 고가/중가/저가) 카드 색. 금액이 라벨 — 골드/실버/브론즈 어휘 제거.
# fill 은 은은한 컬러 (배경과 분리되되 화려하지 않게), text 는 대비.
TIER_STYLES = [
    {"fill_top": (255, 248, 225), "fill_bot": (255, 224, 138),
     "border": (214, 158, 30),    "glow": (255, 210, 80, 70),
     "text_color": (60, 40, 0)},
    {"fill_top": (240, 244, 250), "fill_bot": (206, 220, 236),
     "border": (120, 145, 180),   "glow": (150, 180, 220, 55),
     "text_color": (30, 40, 60)},
    {"fill_top": (245, 235, 228), "fill_bot": (224, 198, 170),
     "border": (170, 130, 95),    "glow": (190, 150, 110, 55),
     "text_color": (50, 35, 20)},
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
        # 흰 배경 (premium 룩 — 축구 외 토픽 기본)
        return Image.new("RGB", CANVAS, WHITE)


def _is_dark_bg(style: str) -> bool:
    """배경이 어두운지 — 제목/룰/브랜드 텍스트 색 결정용."""
    return style in ("soccer", "gradient_idol", "gradient_dark")


# 한국 만원권 모티프 색 (청록/민트 계열)
BILL_FILL = (118, 188, 175)      # 만원권 청록
BILL_FILL2 = (96, 168, 156)
BILL_BORDER = (60, 120, 110)
BILL_TEXT = (35, 80, 72)


def _draw_money_bill(img: Image.Image, draw: ImageDraw.ImageDraw,
                     cx: int, cy: int, w: int, h: int,
                     amount_text: str, font_paths: dict, angle: int = -8):
    """만원 지폐 일러스트 (단순화) — 청록 사각형 + 모서리 금액 + 중앙 원형 초상 자리.

    별도 레이어에 그려서 회전 후 합성 (지폐 살짝 기울임 → 생동감).
    """
    pad = 60
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ox, oy = pad, pad

    # 지폐 본체 (라운드 사각형 + 그라데이션 느낌 2색 보더)
    ld.rounded_rectangle([ox, oy, ox + w, oy + h], radius=18,
                         fill=BILL_FILL, outline=BILL_BORDER, width=4)
    # 내부 테두리 라인 (지폐 느낌)
    ld.rounded_rectangle([ox + 10, oy + 10, ox + w - 10, oy + h - 10],
                         radius=12, outline=BILL_FILL2, width=3)

    bold = font_paths.get("Bold")
    # 중앙 원형 (초상 자리 — 빈 원, 특정 인물 X)
    circle_r = int(h * 0.30)
    ccx = ox + int(w * 0.34)
    ccy = oy + h // 2
    ld.ellipse([ccx - circle_r, ccy - circle_r, ccx + circle_r, ccy + circle_r],
               outline=BILL_BORDER, width=3, fill=BILL_FILL2)
    # 원 안에 ₩ 마크
    won_font = ImageFont.truetype(bold, int(circle_r * 1.1))
    wb = won_font.getbbox("₩")
    ww = wb[2] - wb[0]; wh = wb[3] - wb[1]
    ld.text((ccx - ww/2, ccy - wh/2 - wb[1]), "₩", font=won_font, fill=BILL_TEXT)

    # 우측 금액 텍스트 (큰 글씨)
    amt_font = ImageFont.truetype(bold, int(h * 0.42))
    ab = amt_font.getbbox(amount_text)
    aw = ab[2] - ab[0]; ah = ab[3] - ab[1]
    ld.text((ox + int(w * 0.58), oy + h//2 - ah/2 - ab[1]),
            amount_text, font=amt_font, fill=BILL_TEXT)
    # 좌상단 / 우하단 작은 금액 (지폐 코너 숫자 느낌)
    sm_font = ImageFont.truetype(bold, int(h * 0.16))
    ld.text((ox + 22, oy + 16), amount_text, font=sm_font, fill=BILL_TEXT)

    # 회전 후 합성
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    lw, lh = layer.size
    img.alpha_composite(layer, (int(cx - lw / 2), int(cy - lh / 2)))


def _draw_emblem_card(img: Image.Image, rect: Tuple[int, int, int, int],
                      tier_style: dict, cell: dict,
                      font_paths: dict = None):
    """단일 엠블럼 카드를 img 위에 그림 (in-place).

    cell: {name, price, subtitle?, jersey?: {color, number}, role_emoji?}
    """
    x0, y0, x1, y1 = rect
    cw, ch = x1 - x0, y1 - y0

    # 1) 카드 내부 — 그라데이션 fill
    grad = _vertical_gradient((cw, ch), tier_style["fill_top"], tier_style["fill_bot"])

    # 2) 마스크 (라운드 모서리)
    mask = Image.new("L", (cw, ch), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, cw, ch], radius=24, fill=255)

    # 3) 외부 글로우 — 약하게 (깔끔한 룩)
    glow_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    gdraw.rounded_rectangle([x0 - 3, y0 + 5, x1 + 3, y1 + 9], radius=28,
                            fill=tier_style["glow"])
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=12))
    img.alpha_composite(glow_layer)

    # 4) 카드 합성
    img.paste(grad.convert("RGBA"), (x0, y0), mask)

    # 5) 보더 — 얇게 (깔끔한 룩)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24,
                           outline=tier_style["border"], width=3)

    bold = font_paths.get("Bold") if font_paths else _resolve_font("Bold")
    medium = font_paths.get("Medium") if font_paths else _resolve_font("Medium")
    name_color = tier_style["text_color"]
    cx = x0 + cw / 2

    # 6) 비주얼 — jersey (유니폼+등번호) 또는 역할 이모지
    visual_top = y0 + ch * 0.16
    jersey = cell.get("jersey")
    if jersey:
        # 유니폼 실루엣 + 등번호. 색만으로 팀 연상 (특정 X)
        _draw_jersey(img, draw, cx, visual_top, int(ch * 0.40),
                     jersey_color=jersey.get("color", (200, 30, 30)),
                     number=str(jersey.get("number", "")),
                     bold_path=bold)
    else:
        emoji_size = int(ch * 0.40)
        em_img = _get_emoji_image(cell.get("role_emoji", ""), emoji_size) if cell.get("role_emoji") else None
        if em_img:
            img.alpha_composite(em_img, (int(cx - emoji_size / 2), int(visual_top)))

    # 7) 실명 (Bold, 2줄 wrap 가능) — subtitle 있으면 자리 더 위로
    name = cell.get("name", "")
    name_font = ImageFont.truetype(bold, 44)
    max_name_w = cw - 26
    name_lines = _wrap_label(name, name_font, max_name_w)[:2]
    name_block_h = name_font.size * len(name_lines) + 4 * (len(name_lines) - 1)
    subtitle = cell.get("subtitle", "")
    name_bottom_margin = 96 if subtitle else 60
    name_y = y1 - name_bottom_margin - name_block_h
    for line in name_lines:
        bbox = name_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw / 2, name_y), line, font=name_font, fill=name_color)
        name_y += name_font.size + 4

    # 8) 서브타이틀 (그룹/소속/팀) — 멤버명 아래, 약간 흐리게 시각 위계 명확화
    if subtitle:
        sub_font = ImageFont.truetype(medium, 28)
        # name_color 에 흰색 30% 섞어 위계 약화
        sub_color = tuple(int(c * 0.55 + 255 * 0.45) for c in name_color[:3])
        bbox = sub_font.getbbox(subtitle)
        sw = bbox[2] - bbox[0]
        draw.text((cx - sw / 2, y1 - 50), subtitle, font=sub_font, fill=sub_color)

    # 9) 금액 칩 (좌상단) — 골드/실버/브론즈 대신 실제 금액
    price_label = cell.get("price", "")
    if price_label:
        pf = ImageFont.truetype(bold, 22)
        pb = pf.getbbox(price_label)
        pw = pb[2] - pb[0]
        ph = pb[3] - pb[1]
        pad_x, pad_y = 11, 5
        chip_x0 = x0 + 14
        chip_y0 = y0 + 14
        chip_x1 = chip_x0 + pw + pad_x * 2
        chip_y1 = chip_y0 + ph + pad_y * 2 + 4
        draw.rounded_rectangle([chip_x0, chip_y0, chip_x1, chip_y1],
                               radius=10, fill=tier_style["border"])
        draw.text((chip_x0 + pad_x, chip_y0 + pad_y),
                  price_label, font=pf, fill=(255, 255, 255))


def _draw_jersey(img, draw, cx, top_y, size, jersey_color, number, bold_path):
    """간단한 축구 유니폼 실루엣 + 등번호. 색만으로 표현해 특정 팀 비특정."""
    w = int(size * 0.95)
    h = int(size * 1.0)
    left = int(cx - w / 2)
    top = int(top_y)
    # 몸통 (사다리꼴 느낌 — 둥근 사각형으로 단순화)
    body_top = top + int(h * 0.22)
    draw.rounded_rectangle([left + int(w*0.12), body_top, left + int(w*0.88), top + h],
                           radius=int(w*0.10), fill=jersey_color)
    # 어깨/소매 (좌우 작은 사각형)
    sleeve_w = int(w * 0.20)
    draw.polygon([(left, body_top + int(h*0.06)),
                  (left + int(w*0.22), top + int(h*0.16)),
                  (left + int(w*0.22), body_top + int(h*0.30)),
                  (left, body_top + int(h*0.34))], fill=jersey_color)
    draw.polygon([(left + w, body_top + int(h*0.06)),
                  (left + w - int(w*0.22), top + int(h*0.16)),
                  (left + w - int(w*0.22), body_top + int(h*0.30)),
                  (left + w, body_top + int(h*0.34))], fill=jersey_color)
    # 목 (V넥 — 배경색 삼각형)
    neck_w = int(w * 0.18)
    draw.polygon([(int(cx - neck_w/2), body_top),
                  (int(cx + neck_w/2), body_top),
                  (int(cx), body_top + int(h*0.16))], fill=(255, 255, 255))
    # 등번호 (흰색, 가운데)
    num_font = ImageFont.truetype(bold_path, int(h * 0.42))
    nb = num_font.getbbox(number)
    nw = nb[2] - nb[0]
    nh = nb[3] - nb[1]
    draw.text((cx - nw/2, body_top + int(h*0.28) - nh/2), number,
              font=num_font, fill=(255, 255, 255))


def make_emblem_matrix(
    title: str,
    highlight: str,
    rule_hint: str,
    col_headers: List[str],
    row_prices: List[str],
    cells: List[List[dict]],
    output_path: Path,
    brand: str = "",
    background_style: str = "soccer",   # "soccer" / "gradient_idol" / "gradient_dark" / "white"
    budget_label: str = "만원",         # 상단 지폐 일러스트에 표시할 금액
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

    # 배경 명암에 따른 텍스트 색
    dark_bg = _is_dark_bg(background_style)
    title_color = WHITE if dark_bg else INK
    hint_color = (230, 230, 230) if dark_bg else MUTED
    header_color = WHITE if dark_bg else INK
    brand_color = (220, 220, 220) if dark_bg else MUTED

    # ─── 1) 만원 지폐 일러스트 (제목 위) ───
    # "만원" 텍스트 형광 대신 실제 지폐 그림으로 시각화. 금액은 budget_label 로 전달.
    bill_amount = budget_label or "만원"
    bill_w, bill_h = 300, 150
    bill_cx = CANVAS[0] // 2
    bill_cy = 180
    _draw_money_bill(img, draw, bill_cx, bill_cy, bill_w, bill_h,
                     amount_text=bill_amount, font_paths=font_paths, angle=-8)
    draw = ImageDraw.Draw(img)

    # ─── 1b) 제목 (형광 없이, 지폐 아래) ───
    title_y = 290
    title_w = draw.textlength(title, font=f_title)
    title_x = (CANVAS[0] - title_w) / 2
    draw.text((title_x, title_y), title, font=f_title, fill=title_color)

    # ─── 2) 룰 힌트 ───
    hint_y = title_y + 120
    hint_w = draw.textlength(rule_hint, font=f_hint)
    draw.text(((CANVAS[0] - hint_w) / 2, hint_y), rule_hint,
              font=f_hint, fill=hint_color)

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
                  hdr, font=f_col, fill=header_color)

    # ─── 5) 셀 카드 ───
    card_pad = 12
    for r in range(n_rows):
        tier = TIER_STYLES[r]
        for c in range(n_cols):
            x0 = int(grid_left + c * cell_w + card_pad)
            y0 = int(grid_top + header_h + r * cell_h + card_pad)
            x1 = int(grid_left + (c + 1) * cell_w - card_pad)
            y1 = int(grid_top + header_h + (r + 1) * cell_h - card_pad)

            cell = dict(cells[r][c])
            # 금액 칩 — 행별 가격을 cell 에 주입 (개별 셀이 price 지정 안 하면 row_prices 사용)
            cell.setdefault("price", row_prices[r])
            _draw_emblem_card(
                img, (x0, y0, x1, y1), tier, cell,
                font_paths=font_paths,
            )

    # ─── 6) 공유 유도 CTA + 브랜드 (하단 푸터) ───
    # 강조 라인 — 노란 형광 박스로 "친구와 비교" 유도
    cta_text = "내 조합 vs 친구 조합, 누가 이길까?"
    f_cta = ImageFont.truetype(bold_path, 40)
    cta_w = draw.textlength(cta_text, font=f_cta)
    cta_x = (CANVAS[0] - cta_w) / 2
    cta_y = CANVAS[1] - 300
    draw.rounded_rectangle([int(cta_x - 22), int(cta_y - 6),
                            int(cta_x + cta_w + 22), int(cta_y + 54)],
                           radius=12, fill=HIGHLIGHT_YELLOW)
    draw.text((cta_x, cta_y), cta_text, font=f_cta, fill=INK)

    # 브랜드 — 폭 넘치면 자동 축소
    if brand:
        bsize = 30
        while bsize > 20:
            f_b = ImageFont.truetype(medium_path, bsize)
            if draw.textlength(brand, font=f_b) <= CANVAS[0] - 80:
                break
            bsize -= 2
        bw = draw.textlength(brand, font=f_b)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 210),
                  brand, font=f_b, fill=brand_color)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92)
    return output_path
