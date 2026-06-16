"""
축구 영입 매트릭스 — 5컬럼 × 3로우 + 결정적 캐릭터 헤드 + 4-2-1-3 포메이션.

참고 작가 스타일(귀여운 일러스트)을 PIL 로 절차적 재현:
- 1080x1920 9:16
- 상단: 제목(노란 하이라이트) + 부제
- 이적 설명 박스: 미니 축구장 + 4-2-1-3 도식 + 룰 설명
- 5×3 그리드: 가격 컬럼(1000~5000억) × 포지션 행(ST/CDM/GK)
- 각 셀: 절차적 캐릭터 헤드(name hash → 결정적 변형) + 이름
- 하단: 노란 CTA + 출처

캐릭터는 작가의 자산이 아닌 절차적 — 같은 구도/톤이지만 동일 캐릭터는 X.
"""

import hashlib
import math
import os
import sys
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font


CANVAS = (1080, 1920)
BG = (252, 248, 240)
INK = (32, 28, 36)
MUTED = (130, 130, 140)
HIGHLIGHT_YELLOW = (255, 222, 0)
CTA_YELLOW = (255, 232, 50)

# 가격 티어 컬러 (1000~5000억 — 청록 → 파랑 → 보라 → 분홍 → 빨강)
PRICE_TIER_COLORS = [
    (96, 188, 162),    # 1000억 — 청록
    (88, 156, 220),    # 2000억 — 하늘
    (140, 124, 220),   # 3000억 — 보라
    (230, 130, 170),   # 4000억 — 분홍
    (230, 100, 90),    # 5000억 — 빨강
]

# 스킨톤 3종
SKIN_TONES = [
    (250, 215, 188),
    (235, 195, 158),
    (210, 168, 128),
]

# 헤어 컬러 4종 (검정/다크 브라운/라이트 브라운/회색=레전드)
HAIR_COLORS = [
    (30, 24, 22),
    (62, 40, 30),
    (110, 78, 52),
    (190, 180, 175),
]

# 포지션 이모지/라벨
POSITION_ICONS = {
    "스트라이커": "⚔",
    "미드필더": "🎯",
    "골키퍼": "🧤",
}


