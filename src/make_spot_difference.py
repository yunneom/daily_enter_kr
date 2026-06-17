"""
틀린 곰 찾기 — spot-the-difference 퍼즐 (모구/카피바라 대체: 곰돌이).

@mogu._.ma 의 "다른 모구는 하나!" 포맷을 코드로 재현하되, 캐릭터는
카피바라가 아닌 절차적 곰돌이(둥근 귀 + 주둥이)로 차별화.

[메커니즘]
- 5×6 = 30 마리 곰. 1마리만 미묘하게 다름 (윙크/볼터치/혀/귀 등)
- 시청자가 찾으려 화면 정지·확대 → 체류 ↑ + "몇 번째!" 댓글 폭발
- 정답 위치 + 차이 종류를 seed 로 회전 → 매 게시 다른 퍼즐
"""

import sys
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font


CANVAS = (1080, 1920)
BG = (253, 251, 247)
INK = (60, 48, 40)
MUTED = (150, 140, 132)

# 곰돌이 팔레트
FUR = (208, 170, 132)
FUR_DARK = (180, 142, 104)
EAR_INNER = (235, 205, 178)
SNOUT = (240, 222, 200)
NOSE = (90, 68, 52)
BLUSH = (244, 168, 158)
TONGUE = (232, 130, 130)

GRID_COLS = 5
GRID_ROWS = 6

# 차이 종류 — odd 곰에 적용 (subtle 하지만 찾을 수 있게)
ODD_TYPES = ["wink", "blush", "tongue", "ear_tilt", "eyebrows"]


def _draw_bear(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int,
               odd: bool = False, odd_type: str = "wink"):
    """둥근 곰돌이 한 마리. odd=True 면 odd_type 차이를 적용."""
    r = size // 2
    # ── 귀 (둥근 두 개) ──
    ear_r = int(r * 0.34)
    ear_dx = int(r * 0.62)
    ear_dy = int(r * 0.72)
    ear_sizes = [ear_r, ear_r]
    if odd and odd_type == "ear_tilt":
        ear_sizes[1] = int(ear_r * 0.66)  # 오른쪽 귀 작게
    for sign, er in zip((-1, 1), ear_sizes):
        ex = cx + sign * ear_dx
        ey = cy - ear_dy
        draw.ellipse([ex - er, ey - er, ex + er, ey + er],
                     fill=FUR, outline=INK, width=3)
        draw.ellipse([ex - int(er*0.5), ey - int(er*0.5),
                      ex + int(er*0.5), ey + int(er*0.5)], fill=EAR_INNER)

    # ── 머리/몸 (둥근 사각형) ──
    draw.rounded_rectangle([cx - r, cy - int(r*0.85), cx + r, cy + int(r*1.0)],
                           radius=int(r*0.7), fill=FUR, outline=INK, width=3)

    # ── 눈 ──
    eye_y = cy - int(r*0.12)
    eye_dx = int(r*0.38)
    eye_r = max(3, int(r*0.11))
    if odd and odd_type == "wink":
        # 왼쪽 눈 윙크 (호)
        draw.arc([cx - eye_dx - eye_r-2, eye_y - eye_r, cx - eye_dx + eye_r+2, eye_y + eye_r],
                 start=200, end=340, fill=INK, width=4)
        draw.ellipse([cx + eye_dx - eye_r, eye_y - eye_r,
                      cx + eye_dx + eye_r, eye_y + eye_r], fill=INK)
    else:
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=INK)

    # 눈썹 (odd 전용)
    if odd and odd_type == "eyebrows":
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            draw.line([(ex - eye_r-2, eye_y - eye_r*2-2),
                       (ex + eye_r+2, eye_y - eye_r*2-5)], fill=INK, width=3)

    # ── 주둥이 + 코 ──
    snout_w = int(r*0.62); snout_h = int(r*0.46)
    snout_cy = cy + int(r*0.28)
    draw.ellipse([cx - snout_w, snout_cy - snout_h, cx + snout_w, snout_cy + snout_h],
                 fill=SNOUT, outline=INK, width=2)
    # 코
    nose_w = int(r*0.18)
    draw.ellipse([cx - nose_w, snout_cy - int(snout_h*0.5),
                  cx + nose_w, snout_cy + int(snout_h*0.05)], fill=NOSE)
    # 입 (코 아래 Y)
    mouth_y = snout_cy + int(snout_h*0.18)
    draw.line([(cx, snout_cy), (cx, mouth_y)], fill=NOSE, width=2)
    draw.arc([cx - int(r*0.26), mouth_y - 6, cx, mouth_y + int(r*0.18)],
             start=20, end=140, fill=NOSE, width=2)
    draw.arc([cx, mouth_y - 6, cx + int(r*0.26), mouth_y + int(r*0.18)],
             start=40, end=160, fill=NOSE, width=2)

    # 혀 (odd 전용)
    if odd and odd_type == "tongue":
        draw.ellipse([cx - int(r*0.12), mouth_y + int(r*0.06),
                      cx + int(r*0.12), mouth_y + int(r*0.28)],
                     fill=TONGUE, outline=NOSE, width=1)

    # 볼터치 (odd 전용)
    if odd and odd_type == "blush":
        for sign in (-1, 1):
            bx = cx + sign * int(r*0.6)
            by = cy + int(r*0.18)
            draw.ellipse([bx - int(r*0.16), by - int(r*0.09),
                          bx + int(r*0.16), by + int(r*0.09)], fill=BLUSH)


