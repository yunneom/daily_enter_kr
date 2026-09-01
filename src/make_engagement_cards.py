"""
참여형(engagement) 포맷 전용 카드 렌더러 — 1080x1920 (9:16).

포맷별 카드:
- make_text_cover      : 텍스트 표지 (밸런스게임/케미/카운트다운 공용)
- make_balance_card    : 상하 2분할 A/B 선택 카드
- make_member_photo_card: 실물사진 풀블리드 + 하단 이름 (퍼즈 챌린지 프레임/정답 카드)
- make_unit_grid_card  : 4행x3열 실물사진 그리드 (드림 유닛 빌더)
- make_duo_card        : 같은 그룹 2인 나란히 (케미 투표 후보)
- make_result_bar_card : 득표율 가로 바 결과 카드
- make_countdown_card  : 브랜드평판 카운트다운 낱장 (큰 순위 + 사진/이름)
- make_cta_card        : 참여 유도 마무리 카드

사진은 반드시 idol_photo.fetch_photo() 를 통과한 로컬 경로만 받는다
(커먼즈 검증 + 성인 게이트가 그 안에 있음). 이 모듈은 경로가 None 이면
그룹 컬러 그라디언트 폴백을 그린다 — 외부에서 임의 URL 을 넣지 말 것.

스타일: 뉴스 카드(minimal 흰 배경)와 구분되는 다크 그라디언트 베이스
(웹 월드컵 테마 #0b0b12 계열) — 피드에서 뉴스와 시각적으로 분리.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from make_card import _resolve_font

CANVAS = (1080, 1920)
BG_TOP = (18, 16, 30)
BG_BOT = (11, 11, 18)
INK = (244, 244, 247)
MUTED = (150, 150, 165)
ACCENT = (124, 58, 237)     # 보라 (웹 테마)
ACCENT2 = (219, 39, 119)    # 핑크
GOLD = (250, 204, 21)
BAR_BG = (44, 42, 60)

# 그룹 컬러 (웹 lib/colors.ts 와 동일 팔레트)
GROUP_COLORS = {
    "아이브": (37, 99, 235), "에스파": (124, 58, 237), "블랙핑크": (219, 39, 119),
    "소녀시대": (217, 119, 6), "엔믹스": (5, 150, 105), "르세라핌": (220, 38, 38),
    "아일릿": (234, 88, 12), "트와이스": (225, 29, 72), "레드벨벳": (190, 18, 60),
    "시그니처": (13, 148, 136), "프로미스나인": (79, 70, 229), "다이아": (147, 51, 234),
    "리센느": (14, 165, 233), "우주소녀": (192, 38, 211), "위키미키": (245, 158, 11),
}
DEFAULT_GROUP_COLOR = (107, 114, 128)


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size: Tuple[int, int], top: Tuple[int, int, int], bot: Tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px_row = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = px_row
    return img


def _base() -> Image.Image:
    return _vgrad(CANVAS, BG_TOP, BG_BOT)


def _center(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill=INK) -> int:
    w = draw.textlength(text, font=font)
    draw.text(((CANVAS[0] - w) / 2, y), text, font=font, fill=fill)
    return int(y + font.size * 1.35)


def _cover_crop(src: Image.Image, tw: int, th: int) -> Image.Image:
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    src = src.resize((nw, nh), Image.LANCZOS)
    # 인물 사진은 상단(얼굴) 우선 크롭
    x0 = (nw - tw) // 2
    y0 = min((nh - th) // 3, nh - th)
    return src.crop((x0, y0, x0 + tw, y0 + th))


def _photo_or_gradient(photo_path: Optional[str], group: str, size: Tuple[int, int]) -> Image.Image:
    """검증된 로컬 사진 경로 → cover crop. None → 그룹 컬러 그라디언트."""
    if photo_path and Path(photo_path).exists():
        try:
            return _cover_crop(Image.open(photo_path).convert("RGB"), *size)
        except Exception:
            pass
    c = GROUP_COLORS.get(group, DEFAULT_GROUP_COLOR)
    dark = tuple(max(0, int(v * 0.45)) for v in c)
    return _vgrad(size, c, dark)


def _brand_footer(draw: ImageDraw.ImageDraw, text: str = "@daily_enter_kr"):
    f = _font("Medium", 34)
    w = draw.textlength(text, font=f)
    draw.text(((CANVAS[0] - w) / 2, CANVAS[1] - 110), text, font=f, fill=MUTED)


# ─────────────────────────────────────────────────────────────────────────────
def make_text_cover(title_lines: List[str], sub: str, out: Path,
                    kicker: str = "", accent_line_idx: int = -1) -> Path:
    """텍스트 표지. accent_line_idx 줄은 그라디언트 대신 골드로 강조."""
    img = _base()
    draw = ImageDraw.Draw(img)
    n = len(title_lines)
    f_title = _font("Bold", 110 if n <= 2 else 92)
    f_kick = _font("SemiBold", 44)
    f_sub = _font("Medium", 46)

    total_h = n * f_title.size * 1.25 + (90 if kicker else 0) + 120
    y = int((CANVAS[1] - total_h) / 2) - 60
    if kicker:
        # 필 배지
        w = draw.textlength(kicker, font=f_kick)
        x0 = (CANVAS[0] - w) / 2 - 34
        draw.rounded_rectangle([x0, y, x0 + w + 68, y + 84], radius=42,
                               outline=ACCENT, width=3)
        draw.text(((CANVAS[0] - w) / 2, y + 16), kicker, font=f_kick, fill=(233, 213, 255))
        y += 150
    for i, line in enumerate(title_lines):
        fill = GOLD if i == accent_line_idx else INK
        y = _center(draw, y, line, f_title, fill=fill)
    y += 40
    _center(draw, y, sub, f_sub, fill=MUTED)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_balance_card(q_num: int, q_total: int, question: str,
                      opt_a: str, opt_b: str, out: Path) -> Path:
    """상하 2분할 밸런스게임. 위=1(보라) / 아래=2(핑크), 중앙 VS."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_q = _font("SemiBold", 52)
    f_opt = _font("Bold", 72)
    f_num = _font("Bold", 60)
    f_tag = _font("Medium", 38)

    _center(draw, 170, f"Q{q_num}/{q_total}", f_tag, fill=MUTED)
    _center(draw, 240, question, f_q)

    mid = CANVAS[1] // 2 + 60
    panel_m, panel_h = 70, 520
    # 옵션 패널 (1: 위 / 2: 아래)
    for idx, (label, y0, color) in enumerate(
            [(opt_a, mid - panel_h - 40, ACCENT), (opt_b, mid + 40, ACCENT2)]):
        y1 = y0 + panel_h
        draw.rounded_rectangle([panel_m, y0, CANVAS[0] - panel_m, y1], radius=36,
                               fill=tuple(int(v * 0.28) for v in color),
                               outline=color, width=4)
        # 번호 원
        cx, cy = CANVAS[0] // 2, y0 + 120
        draw.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=color)
        nw = draw.textlength(str(idx + 1), font=f_num)
        draw.text((cx - nw / 2, cy - f_num.size * 0.58), str(idx + 1), font=f_num, fill=(255,) * 3)
        # 옵션 텍스트 (2줄 지원)
        lines = _wrap(draw, label, f_opt, CANVAS[0] - panel_m * 2 - 80)
        ty = y0 + 220 if len(lines) > 1 else y0 + 260
        for ln in lines[:2]:
            ty = _center(draw, ty, ln, f_opt)
    # VS
    f_vs = _font("Bold", 84)
    vw = draw.textlength("VS", font=f_vs)
    draw.text(((CANVAS[0] - vw) / 2, mid - 52), "VS", font=f_vs, fill=GOLD)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def _wrap(draw, text, font, max_w) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def make_member_photo_card(photo_path: Optional[str], name: str, group: str,
                           out: Path, sub: str = "", big_text: str = "") -> Path:
    """실물사진 풀블리드 + 하단 그라디언트 + 이름. big_text 는 상단 대형 라벨
    (카운트다운 순위 등)."""
    img = _photo_or_gradient(photo_path, group, CANVAS)
    # 하단 가독성 그라디언트
    grad = Image.new("L", (1, 500))
    for y in range(500):
        grad.putpixel((0, y), int(210 * (y / 499)))
    alpha = grad.resize((CANVAS[0], 500))
    black = Image.new("RGB", (CANVAS[0], 500), (5, 5, 10))
    img.paste(black, (0, CANVAS[1] - 500), alpha)

    draw = ImageDraw.Draw(img)
    if big_text:
        f_big = _font("Bold", 200)
        # 상단 배지 배경
        w = draw.textlength(big_text, font=f_big)
        draw.text((70, 150), big_text, font=f_big, fill=GOLD,
                  stroke_width=8, stroke_fill=(5, 5, 10))
    f_name = _font("Bold", 92)
    f_grp = _font("SemiBold", 46)
    nw = draw.textlength(name, font=f_name)
    draw.text(((CANVAS[0] - nw) / 2, CANVAS[1] - 360), name, font=f_name, fill=INK)
    gw = draw.textlength(group, font=f_grp)
    draw.text(((CANVAS[0] - gw) / 2, CANVAS[1] - 240), group, font=f_grp,
              fill=GROUP_COLORS.get(group, DEFAULT_GROUP_COLOR))
    if sub:
        f_sub = _font("Medium", 38)
        sw = draw.textlength(sub, font=f_sub)
        draw.text(((CANVAS[0] - sw) / 2, CANVAS[1] - 165), sub, font=f_sub, fill=MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_group_rank_card(photo_path: Optional[str], rank: int, name: str,
                         name_en: str, sub: str, out: Path,
                         kicker: str = "신인 걸그룹 브랜드평판") -> Path:
    """그룹 랭킹 카드 — 가로형 '단체 사진'용.

    커먼즈의 그룹 사진은 대부분 가로형이라 풀블리드(cover crop)로 쓰면 멤버가
    잘려나간다. 대신 원본 비율을 살린 가로 밴드로 중앙 배치하고 위(순위)/아래
    (그룹명·지수)에 텍스트를 둔다. photo_path 가 None 이면 그룹 컬러 그라디언트.
    """
    img = _base()
    draw = ImageDraw.Draw(img)

    # 상단: 킥커 + 대형 순위
    f_kick = _font("SemiBold", 42)
    _center(draw, 130, kicker, f_kick, fill=MUTED)
    f_big = _font("Bold", 230)
    rank_txt = str(rank)
    rw = draw.textlength(rank_txt, font=f_big)
    draw.text(((CANVAS[0] - rw) / 2, 190), rank_txt, font=f_big, fill=GOLD,
              stroke_width=8, stroke_fill=(5, 5, 10))

    # 중앙: 사진 밴드 (원본 비율 유지, 높이 상한만 적용)
    band_top, band_max_h = 540, 780
    if photo_path and Path(photo_path).exists():
        try:
            src = Image.open(photo_path).convert("RGB")
            bw = CANVAS[0]
            bh = min(band_max_h, int(bw * src.size[1] / src.size[0]))
            band = _cover_crop(src, bw, bh)
        except Exception:
            band = _photo_or_gradient(None, name, (CANVAS[0], band_max_h))
            bh = band_max_h
    else:
        band = _photo_or_gradient(None, name, (CANVAS[0], band_max_h))
        bh = band_max_h
    by = band_top + (band_max_h - bh) // 2
    img.paste(band, (0, by))
    draw.line([(0, by - 4), (CANVAS[0], by - 4)], fill=ACCENT, width=4)
    draw.line([(0, by + bh), (CANVAS[0], by + bh)], fill=ACCENT2, width=4)

    # 하단: 그룹명 · 영문명 · 지수
    y = band_top + band_max_h + 90
    f_name = _font("Bold", 100)
    y = _center(draw, y, name, f_name)
    if name_en:
        f_en = _font("SemiBold", 46)
        y = _center(draw, y + 6, name_en, f_en,
                    fill=GROUP_COLORS.get(name, (196, 181, 253)))
    if sub:
        f_sub = _font("Medium", 42)
        _center(draw, y + 18, sub, f_sub, fill=MUTED)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_unit_grid_card(rows: List[List[dict]], out: Path,
                        title: str = "나만의 드림 유닛",
                        rule: str = "각 줄에서 1명씩 — 예: 1-3-2-1") -> Path:
    """4행 x 3열 그리드. rows[r][c] = {photo_path, name, group}.
    각 행 왼쪽에 행 번호, 각 셀 위에 열 번호(1/2/3) + 아래 이름."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_title = _font("Bold", 84)
    f_rule = _font("Medium", 42)
    _center(draw, 130, title, f_title)
    _center(draw, 250, rule, f_rule, fill=MUTED)

    grid_top, grid_bot = 360, CANVAS[1] - 170
    row_label_w = 90
    gx0, gx1 = 40 + row_label_w, CANVAS[0] - 40
    n_rows, n_cols = len(rows), 3
    gap = 14
    cw = (gx1 - gx0 - gap * (n_cols - 1)) // n_cols
    ch = (grid_bot - grid_top - gap * (n_rows - 1)) // n_rows
    f_row = _font("Bold", 64)
    f_name = _font("SemiBold", 34)
    f_col = _font("Bold", 36)

    for r, row in enumerate(rows):
        y0 = grid_top + r * (ch + gap)
        # 행 번호
        draw.text((44, y0 + ch // 2 - 40), f"{r + 1}", font=f_row, fill=GOLD)
        for c, cell in enumerate(row):
            x0 = gx0 + c * (cw + gap)
            tile = _photo_or_gradient(cell.get("photo_path"), cell.get("group", ""), (cw, ch))
            # 하단 이름 가독 그라디언트
            g = Image.new("L", (1, 110))
            for y in range(110):
                g.putpixel((0, y), int(220 * (y / 109)))
            a = g.resize((cw, 110))
            b = Image.new("RGB", (cw, 110), (5, 5, 10))
            tile.paste(b, (0, ch - 110), a)
            # 라운드 마스크
            mask = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw, ch], radius=22, fill=255)
            img.paste(tile, (x0, y0), mask)
            td = ImageDraw.Draw(img)
            # 열 번호 뱃지 (첫 행에만)
            if r == 0:
                td.text((x0 + 14, y0 + 10), f"{c + 1}", font=f_col, fill=GOLD,
                        stroke_width=4, stroke_fill=(5, 5, 10))
            name = cell.get("name", "")
            nw = td.textlength(name, font=f_name)
            td.text((x0 + (cw - nw) / 2, y0 + ch - 56), name, font=f_name, fill=INK)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_duo_card(num: int, group: str, members: List[dict], out: Path,
                  tagline: str = "") -> Path:
    """케미 투표 후보 카드 — 같은 그룹 2인 나란히. members[i] = {photo_path, name}."""
    img = _base()
    draw = ImageDraw.Draw(img)
    gc = GROUP_COLORS.get(group, DEFAULT_GROUP_COLOR)
    f_num = _font("Bold", 96)
    f_grp = _font("Bold", 66)
    f_name = _font("SemiBold", 48)
    f_tag = _font("Medium", 42)

    # 번호 원
    cx = CANVAS[0] // 2
    draw.ellipse([cx - 74, 130, cx + 74, 278], fill=gc)
    nw = draw.textlength(str(num), font=f_num)
    draw.text((cx - nw / 2, 148), str(num), font=f_num, fill=(255,) * 3)
    _center(draw, 320, group, f_grp, fill=gc)

    # 2인 사진 나란히
    pw, ph = 470, 940
    py = 470
    for i, m in enumerate(members[:2]):
        x0 = 45 + i * (pw + 50)
        tile = _photo_or_gradient(m.get("photo_path"), group, (pw, ph))
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw, ph], radius=30, fill=255)
        img.paste(tile, (x0, py), mask)
        d2 = ImageDraw.Draw(img)
        name = m.get("name", "")
        w = d2.textlength(name, font=f_name)
        d2.rounded_rectangle([x0 + (pw - w) / 2 - 22, py + ph + 18,
                              x0 + (pw + w) / 2 + 22, py + ph + 90],
                             radius=18, fill=(30, 28, 44))
        d2.text((x0 + (pw - w) / 2, py + ph + 28), name, font=f_name, fill=INK)
    if tagline:
        _center(draw, py + ph + 130, tagline, f_tag, fill=MUTED)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_result_bar_card(title: str, items: List[dict], out: Path,
                         sub: str = "") -> Path:
    """결과 카드 — items = [{label, pct, color?}] 상위부터. 가로 바."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_title = _font("Bold", 80)
    f_label = _font("SemiBold", 48)
    f_pct = _font("Bold", 52)
    f_sub = _font("Medium", 40)
    y = _center(draw, 160, title, f_title)
    if sub:
        y = _center(draw, y + 10, sub, f_sub, fill=MUTED)
    y += 70
    bar_x0, bar_x1 = 90, CANVAS[0] - 90
    bw = bar_x1 - bar_x0
    for i, it in enumerate(items):
        color = it.get("color") or (GOLD if i == 0 else ACCENT)
        pct = max(0.0, min(100.0, float(it["pct"])))
        draw.text((bar_x0, y), it["label"], font=f_label, fill=INK)
        pw = draw.textlength(f"{pct:.0f}%", font=f_pct)
        draw.text((bar_x1 - pw, y - 6), f"{pct:.0f}%", font=f_pct, fill=color)
        by = y + 78
        draw.rounded_rectangle([bar_x0, by, bar_x1, by + 46], radius=23, fill=BAR_BG)
        fill_w = int(bw * pct / 100)
        if fill_w > 46:
            draw.rounded_rectangle([bar_x0, by, bar_x0 + fill_w, by + 46], radius=23, fill=color)
        y = by + 130
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_cta_card(lines: List[str], out: Path, emphasis: str = "") -> Path:
    """마무리 참여 유도 카드. emphasis 는 골드 대형 라인."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_emp = _font("Bold", 96)
    f_line = _font("SemiBold", 54)
    total = (110 if emphasis else 0) + len(lines) * 78
    y = (CANVAS[1] - total) // 2 - 40
    if emphasis:
        y = _center(draw, y, emphasis, f_emp, fill=GOLD) + 30
    for ln in lines:
        y = _center(draw, y, ln, f_line) + 8
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_calendar_card(period: str, entries: list, out: Path,
                       disclaimer: str = "공식 발표 기준 · 일정은 변동될 수 있음") -> Path:
    """컴백 캘린더 리스트 카드 — 저장형 자산 (2026-W34 트렌드 스카우트 채택안 1번).
    entries[i] = {date:'YYYY-MM-DD', name, detail, kind}. 최대 8건/장."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_title = _font("Bold", 92)
    f_sub = _font("Medium", 40)
    f_date = _font("Bold", 46)
    f_name = _font("Bold", 56)
    f_detail = _font("Medium", 36)
    f_kind = _font("SemiBold", 30)
    f_disc = _font("Medium", 30)

    _center(draw, 140, "걸그룹 컴백 캘린더", f_title)
    _center(draw, 265, period, f_sub, fill=GOLD)

    y = 420
    row_h = 170
    for e in entries[:8]:
        mm, dd = e["date"][5:7], e["date"][8:10]
        # 날짜 배지
        draw.rounded_rectangle([70, y, 250, y + 110], radius=20,
                               fill=(30, 28, 44), outline=ACCENT, width=3)
        ds = f"{int(mm)}/{int(dd)}"
        w = draw.textlength(ds, font=f_date)
        draw.text((160 - w / 2, y + 30), ds, font=f_date, fill=INK)
        # 이름 + 상세
        draw.text((290, y), e["name"], font=f_name, fill=INK)
        draw.text((290, y + 70), e.get("detail", ""), font=f_detail, fill=MUTED)
        # 종류 태그 (데뷔/컴백/발매)
        kind = e.get("kind", "")
        if kind:
            kw = draw.textlength(kind, font=f_kind)
            kx = CANVAS[0] - 80 - kw
            color = ACCENT2 if kind == "데뷔" else ACCENT
            draw.rounded_rectangle([kx - 20, y + 8, kx + kw + 20, y + 62],
                                   radius=16, outline=color, width=3)
            draw.text((kx, y + 18), kind, font=f_kind, fill=INK)
        y += row_h

    _center(draw, CANVAS[1] - 210, disclaimer, f_disc, fill=MUTED)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_quiz_card(q_num: int, q_total: int, question: str, options: list,
                   out: Path, answer_idx: int = -1, countdown: str = "") -> Path:
    """상식 등급전 문항 카드 (스카우트 채택안 3번). answer_idx>=0 면 정답 리빌 버전
    (정답 옵션만 골드 하이라이트). options 는 4개."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_tag = _font("Medium", 40)
    f_q = _font("Bold", 62)
    f_opt = _font("SemiBold", 48)
    f_num = _font("Bold", 44)

    _center(draw, 150, f"Q{q_num}/{q_total}" + (f"  ·  {countdown}" if countdown else ""),
            f_tag, fill=MUTED)
    qy = 260
    for line in _wrap(draw, question, f_q, CANVAS[0] - 140)[:3]:
        qy = _center(draw, qy, line, f_q)

    y = max(qy + 60, 640)
    for i, opt in enumerate(options[:4]):
        is_answer = (i == answer_idx)
        color = GOLD if is_answer else (BAR_BG if answer_idx >= 0 else ACCENT)
        fill = (60, 52, 20) if is_answer else (26, 24, 38)
        draw.rounded_rectangle([90, y, CANVAS[0] - 90, y + 150], radius=26,
                               fill=fill, outline=color, width=4 if is_answer else 3)
        draw.ellipse([120, y + 45, 180, y + 105], fill=color)
        nw = draw.textlength(str(i + 1), font=f_num)
        draw.text((150 - nw / 2, y + 50), str(i + 1), font=f_num, fill=(20, 20, 25))
        tfill = GOLD if is_answer else (INK if answer_idx < 0 else MUTED)
        draw.text((215, y + 48), opt[:18], font=f_opt, fill=tfill)
        y += 185

    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def make_grade_card(out: Path) -> Path:
    """퀴즈 엔딩 등급 카드 — 맞은 개수 → 등급 안내."""
    img = _base()
    draw = ImageDraw.Draw(img)
    f_title = _font("Bold", 88)
    f_row = _font("SemiBold", 54)
    f_cta = _font("Medium", 44)
    _center(draw, 260, "몇 개 맞혔나요?", f_title)
    grades = [("0–1개", "뉴비", MUTED), ("2–3개", "라이트 팬", ACCENT),
              ("4개", "찐팬", ACCENT2), ("5개", "고인물 👑", GOLD)]
    y = 560
    for score, label, color in grades:
        draw.rounded_rectangle([120, y, CANVAS[0] - 120, y + 140], radius=26,
                               fill=(26, 24, 38), outline=color, width=3)
        draw.text((170, y + 42), score, font=f_row, fill=MUTED)
        w = draw.textlength(label, font=f_row)
        draw.text((CANVAS[0] - 170 - w, y + 42), label, font=f_row, fill=color)
        y += 175
    _center(draw, y + 40, "맞은 개수를 댓글로! (0~5)", f_cta, fill=GOLD)
    _brand_footer(draw)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out