def _draw_player_head(img: Image.Image, cx: int, cy: int, size: int,
                      name: str, is_legend: bool = False):
    """원형 캐릭터 헤드 — name hash 기반 결정적 변형."""
    draw = ImageDraw.Draw(img)
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    skin = SKIN_TONES[h % 3]
    hair_idx = (h >> 4) % 5
    if is_legend:
        hair_color = HAIR_COLORS[3]  # 회색
    else:
        hair_color = HAIR_COLORS[(h >> 8) % 3]
    expr_idx = (h >> 12) % 4

    r = size // 2
    # 얼굴 원
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=skin, outline=INK, width=3)

    # 헤어 5종 — 머리 위로 덮음
    if hair_idx == 0:
        # 슬릭백
        draw.pieslice([cx - r, cy - r - 6, cx + r, cy + 4],
                      start=180, end=360, fill=hair_color, outline=INK, width=3)
    elif hair_idx == 1:
        # 짧은 평탄
        draw.pieslice([cx - r - 2, cy - r - 8, cx + r + 2, cy - 2],
                      start=180, end=360, fill=hair_color, outline=INK, width=3)
    elif hair_idx == 2:
        # 곱슬 (둥근 봉우리 3개)
        draw.pieslice([cx - r, cy - r - 4, cx + r, cy + 8],
                      start=180, end=360, fill=hair_color, outline=INK, width=3)
        for off in (-r // 2, 0, r // 2):
            draw.ellipse([cx + off - 12, cy - r - 14, cx + off + 12, cy - r + 10],
                         fill=hair_color, outline=INK, width=2)
    elif hair_idx == 3:
        # 옆가르마
        draw.pieslice([cx - r, cy - r - 6, cx + r, cy + 4],
                      start=180, end=360, fill=hair_color, outline=INK, width=3)
        # 앞머리 라인
        draw.line([(cx - r // 2, cy - r // 2 + 4), (cx + r // 2, cy - r + 6)],
                  fill=INK, width=2)
    else:
        # 살짝 긴 (옆으로 흘러내림)
        draw.pieslice([cx - r - 2, cy - r - 4, cx + r + 2, cy + 6],
                      start=180, end=360, fill=hair_color, outline=INK, width=3)
        # 옆 머리카락
        draw.ellipse([cx - r - 4, cy - 6, cx - r + 8, cy + r // 2],
                     fill=hair_color)
        draw.ellipse([cx + r - 8, cy - 6, cx + r + 4, cy + r // 2],
                     fill=hair_color)

    # 눈 — 표정에 따라
    eye_y = cy - 2
    eye_dx = int(r * 0.32)
    eye_w = 5
    if expr_idx == 1 or expr_idx == 3:
        # 윙크 또는 그린 — 눈 가늘게
        draw.line([(cx - eye_dx - 5, eye_y), (cx - eye_dx + 5, eye_y)],
                  fill=INK, width=3)
        draw.line([(cx + eye_dx - 5, eye_y), (cx + eye_dx + 5, eye_y)],
                  fill=INK, width=3)
    else:
        draw.ellipse([cx - eye_dx - eye_w, eye_y - eye_w,
                      cx - eye_dx + eye_w, eye_y + eye_w], fill=INK)
        draw.ellipse([cx + eye_dx - eye_w, eye_y - eye_w,
                      cx + eye_dx + eye_w, eye_y + eye_w], fill=INK)

    # 입 — 표정 4종
    if expr_idx == 0:  # smile (반원)
        draw.arc([cx - 10, cy + 8, cx + 10, cy + 22],
                 start=0, end=180, fill=INK, width=3)
    elif expr_idx == 1:  # serious (수평선)
        draw.line([(cx - 8, cy + 16), (cx + 8, cy + 16)], fill=INK, width=3)
    elif expr_idx == 2:  # confident (큰 웃음)
        draw.chord([cx - 12, cy + 6, cx + 12, cy + 24],
                   start=0, end=180, fill=(220, 90, 90), outline=INK, width=2)
    else:  # grin
        draw.arc([cx - 13, cy + 4, cx + 13, cy + 24],
                 start=0, end=180, fill=INK, width=4)

    # 레전드 — 회색 콧수염 추가
    if is_legend:
        draw.ellipse([cx - 10, cy + 4, cx + 10, cy + 12],
                     fill=hair_color, outline=INK, width=1)

    # 볼터치 살짝
    draw.ellipse([cx - r + 6, cy + 4, cx - r + 18, cy + 16],
                 fill=(250, 180, 175, 0))


def _draw_formation_diagram(img: Image.Image, x0: int, y0: int, w: int, h: int):
    """4-2-1-3 미니 축구장 + 점들."""
    draw = ImageDraw.Draw(img)
    # 잔디 그라데이션
    grass_top = (74, 142, 60)
    grass_bot = (54, 108, 44)
    for i in range(h):
        t = i / max(h - 1, 1)
        c = tuple(int(grass_top[k] * (1 - t) + grass_bot[k] * t) for k in range(3))
        draw.line([(x0, y0 + i), (x0 + w, y0 + i)], fill=c)
    # 외곽선
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8,
                            outline=(255, 255, 255), width=2)
    # 중앙선
    cy = y0 + h // 2
    draw.line([(x0, cy), (x0 + w, cy)], fill=(255, 255, 255), width=2)
    # 센터 서클
    cr = 14
    cx = x0 + w // 2
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr],
                 outline=(255, 255, 255), width=2)
    # 골 박스 (상하)
    bw = int(w * 0.42)
    bh = 14
    draw.rectangle([cx - bw // 2, y0, cx + bw // 2, y0 + bh],
                   outline=(255, 255, 255), width=2)
    draw.rectangle([cx - bw // 2, y0 + h - bh, cx + bw // 2, y0 + h],
                   outline=(255, 255, 255), width=2)

    # 4-2-1-3 점 배치 (우리팀 = 아래 절반에 GK + DEF, 위로 갈수록 공격)
    # 좌표: 아래에서 위로
    y_gk = y0 + h - 12
    y_def = y0 + int(h * 0.78)
    y_cdm = y0 + int(h * 0.58)
    y_cam = y0 + int(h * 0.42)
    y_fwd = y0 + int(h * 0.20)
    dot_r = 6
    red = (224, 70, 60)

    def dot(px, py):
        draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                     fill=red, outline=(255, 255, 255), width=2)

    # GK 1명
    dot(cx, y_gk)
    # DEF 4명
    for i in range(4):
        px = x0 + int(w * (0.18 + i * 0.21))
        dot(px, y_def)
    # CDM 2명
    for i in range(2):
        px = x0 + int(w * (0.34 + i * 0.32))
        dot(px, y_cdm)
    # CAM 1명
    dot(cx, y_cam)
    # FWD 3명
    for i in range(3):
        px = x0 + int(w * (0.24 + i * 0.26))
        dot(px, y_fwd)


def make_soccer_squad_matrix(
    title: str,
    highlight: str,         # 노란 하이라이트 단어
    rule_hint: str,
    col_headers: List[str], # 5 가격 컬럼
    row_headers: List[str], # 3 포지션 (스트라이커/미드필더/골키퍼)
    cells: List[List[dict]],# cells[row][col] — {name, is_legend?}
    output_path: Path,
    brand: str = "",
    precondition_lines: Optional[List[str]] = None,
    source_note: str = "",
    cta_text: str = "💬 당신의 영입 조합은? 댓글로 ⬇️",
):
    assert len(col_headers) == 5 and len(row_headers) == 3, "5×3 전용"
    assert len(cells) == 3 and all(len(r) == 5 for r in cells)

    img = Image.new("RGB", CANVAS, BG).convert("RGBA")
    draw = ImageDraw.Draw(img)

    bold = _resolve_font("Bold")
    semi = _resolve_font("SemiBold")
    medium = _resolve_font("Medium")

    f_title = ImageFont.truetype(bold, 78)
    f_sub = ImageFont.truetype(medium, 38)
    f_cond_label = ImageFont.truetype(bold, 30)
    f_cond = ImageFont.truetype(medium, 28)
    f_col = ImageFont.truetype(bold, 28)
    f_row = ImageFont.truetype(bold, 32)
    f_name = ImageFont.truetype(semi, 22)
    f_cta = ImageFont.truetype(bold, 34)
    f_src = ImageFont.truetype(medium, 22)
    f_brand = ImageFont.truetype(medium, 26)

    # ─── 1) 제목 (highlight 단어 노란 형광) ───
    title_y = 100
    title_w = draw.textlength(title, font=f_title)
    title_x = (CANVAS[0] - title_w) / 2
    if highlight and highlight in title:
        before = title.split(highlight, 1)[0]
        bw = draw.textlength(before, font=f_title)
        hw = draw.textlength(highlight, font=f_title)
        # 형광 박스
        draw.rounded_rectangle([int(title_x + bw - 8), title_y + 14,
                                 int(title_x + bw + hw + 8), title_y + 92],
                                radius=8, fill=HIGHLIGHT_YELLOW)
    draw.text((title_x, title_y), title, font=f_title, fill=INK)

    # 부제
    sub_y = title_y + 108
    sw = draw.textlength(rule_hint, font=f_sub)
    draw.text(((CANVAS[0] - sw) / 2, sub_y), rule_hint, font=f_sub, fill=MUTED)

    # ─── 2) 이적 설명 박스 — 미니 포메이션 + 텍스트 ───
    box_y0 = sub_y + 60
    box_h = 250
    box_y1 = box_y0 + box_h
    draw.rounded_rectangle([60, box_y0, CANVAS[0] - 60, box_y1],
                            radius=18, fill=(252, 246, 222),
                            outline=(225, 200, 100), width=3)
    # 노란 라벨
    label = "이적 설명"
    lb = f_cond_label.getbbox(label)
    lbw = lb[2] - lb[0]
    draw.rounded_rectangle([78, box_y0 + 16, 78 + lbw + 22, box_y0 + 60],
                            radius=10, fill=(248, 200, 50))
    draw.text((78 + 11, box_y0 + 20), label, font=f_cond_label, fill=INK)

    # 텍스트 (왼쪽)
    cond_lines = precondition_lines or [
        "현재 팀: 대한민국 (4-2-1-3)",
        "구성: 스트라이커·미드필더·골키퍼",
        "→ 각 1명씩 영입 (총 1조)",
    ]
    cy_t = box_y0 + 80
    for line in cond_lines:
        draw.text((90, cy_t), line, font=f_cond, fill=INK)
        cy_t += 40

    # 포메이션 다이어그램 (우측)
    fd_w, fd_h = 230, 200
    fd_x = CANVAS[0] - 60 - fd_w - 16
    fd_y = box_y0 + 24
    _draw_formation_diagram(img, fd_x, fd_y, fd_w, fd_h)
    draw = ImageDraw.Draw(img)

    # ─── 3) 5×3 그리드 ───
    grid_top = box_y1 + 50
    grid_bottom = CANVAS[1] - 270
    grid_left = 110     # 좌측 포지션 라벨 자리
    grid_right = CANVAS[0] - 30
    header_h = 60
    row_label_w = 90

    cell_area_left = grid_left
    cell_area_right = grid_right
    cell_w = (cell_area_right - cell_area_left) / 5
    cell_h = (grid_bottom - grid_top - header_h) / 3

    # 컬럼 헤더 (가격 티어) — 라운드 칩
    for c, hdr in enumerate(col_headers):
        cx = cell_area_left + c * cell_w + cell_w / 2
        chip_w = cell_w - 12
        chip_color = PRICE_TIER_COLORS[c]
        draw.rounded_rectangle([int(cx - chip_w / 2), grid_top + 8,
                                 int(cx + chip_w / 2), grid_top + header_h - 4],
                                radius=14, fill=chip_color)
        bb = f_col.getbbox(hdr)
        hw = bb[2] - bb[0]
        draw.text((cx - hw / 2, grid_top + 16), hdr, font=f_col, fill=(255, 255, 255))

    # 로우 라벨 (포지션) + 셀
    for r, pos in enumerate(row_headers):
        row_y_top = grid_top + header_h + r * cell_h
        row_y_bot = row_y_top + cell_h
        row_cy = (row_y_top + row_y_bot) / 2

        # 로우 구분선
        draw.line([(cell_area_left - 30, int(row_y_bot)),
                   (cell_area_right, int(row_y_bot))],
                  fill=(220, 215, 205), width=1)

        # 포지션 라벨 (좌측)
        icon = POSITION_ICONS.get(pos, "")
        label_x = 30
        # 작은 배지
        draw.rounded_rectangle([label_x, int(row_cy - 36), label_x + 70, int(row_cy + 36)],
                                radius=14, fill=(40, 50, 80))
        if icon:
            f_icon = ImageFont.truetype(bold, 28)
            ib = f_icon.getbbox(icon)
            iw = ib[2] - ib[0]
            draw.text((label_x + 35 - iw / 2, int(row_cy - 26)), icon,
                      font=f_icon, fill=(255, 255, 255))
        # 포지션 약어 (CDM/ST/GK)
        abbr = {"스트라이커": "ST", "미드필더": "CDM", "골키퍼": "GK"}.get(pos, pos[:3])
        ab = f_name.getbbox(abbr)
        aw = ab[2] - ab[0]
        draw.text((label_x + 35 - aw / 2, int(row_cy + 4)), abbr,
                  font=f_name, fill=(255, 255, 255))

        # 셀
        for c in range(5):
            cell_cx = int(cell_area_left + c * cell_w + cell_w / 2)
            cell_cy = int(row_cy)

            # 캐릭터 헤드
            head_size = int(min(cell_w, cell_h) * 0.55)
            head_cy = cell_cy - 12
            cell = cells[r][c]
            name = cell.get("name", "")
            is_legend = cell.get("is_legend", False)
            _draw_player_head(img, cell_cx, head_cy, head_size, name,
                              is_legend=is_legend)
            draw = ImageDraw.Draw(img)

            # 이름
            nb = f_name.getbbox(name)
            nw = nb[2] - nb[0]
            name_y = head_cy + head_size // 2 + 8
            draw.text((cell_cx - nw / 2, name_y), name,
                      font=f_name, fill=INK)

    # ─── 4) 하단 CTA ───
    cta_y = CANVAS[1] - 200
    cw = draw.textlength(cta_text, font=f_cta)
    draw.rounded_rectangle([int((CANVAS[0] - cw) / 2 - 24), cta_y - 10,
                             int((CANVAS[0] + cw) / 2 + 24), cta_y + 52],
                            radius=14, fill=CTA_YELLOW,
                            outline=(220, 180, 30), width=2)
    draw.text(((CANVAS[0] - cw) / 2, cta_y), cta_text, font=f_cta, fill=INK)

    # 출처
    if source_note:
        sw = draw.textlength(source_note, font=f_src)
        draw.text(((CANVAS[0] - sw) / 2, cta_y + 76),
                  source_note, font=f_src, fill=MUTED)

    # 브랜드
    if brand:
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0] - bw) / 2, CANVAS[1] - 80),
                  brand, font=f_brand, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    out = Path("/tmp/soccer_squad_test.jpg")
    cells = [
        # ST row — 1000~5000
        [{"name": "조규성"}, {"name": "황희찬"}, {"name": "오현규"},
         {"name": "손흥민"}, {"name": "차범근", "is_legend": True}],
        # CDM row
        [{"name": "백승호"}, {"name": "정우영"}, {"name": "황인범"},
         {"name": "기성용"}, {"name": "박지성", "is_legend": True}],
        # GK row
        [{"name": "김동준"}, {"name": "송범근"}, {"name": "조현우"},
         {"name": "김승규"}, {"name": "이운재", "is_legend": True}],
    ]
    make_soccer_squad_matrix(
        title="1000억으로 국대 영입하기",
        highlight="1000억",
        rule_hint="당신의 영입 픽은?",
        col_headers=["100억", "200억", "300억", "400억", "500억"],
        row_headers=["스트라이커", "미드필더", "골키퍼"],
        cells=cells,
        output_path=out,
        brand="@daily_enter_kr",
        source_note="※ 가상 영입 시나리오 — 실제 이적료 X",
    )
    print("✓", out)