# 차이 종류별 한국어 힌트 (정답 공개용 — 현재는 캡션/댓글에서 활용 가능)
ODD_TYPE_KR = {
    "wink": "윙크하는 곰", "blush": "볼터치한 곰", "tongue": "혀 내민 곰",
    "ear_tilt": "한쪽 귀 작은 곰", "eyebrows": "눈썹 있는 곰",
}


def make_spot_difference(
    output_path: Path,
    seed: int = 0,
    title: str = "다른 곰은 하나!",
    subtitle: str = "어디 있을까?",
    brand: str = "",
    answer_note: bool = False,
):
    """5×6 곰 그리드 + 1마리만 다름. seed 로 정답 위치/차이 종류 회전.

    Returns: (output_path, answer_index, odd_type) — 정답 1-based 위치 + 차이.
    """
    img = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(img)

    bold = _resolve_font("Bold")
    medium = _resolve_font("Medium")
    f_title = ImageFont.truetype(bold, 84)
    f_sub = ImageFont.truetype(medium, 44)
    f_brand = ImageFont.truetype(medium, 30)

    # 제목
    tw = draw.textlength(title, font=f_title)
    draw.text(((CANVAS[0]-tw)/2, 150), title, font=f_title, fill=INK)
    sw = draw.textlength(subtitle, font=f_sub)
    draw.text(((CANVAS[0]-sw)/2, 262), subtitle, font=f_sub, fill=MUTED)

    # 정답 위치 + 차이 종류 (seed 결정)
    total = GRID_COLS * GRID_ROWS
    odd_index = seed % total
    odd_type = ODD_TYPES[(seed // total) % len(ODD_TYPES)]

    # 그리드 영역
    grid_top = 380
    grid_bottom = CANVAS[1] - 220
    grid_left = 80
    grid_right = CANVAS[0] - 80
    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS
    bear_size = int(min(cell_w, cell_h) * 0.78)

    for i in range(total):
        rr, cc = divmod(i, GRID_COLS)
        cx = int(grid_left + cc * cell_w + cell_w / 2)
        cy = int(grid_top + rr * cell_h + cell_h / 2)
        _draw_bear(draw, cx, cy, bear_size,
                   odd=(i == odd_index), odd_type=odd_type)

    # 정답 표시 (디버그/정답편 — 빨간 동그라미)
    if answer_note:
        rr, cc = divmod(odd_index, GRID_COLS)
        cx = int(grid_left + cc * cell_w + cell_w / 2)
        cy = int(grid_top + rr * cell_h + cell_h / 2)
        rad = int(bear_size * 0.62)
        draw.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=(230, 60, 60), width=6)

    if brand:
        bw = draw.textlength(brand, font=f_brand)
        draw.text(((CANVAS[0]-bw)/2, CANVAS[1]-130), brand, font=f_brand, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=94)
    return output_path, odd_index + 1, odd_type


if __name__ == "__main__":
    for s in (0, 7, 33):
        p, ans, typ = make_spot_difference(
            Path(f"/tmp/spot_bear_s{s}.jpg"), seed=s, brand="@daily_enter_kr")
        print(f"seed={s} → {p}  정답 {ans}번째 ({ODD_TYPE_KR[typ]})")
