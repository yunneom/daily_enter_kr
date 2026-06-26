"""
걸그룹 월드컵 32강 대진표 카드 — 토너먼트 브라켓 트리.

[구조]
32명 → 4개 1/4 브라켓(Q0-Q3, 각 8명). 상반부(Q0·Q1)·하반부(Q2·Q3) 2장으로 분할.
각 반쪽 = 16명 → R32(8매치) → 16강(4) → 8강(2) → 4강(1) → 결승 진출.
TOP1-4 분산 시드 덕에 빅매치는 결승까지 안 만남 → 브라켓에 그대로 드러남.

[디자인]
좌측에 R32 16명 chip(시드순위 배지 + 이름 + 그룹), 우측으로 브라켓 라인 수렴.
컬럼 헤더(32강·16강·8강·4강·결승진출). 마지막 🏆. 하단 투표 안내.

[사용]
make_bracket_half("top"|"bottom", data, out)  — 반쪽 1장
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image
from make_worldcup_match_card import group_emoji_for


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)
BG_TOP = (28, 22, 68)
BG_BOT = (78, 28, 96)
GOLD = (255, 220, 120)
PINK = (255, 102, 184)
WHITE_DIM = (220, 215, 235)
CARD_BG = (255, 255, 255)
LINE = (255, 220, 120)
SLOT_DIM = (90, 78, 130)

# 컬럼 X (chip 좌측만 이름, 나머지는 라인 수렴 지점)
COL_HEADERS_X = [150, 392, 580, 760, 950]  # 32강/16강/8강/4강/결승
CHIP_X0, CHIP_X1 = 22, 282
ZONE_TOP, ZONE_BOT = 300, 1700


def _font(weight, size):
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[k] * (1 - t) + bot[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def _centered(draw, text, font, cx, y, fill=WHITE, stroke=0, sfill=None):
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kw = dict(font=font, fill=fill)
    if stroke:
        kw["stroke_width"] = stroke; kw["stroke_fill"] = sfill or INK
    draw.text((cx - w / 2, y), text, **kw)


def _chip(img, draw, cy, member: Dict):
    """R32 멤버 chip — 시드 배지 + 그룹 emoji + 이름 + 그룹."""
    h = 78
    y0, y1 = int(cy - h / 2), int(cy + h / 2)
    draw.rounded_rectangle([CHIP_X0, y0, CHIP_X1, y1], radius=14,
                           fill=CARD_BG, outline=GOLD, width=3)
    # 시드 배지 (좌)
    rk = member.get("rank", "")
    badge_d = 42
    bx, by = CHIP_X0 + 8, int(cy - badge_d / 2)
    draw.ellipse([bx, by, bx + badge_d, by + badge_d], fill=PINK)
    bf = _font("Bold", 24 if len(str(rk)) < 2 else 22)
    bb = bf.getbbox(str(rk))
    draw.text((bx + badge_d / 2 - (bb[2] - bb[0]) / 2 - 1,
               by + badge_d / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
              str(rk), font=bf, fill=WHITE)
    # 그룹 emoji (배지 옆)
    em = _get_emoji_image(group_emoji_for(member.get("group", "")), 34)
    ex = CHIP_X0 + 58
    if em:
        img.alpha_composite(em, (ex, int(cy - 17)))
    # 이름 + 그룹
    name = member.get("member", "")
    nf = _font("Bold", 34)
    tx = CHIP_X0 + 100
    draw.text((tx, cy - 30), name, font=nf, fill=INK)
    gf = _font("Medium", 19)
    draw.text((tx, cy + 8), member.get("group", ""), font=gf, fill=(120, 120, 130))


def _connect(draw, src_cys, src_x, tgt_cys, tgt_x):
    """src(2N) → tgt(N) 브라켓 라인. bar 는 src_x 와 tgt_x 중간."""
    bar = (src_x + tgt_x) // 2
    for j in range(len(tgt_cys)):
        ya, yb = src_cys[2 * j], src_cys[2 * j + 1]
        ty = tgt_cys[j]
        draw.line([(src_x, ya), (bar, ya)], fill=LINE, width=3)
        draw.line([(src_x, yb), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ya), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ty), (tgt_x, ty)], fill=LINE, width=3)


def make_bracket_half(half: str, data: dict, output_path: Path,
                      vote_note: str = "🔴 32강 투표 진행 중 — 프로필에서 매치 참여!",
                      source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> Path:
    """half = 'top'(Q0·Q1) | 'bottom'(Q2·Q3)."""
    quarters = (0, 1) if half == "top" else (2, 3)
    half_label = "상반부 (A조·B조)" if half == "top" else "하반부 (C조·D조)"

    matches = [m for m in data["rounds"]["R32"]["matches"]
               if m["quarter"] in quarters]
    matches.sort(key=lambda m: (m["quarter"], m["slot"]))
    # 16 chip (매치 8개 × 2)
    chips = []
    for m in matches:
        chips.append(m["a"]); chips.append(m["b"])
    assert len(chips) == 16, f"{len(chips)} chips"

    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    em = _get_emoji_image("🏆", 70)
    title = "걸그룹 월드컵 대진표"
    tf = _font("Bold", 66)
    bb = tf.getbbox(title); tw = bb[2] - bb[0]
    sx = (CANVAS[0] - tw - 84) // 2
    if em:
        img.alpha_composite(em, (sx, 40))
    d.text((sx + 84, 44), title, font=tf, fill=GOLD, stroke_width=3, stroke_fill=INK)
    sf = _font("Bold", 40)
    _centered(d, f"32강 · {half_label}", sf, CANVAS[0] // 2, 130, fill=WHITE)
    hint = _font("Medium", 24)
    _centered(d, "숫자 = 브랜드평판 시드순위 · 빅매치는 결승까지 안 만남",
              hint, CANVAS[0] // 2, 192, fill=WHITE_DIM)

    # 컬럼 헤더
    colf = _font("Bold", 30)
    for i, lbl in enumerate(["32강", "16강", "8강", "4강", "결승"]):
        _centered(d, lbl, colf, COL_HEADERS_X[i], 244, fill=GOLD)

    # y 좌표 계산
    H = ZONE_BOT - ZONE_TOP
    chip_cy = [ZONE_TOP + (k + 0.5) * H / 16 for k in range(16)]
    r16 = [(chip_cy[2 * j] + chip_cy[2 * j + 1]) / 2 for j in range(8)]
    qf = [(r16[2 * j] + r16[2 * j + 1]) / 2 for j in range(4)]
    sf_cy = [(qf[2 * j] + qf[2 * j + 1]) / 2 for j in range(2)]
    fin = (sf_cy[0] + sf_cy[1]) / 2

    # 브라켓 라인 (chip → r16 → qf → sf → fin)
    _connect(d, chip_cy, CHIP_X1, r16, 300)
    _connect(d, r16, 300, qf, 490)
    _connect(d, qf, 490, sf_cy, 670)
    _connect(d, sf_cy, 670, [fin], 850)

    # chip 그리기 (라인 위에)
    for k in range(16):
        _chip(img, d, chip_cy[k], chips[k])

    # 결승 진출 슬롯 (끝점)
    fy0, fy1 = int(fin - 50), int(fin + 50)
    d.rounded_rectangle([870, fy0, 1056, fy1], radius=18,
                        fill=None, outline=GOLD, width=4)
    ff = _font("Bold", 34)
    _centered(d, "🏆", _font("Bold", 44), 963, fin - 46)
    _centered(d, "결승 진출", ff, 963, fin + 6, fill=GOLD)

    # 하단 투표 안내 박스
    d.rounded_rectangle([40, 1740, CANVAS[0] - 40, 1830], radius=20, fill=GOLD)
    vf = _font("Bold", 36)
    _centered(d, vote_note, vf, CANVAS[0] // 2, 1762, fill=INK)

    # 풋터
    mf = _font("Medium", 24)
    _centered(d, source_note, mf, CANVAS[0] // 2, 1850, fill=WHITE_DIM)
    _centered(d, "@daily_enter_kr · 매일 새로운 픽", mf, CANVAS[0] // 2, 1884,
              fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


# ════════════════════════════════════════════════════════════
#  단일 카드 — 양사이드 브라켓 (좌 16명 / 우 16명 → 중앙 결승)
# ════════════════════════════════════════════════════════════

# 좌측 chip / 우측 chip x 범위
L_CHIP_X0, L_CHIP_X1 = 16, 250
R_CHIP_X0, R_CHIP_X1 = 830, 1064
FULL_ZONE_TOP, FULL_ZONE_BOT = 286, 1664


def _chip_side(img, draw, cy, member: Dict, side: str, eliminated: bool = False,
               winner: bool = False, x_range=None, chip_h: int = 70):
    """양사이드용 chip — 시그니처 컬러 그라데이션 + 흰 박스 'GRP 이름'.
    eliminated=True 면 회색 톤(탈락 표시). winner=True 면 우측에 WIN 배지.
    x_range=(x0,x1) 로 너비 override. chip_h 로 높이 override."""
    from make_worldcup_match_card import group_color_for, group_en_for
    h = chip_h
    if x_range is not None:
        x0, x1 = x_range
    else:
        x0, x1 = (L_CHIP_X0, L_CHIP_X1) if side == "L" else (R_CHIP_X0, R_CHIP_X1)
    y0, y1 = int(cy - h / 2), int(cy + h / 2)
    w_, h_ = x1 - x0, y1 - y0
    grp = member.get("group", "")
    if eliminated:
        top, bot = (130, 130, 140), (90, 90, 100)
    else:
        top, bot = group_color_for(grp)
    # 그라데이션 카드
    grad = _vgrad((w_, h_), top, bot).convert("RGBA")
    mask = Image.new("L", (w_, h_), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w_-1, h_-1], radius=12, fill=255)
    chip = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    chip.paste(grad, (0, 0), mask)
    img.alpha_composite(chip, (x0, y0))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=12, outline=GOLD, width=3)

    rk = str(member.get("rank", ""))
    name = member.get("member", "")
    grp_en = group_en_for(grp)
    one = f"{grp_en} {name}"
    badge_d = 38
    nf = _font("Bold", 22)
    def _tw(s, f): bb = f.getbbox(s); return bb[2] - bb[0]
    # 흰 박스 안 한 줄 시도 (그룹영문 + 이름), 너무 길면 이름만
    box_w = w_ - badge_d - 18  # 배지 자리 빼고
    while _tw(one, nf) > box_w - 14 and nf.size > 14:
        nf = _font("Bold", nf.size - 1)
    if _tw(one, nf) > box_w - 14:
        # 이름만
        text = name
        while _tw(text, nf) > box_w - 14 and nf.size > 14:
            nf = _font("Bold", nf.size - 1)
    else:
        text = one
    tw = _tw(text, nf)

    if side == "L":
        # 좌측: 배지(좌) + 흰박스(우)
        bx = x0 + 6
        draw.ellipse([bx, cy - badge_d / 2, bx + badge_d, cy + badge_d / 2], fill=PINK)
        bf = _font("Bold", 22 if len(rk) < 2 else 20)
        bbb = bf.getbbox(rk)
        draw.text((bx + badge_d / 2 - (bbb[2] - bbb[0]) / 2 - 1,
                   cy - (bbb[3] - bbb[1]) / 2 - bbb[1]), rk, font=bf, fill=WHITE)
        # 흰 박스
        bxl = x0 + badge_d + 12
        bxr = x1 - 6
        draw.rounded_rectangle([bxl, cy - 18, bxr, cy + 18],
                               radius=8, fill=(255, 255, 255))
        draw.text((bxl + (bxr - bxl - tw) / 2, cy - nf.size / 2 - 2),
                  text, font=nf, fill=INK if not eliminated else (140, 140, 150))
    else:
        bx = x1 - 6 - badge_d
        draw.ellipse([bx, cy - badge_d / 2, bx + badge_d, cy + badge_d / 2], fill=PINK)
        bf = _font("Bold", 22 if len(rk) < 2 else 20)
        bbb = bf.getbbox(rk)
        draw.text((bx + badge_d / 2 - (bbb[2] - bbb[0]) / 2 - 1,
                   cy - (bbb[3] - bbb[1]) / 2 - bbb[1]), rk, font=bf, fill=WHITE)
        bxl = x0 + 6
        bxr = x1 - badge_d - 12
        draw.rounded_rectangle([bxl, cy - 18, bxr, cy + 18],
                               radius=8, fill=(255, 255, 255))
        draw.text((bxl + (bxr - bxl - tw) / 2, cy - nf.size / 2 - 2),
                  text, font=nf, fill=INK if not eliminated else (140, 140, 150))

    # WIN 배지 — 우상단에 작은 골드 캡슐
    if winner:
        wf = _font("Bold", 16)
        wstr = "WIN"
        wbb = wf.getbbox(wstr); ww = wbb[2] - wbb[0]
        wxr = x1 - 4
        wxl = wxr - ww - 14
        wy0 = y0 - 8
        wy1 = wy0 + 24
        draw.rounded_rectangle([wxl, wy0, wxr, wy1], radius=10, fill=(50, 200, 90))
        draw.text((wxl + 7, wy0 + 2), wstr, font=wf, fill=WHITE)


def _connect_side(draw, src_cys, src_x, tgt_cys, tgt_x):
    """좌→우 또는 우→좌 수렴 라인. src_x→tgt_x 방향 자동."""
    bar = (src_x + tgt_x) // 2
    for j in range(len(tgt_cys)):
        ya, yb = src_cys[2 * j], src_cys[2 * j + 1]
        ty = tgt_cys[j]
        draw.line([(src_x, ya), (bar, ya)], fill=LINE, width=3)
        draw.line([(src_x, yb), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ya), (bar, yb)], fill=LINE, width=3)
        draw.line([(bar, ty), (tgt_x, ty)], fill=LINE, width=3)


def make_bracket_full(data: dict, output_path: Path,
                      vote_note: str = "🔴 32강 투표 진행 중 — 프로필에서 매치 참여!",
                      source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> Path:
    """단일 카드 — 좌(Q0·Q1 16명) / 우(Q2·Q3 16명) → 중앙 🏆 결승."""
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    em = _get_emoji_image("🏆", 64)
    title = "걸그룹 월드컵 32강 대진표"
    tf = _font("Bold", 56)
    bb = tf.getbbox(title); tw = bb[2] - bb[0]
    sx = (CANVAS[0] - tw - 76) // 2
    if em:
        img.alpha_composite(em, (sx, 42))
    d.text((sx + 76, 50), title, font=tf, fill=GOLD, stroke_width=3, stroke_fill=INK)
    hint = _font("Medium", 23)
    _centered(d, "숫자 = 브랜드평판 시드 · TOP1-4 는 결승까지 안 만남",
              hint, CANVAS[0] // 2, 132, fill=WHITE_DIM)

    # 컬럼 헤더 (좌→우 대칭). 4강은 라인이 표현 → 헤더는 32/16/8 + 중앙 결승.
    colf = _font("Bold", 24)
    for cx, lbl in [(133, "32강"), (300, "16강"), (430, "8강"),
                    (947, "32강"), (780, "16강"), (650, "8강")]:
        _centered(d, lbl, colf, cx, 178, fill=GOLD)
    _centered(d, "결승", _font("Bold", 28), CANVAS[0] // 2, 174, fill=PINK)

    # 진출 추적: R32 매치별 winner.rank → 진출자 set (eliminated chip 회색 처리용)
    advanced_ranks = set()
    for m in data["rounds"]["R32"].get("matches", []):
        w = m.get("winner")
        if w and w.get("rank") is not None:
            advanced_ranks.add(w["rank"])

    # 좌/우 chip 데이터 (member 와 eliminated 플래그)
    def half_chips(quarters):
        ms = [m for m in data["rounds"]["R32"]["matches"] if m["quarter"] in quarters]
        ms.sort(key=lambda m: (m["quarter"], m["slot"]))
        ch = []
        for m in ms:
            ch.append((m["a"], m["a"]["rank"] not in advanced_ranks))
            ch.append((m["b"], m["b"]["rank"] not in advanced_ranks))
        return ch
    left = half_chips((0, 1))
    right = half_chips((2, 3))

    H = FULL_ZONE_BOT - FULL_ZONE_TOP
    cy16 = [FULL_ZONE_TOP + (k + 0.5) * H / 16 for k in range(16)]
    cy8 = [(cy16[2 * j] + cy16[2 * j + 1]) / 2 for j in range(8)]
    cy4 = [(cy8[2 * j] + cy8[2 * j + 1]) / 2 for j in range(4)]
    cy2 = [(cy4[2 * j] + cy4[2 * j + 1]) / 2 for j in range(2)]
    cy1 = (cy2[0] + cy2[1]) / 2  # 준결승(반쪽 결승 진출) y
    center_cy = (FULL_ZONE_TOP + FULL_ZONE_BOT) / 2

    # 좌측 라인 (chip → 안쪽으로 수렴): x 증가 방향
    _connect_side(d, cy16, L_CHIP_X1, cy8, 330)
    _connect_side(d, cy8, 330, cy4, 460)
    _connect_side(d, cy4, 460, cy2, 560)
    # 좌 반쪽결승 → 중앙
    d.line([(560, cy1), (CANVAS[0] // 2 - 70, cy1)], fill=LINE, width=3)
    d.line([(CANVAS[0] // 2 - 70, cy1), (CANVAS[0] // 2 - 70, center_cy)], fill=LINE, width=3)
    d.line([(CANVAS[0] // 2 - 70, center_cy), (CANVAS[0] // 2 - 8, center_cy)], fill=LINE, width=3)

    # 우측 라인 (mirror): x 감소 방향
    _connect_side(d, cy16, R_CHIP_X0, cy8, 750)
    _connect_side(d, cy8, 750, cy4, 620)
    _connect_side(d, cy4, 620, cy2, 520)
    d.line([(520, cy1), (CANVAS[0] // 2 + 70, cy1)], fill=LINE, width=3)
    d.line([(CANVAS[0] // 2 + 70, cy1), (CANVAS[0] // 2 + 70, center_cy)], fill=LINE, width=3)
    d.line([(CANVAS[0] // 2 + 70, center_cy), (CANVAS[0] // 2 + 8, center_cy)], fill=LINE, width=3)

    # chip 그리기
    for k in range(16):
        lm, lelim = left[k]
        rm, relim = right[k]
        _chip_side(img, d, cy16[k], lm, "L", eliminated=lelim)
        _chip_side(img, d, cy16[k], rm, "R", eliminated=relim)

    # 중앙 🏆 결승 트로피
    tem = _get_emoji_image("🏆", 96)
    if tem:
        img.alpha_composite(tem, (CANVAS[0] // 2 - 48, int(center_cy - 80)))
    _centered(d, "결승", _font("Bold", 32), CANVAS[0] // 2, int(center_cy + 24),
              fill=GOLD, stroke=2, sfill=INK)

    # 하단 투표 안내
    d.rounded_rectangle([40, 1690, CANVAS[0] - 40, 1778], radius=20, fill=GOLD)
    _centered(d, vote_note, _font("Bold", 34), CANVAS[0] // 2, 1712, fill=INK)

    # 풋터
    mf = _font("Medium", 23)
    _centered(d, source_note, mf, CANVAS[0] // 2, 1808, fill=WHITE_DIM)
    _centered(d, "@daily_enter_kr · 매일 새로운 픽", mf, CANVAS[0] // 2, 1842,
              fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


# ════════════════════════════════════════════════════════════
#  16강 단독 대진표 — chip 8 좌 + 8 우, R8/R4/결승 라인 완전 연결
# ════════════════════════════════════════════════════════════

# 16강 chip x 범위 (32강보다 약간 넓음 = 가독성 ↑)
R16_L_X0, R16_L_X1 = 16, 320
R16_R_X0, R16_R_X1 = 760, 1064
R16_ZONE_TOP, R16_ZONE_BOT = 290, 1670


def make_bracket_r16(data: dict, output_path: Path,
                     vote_note: str = "🔴 16강 투표 진행 중! ~6/29(월) 12시 마감",
                     source_note: str = "출처: 한국기업평판연구소 2026.6.21") -> Path:
    """16강 대진표 단독 — 좌 4 매치 + 우 4 매치 → 결승. 결승 라인 완전 연결."""
    matches = data["rounds"]["R16"]["matches"]
    left_ms = sorted([m for m in matches if m["quarter"] in (0, 1)],
                     key=lambda m: (m["quarter"], m["slot"]))
    right_ms = sorted([m for m in matches if m["quarter"] in (2, 3)],
                      key=lambda m: (m["quarter"], m["slot"]))

    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 헤더
    em = _get_emoji_image("🏆", 72)
    title = "걸그룹 월드컵 16강"
    tf = _font("Bold", 64)
    bb = tf.getbbox(title); tw = bb[2] - bb[0]
    sx = (CANVAS[0] - tw - 90) // 2
    if em:
        img.alpha_composite(em, (sx, 56))
    d.text((sx + 90, 60), title, font=tf, fill=GOLD,
           stroke_width=3, stroke_fill=INK)
    hf = _font("Medium", 26)
    _centered(d, "결승까지 한 눈에 · 숫자 = 브랜드평판 시드순위",
              hf, CANVAS[0] // 2, 152, fill=WHITE_DIM)

    # 컬럼 헤더 — 16강 / 8강 / 4강 (좌우 대칭) + 중앙 결승
    colf = _font("Bold", 28)
    for cx, lbl in [(168, "16강"), (365, "8강"), (455, "4강"),
                    (912, "16강"), (715, "8강"), (625, "4강")]:
        _centered(d, lbl, colf, cx, 198, fill=GOLD)
    _centered(d, "결승", _font("Bold", 32), CANVAS[0] // 2, 194, fill=PINK)

    # y 좌표 — 8 chip
    H = R16_ZONE_BOT - R16_ZONE_TOP
    cy_chip = [R16_ZONE_TOP + (k + 0.5) * H / 8 for k in range(8)]
    cy_r8 = [(cy_chip[2 * j] + cy_chip[2 * j + 1]) / 2 for j in range(4)]
    cy_r4 = [(cy_r8[2 * j] + cy_r8[2 * j + 1]) / 2 for j in range(2)]
    cy_final_in = (cy_r4[0] + cy_r4[1]) / 2
    center_cy = (R16_ZONE_TOP + R16_ZONE_BOT) / 2

    # 라인 x 좌표 — 브라켓이 중앙을 넘지 않도록 center=540 이내 유지
    LX_R8, LX_R4, LX_FIN = 400, 460, 490
    RX_R8 = CANVAS[0] - 400   # 680
    RX_R4 = CANVAS[0] - 460   # 620
    RX_FIN = CANVAS[0] - 490  # 590

    # 좌측 라인
    _connect_side(d, cy_chip, R16_L_X1, cy_r8, LX_R8)
    _connect_side(d, cy_r8, LX_R8, cy_r4, LX_R4)
    _connect_side(d, cy_r4, LX_R4, [cy_final_in], LX_FIN)
    # 4강 수렴점 → 결승 트로피: 수직 ↓ + 수평 → (선 하나)
    d.line([(LX_FIN, cy_final_in), (LX_FIN, center_cy)], fill=LINE, width=3)
    d.line([(LX_FIN, center_cy), (CANVAS[0] // 2 - 8, center_cy)], fill=LINE, width=3)

    # 우측 라인 (대칭)
    _connect_side(d, cy_chip, R16_R_X0, cy_r8, RX_R8)
    _connect_side(d, cy_r8, RX_R8, cy_r4, RX_R4)
    _connect_side(d, cy_r4, RX_R4, [cy_final_in], RX_FIN)
    # 4강 수렴점 → 결승 트로피: 수직 ↓ + 수평 ← (선 하나)
    d.line([(RX_FIN, cy_final_in), (RX_FIN, center_cy)], fill=LINE, width=3)
    d.line([(RX_FIN, center_cy), (CANVAS[0] // 2 + 8, center_cy)], fill=LINE, width=3)

    # chip 그리기 — WIN 배지 없음 (16강 진출자만 모아놓은 브라켓이라 불필요)
    for j, m in enumerate(left_ms):
        for k, mem in [(2 * j, m["a"]), (2 * j + 1, m["b"])]:
            _chip_side(img, d, cy_chip[k], mem, "L",
                       x_range=(R16_L_X0, R16_L_X1), chip_h=88)
    for j, m in enumerate(right_ms):
        for k, mem in [(2 * j, m["a"]), (2 * j + 1, m["b"])]:
            _chip_side(img, d, cy_chip[k], mem, "R",
                       x_range=(R16_R_X0, R16_R_X1), chip_h=88)

    # 중앙 결승 트로피
    tem = _get_emoji_image("🏆", 120)
    if tem:
        img.alpha_composite(tem, (CANVAS[0] // 2 - 60, int(center_cy - 100)))
    _centered(d, "결승", _font("Bold", 38), CANVAS[0] // 2, int(center_cy + 32),
              fill=GOLD, stroke=2, sfill=INK)

    # 하단 vote 박스 + 풋터
    d.rounded_rectangle([40, 1700, CANVAS[0] - 40, 1796],
                        radius=20, fill=GOLD)
    _centered(d, vote_note, _font("Bold", 32), CANVAS[0] // 2, 1722, fill=INK)
    mf = _font("Medium", 23)
    _centered(d, source_note, mf, CANVAS[0] // 2, 1818, fill=WHITE_DIM)
    _centered(d, "@daily_enter_kr · 매일 새로운 픽", mf, CANVAS[0] // 2, 1854,
              fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent
    data = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "output_enter" / "publish" / "worldcup_bracket"
    full = out_dir / "bracket_full.jpg"
    make_bracket_full(data, full)
    print(f"✓ {full} ({full.stat().st_size // 1024}KB)")
    r16 = out_dir / "bracket_r16.jpg"
    make_bracket_r16(data, r16)
    print(f"✓ {r16} ({r16.stat().st_size // 1024}KB)")
