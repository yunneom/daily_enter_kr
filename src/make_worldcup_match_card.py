"""
걸그룹 월드컵 매치 카드 — 1080x1920 9:16. 게시글당 2매치 콤비 4지선다.

[레이아웃]
  상단: 🏆 걸그룹 월드컵 [라운드] · 게시글 N/M
  중상: 매치1 — 멤버A vs 멤버B (큰 카드 2개, VS 강조)
  중하: 매치2 — 멤버C vs 멤버D
  하단: 4지선다 (2x2 grid) — "1. A+C / 2. A+D / 3. B+C / 4. B+D"
        "💬 댓글에 번호로 투표 ⬇️"
  풋터: 출처 + brand

[디자인 톤]
브랜드평판 차트와 비슷한 다크 그라데이션 (네이비→마젠타). 빅매치 느낌.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)

# 색 — 빅매치 분위기
BG_TOP = (28, 22, 68)
BG_BOT = (78, 28, 96)
GOLD = (255, 220, 120)
RED = (236, 64, 102)
PINK = (255, 102, 184)
PINK_LIGHT = (255, 200, 224)
WHITE_DIM = (220, 215, 235)
CARD_BG = (255, 255, 255)
VS_RED = (220, 50, 90)


# 그룹 → 대표 emoji 매핑 (회사 IP 우회 + 시각 identity).
# 팬덤 commonly used 컬러/모티프 기반. 안 보이면 ✨ 폴백.
GROUP_EMOJI = {
    "아이브": "👑",            # IVE — queen
    "블랙핑크": "🖤",          # BP — black heart (🩷 핑크하트는 Twemoji 미지원 → 빈칸)
    "에스파": "🦋",            # aespa — synk butterfly
    "뉴진스": "🐰",            # NJ — bunny
    "리센느": "💎",            # Lisenne — diamond
    "아일릿": "🍓",            # ILLIT — strawberry
    "르세라핌": "🔥",          # LE SSERAFIM — fearless flame
    "엔믹스": "🎶",            # NMIXX — music mix
    "레드벨벳": "❤️",          # RV — red
    "트와이스": "✌️",          # TWICE — V sign
    "ITZY": "⚡",             # ITZY — energy
    "소녀시대": "⭐",          # SNSD — star
    "우주소녀": "🌙",          # WJSN — cosmos
    "시그니처": "🎼",          # tripleS — note
    "마마무": "🌈",            # MAMAMOO — rainbow
    "위키미키": "✏️",          # Weki Meki — sketch
    "프로미스나인": "💫",      # fromis_9 — sparkle
    "다이아": "💎",            # DIA — diamond
    "베이비몬스터": "👶",      # BabyMonster — baby
    "키스오브라이프": "💋",    # KISS OF LIFE — kiss
    "미야오": "🐱",            # MEOVV — cat
    "에이핑크": "🌸",          # Apink — sakura
    "오마이걸": "🌷",          # Oh My Girl — tulip
    "걸스데이": "👯",          # Girl's Day — twins
    "피프티피프티": "🎯",      # FIFTY FIFTY — target
    "트리플에스": "📐",        # tripleS — geometry
    "케플러": "🪐",            # Kep1er — planet
    "하츠투하츠": "💞",        # Hearts2Hearts — heart
}

def group_emoji_for(group: str) -> str:
    return GROUP_EMOJI.get(group, "✨")


# 그룹 → 영문 표기 ("IVE 장원영" 한 줄 표기용). 미등록 시 한글 그대로.
GROUP_EN = {
    "아이브": "IVE", "블랙핑크": "BLACKPINK", "에스파": "aespa", "뉴진스": "NewJeans",
    "리센느": "Lisenne", "아일릿": "ILLIT", "르세라핌": "LE SSERAFIM", "엔믹스": "NMIXX",
    "레드벨벳": "Red Velvet", "트와이스": "TWICE", "ITZY": "ITZY", "소녀시대": "SNSD",
    "우주소녀": "WJSN", "시그니처": "tripleS", "마마무": "MAMAMOO", "위키미키": "Weki Meki",
    "프로미스나인": "fromis_9", "다이아": "DIA", "베이비몬스터": "BABYMONSTER",
    "키스오브라이프": "KISS OF LIFE", "미야오": "MEOVV", "에이핑크": "Apink",
    "오마이걸": "OH MY GIRL", "걸스데이": "Girl's Day", "피프티피프티": "FIFTY FIFTY",
    "트리플에스": "tripleS", "케플러": "Kep1er", "하츠투하츠": "Hearts2Hearts",
    # 보이그룹 (향후 보이그룹 월드컵용)
    "스트레이키즈": "Stray Kids", "엔하이픈": "ENHYPEN", "TXT": "TXT", "RIIZE": "RIIZE",
    "ATEEZ": "ATEEZ", "제로베이스원": "ZB1",
}

def group_en_for(group: str) -> str:
    return GROUP_EN.get(group, group)


# 그룹 → 팬덤 시그니처 컬러 (카드 그라데이션). (top, bottom) RGB.
# 흰 글씨 가독 위해 중간~진한 채도. 미등록 시 기본 보라.
GROUP_COLOR = {
    "아이브": ((255, 90, 140), (200, 40, 110)),       # IVE — 핑크/마젠타
    "블랙핑크": ((255, 80, 160), (30, 30, 36)),        # BP — 핑크+블랙
    "에스파": ((40, 44, 60), (120, 30, 120)),          # aespa — 블랙+네온퍼플
    "뉴진스": ((120, 200, 255), (60, 130, 230)),       # NJ — 베이비블루
    "리센느": ((90, 160, 220), (40, 90, 170)),         # Lisenne — 블루
    "아일릿": ((255, 130, 170), (235, 90, 130)),       # ILLIT — 코랄핑크
    "르세라핌": ((60, 70, 90), (200, 60, 70)),         # LSRFM — 차콜+레드
    "엔믹스": ((90, 70, 200), (200, 60, 150)),         # NMIXX — 퍼플/마젠타
    "레드벨벳": ((230, 50, 70), (140, 20, 40)),        # RV — 레드
    "트와이스": ((255, 120, 170), (250, 80, 90)),      # TWICE — 핑크/애프리콧
    "ITZY": ((255, 70, 90), (230, 30, 60)),            # ITZY — 레드
    "소녀시대": ((255, 160, 190), (230, 110, 150)),    # SNSD — 파스텔로즈
    "우주소녀": ((120, 90, 210), (70, 50, 160)),       # WJSN — 퍼플
    "시그니처": ((90, 100, 120), (50, 55, 75)),        # tripleS — 그레이블루
    "마마무": ((255, 140, 60), (220, 90, 40)),         # MAMAMOO — 오렌지
    "위키미키": ((255, 110, 150), (220, 70, 120)),     # WM — 핑크
    "프로미스나인": ((90, 170, 230), (130, 90, 220)),  # fromis — 블루퍼플
    "다이아": ((110, 180, 220), (70, 130, 190)),       # DIA — 블루
    "베이비몬스터": ((60, 60, 70), (200, 50, 60)),     # BM — 블랙레드
    "키스오브라이프": ((230, 60, 110), (160, 30, 80)), # KIOF — 로즈
    "미야오": ((255, 100, 130), (210, 50, 90)),        # MEOVV — 핑크
    "에이핑크": ((255, 150, 180), (240, 110, 150)),    # Apink — 핑크
    "오마이걸": ((255, 160, 120), (230, 110, 150)),    # OMG — 코랄
    "걸스데이": ((255, 140, 160), (220, 90, 120)),     # GD — 핑크
    "피프티피프티": ((130, 110, 210), (80, 70, 170)),  # FF — 퍼플
    "트리플에스": ((90, 100, 120), (50, 55, 75)),
    "케플러": ((150, 110, 220), (90, 70, 180)),        # Kep1er — 퍼플
    "하츠투하츠": ((255, 120, 150), (230, 80, 120)),   # H2H — 핑크
}

def group_color_for(group: str):
    return GROUP_COLOR.get(group, ((90, 60, 150), (50, 30, 100)))


def _font(weight: str, size: int):
    p = _resolve_font(weight)
    return ImageFont.truetype(p, size)


def _vgrad(size, top, bot):
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


def _draw_centered(draw, text, font, cx, y, fill=WHITE, stroke=0, stroke_fill=None):
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kw = dict(font=font, fill=fill)
    if stroke:
        kw["stroke_width"] = stroke
        kw["stroke_fill"] = stroke_fill or INK
    draw.text((cx - w / 2, y), text, **kw)


def _circle_photo(path: str, size: int) -> Optional[Image.Image]:
    """사진 → 정사각 center-crop → 원형 마스크. 실패 시 None."""
    try:
        from PIL import ImageDraw as _ID
        ph = Image.open(path).convert("RGB")
        pw, phh = ph.size
        s = min(pw, phh)
        ph = ph.crop(((pw - s) // 2, (phh - s) // 2,
                      (pw - s) // 2 + s, (phh - s) // 2 + s)).resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        _ID.Draw(mask).ellipse([0, 0, size, size], fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(ph, (0, 0), mask)
        return out
    except Exception:
        return None


def _rounded_grad(w: int, h: int, top, bot, radius: int = 24) -> Image.Image:
    """그룹 시그니처 컬러 그라데이션 + 둥근 모서리 RGBA 카드."""
    grad = _vgrad((w, h), top, bot).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def _member_card(img: Image.Image, x: int, y: int, w: int, h: int,
                 member: Dict):
    """단일 멤버 카드 — 그룹 시그니처 컬러 그라데이션 + 큰 emoji +
    'IVE 장원영' 한 줄 표기(그룹영문+이름) + BR 순위 배지.
    (실사 사진은 IDOL_PHOTOS=on 일 때만, 기본 off)."""
    grp = member.get("group", "")
    name = member.get("member", "")
    top, bot = group_color_for(grp)
    # 시그니처 컬러 그라데이션 카드 + 금 테두리
    card = _rounded_grad(w, h, top, bot)
    img.alpha_composite(card, (x, y))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=24,
                        outline=GOLD, width=4)

    # (옵션) 실사 사진 — 기본 off
    photo_done = False
    if os.environ.get("IDOL_PHOTOS", "off").lower() == "on":
        try:
            import idol_photo
            rec = idol_photo.fetch_photo(name)
            if rec and rec.get("path"):
                circ = _circle_photo(rec["path"], 150)
                if circ:
                    d.ellipse([x + (w - 158) // 2, y + 22,
                               x + (w - 158) // 2 + 158, y + 22 + 158],
                              outline=WHITE, width=4)
                    img.alpha_composite(circ, (x + (w - 150) // 2, y + 26))
                    photo_done = True
        except Exception:
            pass
    # 폴백/기본 — 큰 그룹 emoji (불투명 흰 원 배경 위 → 모든 emoji 가독)
    if not photo_done:
        cx = x + w // 2
        # 반투명→거의 불투명 흰 원 (블랙핑크 🩷 등 옅은 emoji 도 선명하게)
        disc = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(disc).ellipse([w // 2 - 88, 24, w // 2 + 88, 24 + 176],
                                     fill=(255, 255, 255, 235), outline=(255, 255, 255, 255), width=3)
        img.alpha_composite(disc, (x, y))
        em = _get_emoji_image(group_emoji_for(grp), 150)
        if em:
            img.alpha_composite(em, (cx - 75, y + 38))

    # "IVE 장원영" — 흰 라운드 박스 위 검정 글씨 (집중 ↑). 그룹+이름 같은 폰트/크기.
    cx = x + w // 2
    grp_en = group_en_for(grp)
    one_line = f"{grp_en} {name}"
    def _tw(s, f): bb = f.getbbox(s); return bb[2] - bb[0]
    box_x0, box_x1 = x + 12, x + w - 12
    box_inner = (box_x1 - box_x0) - 24  # 박스 안쪽 텍스트 가용폭
    # 한 줄 시도
    size = 54; nf = _font("Bold", size)
    while _tw(one_line, nf) > box_inner and size > 34:
        size -= 2; nf = _font("Bold", size)
    if _tw(one_line, nf) <= box_inner:
        lines = [one_line]
    else:
        # 2줄 (그룹 / 이름)
        size = 50; nf = _font("Bold", size)
        while max(_tw(grp_en, nf), _tw(name, nf)) > box_inner and size > 30:
            size -= 2; nf = _font("Bold", size)
        lines = [grp_en, name]
    # 흰 박스 (이름 영역 배경)
    pad_y = 12
    box_h = len(lines) * size + (len(lines) - 1) * 6 + pad_y * 2
    box_y0 = y + 206
    d.rounded_rectangle([box_x0, box_y0, box_x1, box_y0 + box_h],
                        radius=16, fill=(255, 255, 255), outline=GOLD, width=2)
    ty = box_y0 + pad_y
    for ln in lines:
        d.text((cx - _tw(ln, nf) / 2, ty), ln, font=nf, fill=INK)
        ty += size + 6

    # BR 순위 배지 (좌상단, 골드)
    rk = member.get("rank")
    if rk:
        rf = _font("Bold", 26)
        rstr = f"BR {rk}위"
        rbb = rf.getbbox(rstr); rw = rbb[2] - rbb[0]
        d.rounded_rectangle([x + 14, y + 14, x + 14 + rw + 28, y + 14 + 44],
                            radius=12, fill=GOLD)
        d.text((x + 14 + 14, y + 14 + 6), rstr, font=rf, fill=INK)


def _match_block(img: Image.Image, x0: int, y0: int, width: int,
                 match_idx: int, a: Dict, b: Dict):
    """매치 1개 — 두 멤버 카드 + 중앙 VS. 인물 번호 X (4지선다와 분리)."""
    d = ImageDraw.Draw(img)
    # 매치 라벨
    lf = _font("Bold", 36)
    lbl = f"매치 {match_idx}"
    bb = lf.getbbox(lbl)
    lw = bb[2] - bb[0]
    # 배경 캡슐
    cap_x = x0 + (width - lw - 40) // 2
    d.rounded_rectangle([cap_x, y0, cap_x + lw + 40, y0 + 50],
                        radius=24, fill=PINK)
    d.text((cap_x + 20, y0 + 5), lbl, font=lf, fill=WHITE)

    # 멤버 카드 2개 + 중앙 VS
    card_y = y0 + 70
    card_h = 380
    gap = 24
    vs_w = 100
    card_w = (width - vs_w - 2 * gap) // 2
    left_x = x0
    right_x = x0 + card_w + gap + vs_w + gap

    _member_card(img, left_x, card_y, card_w, card_h, a)
    _member_card(img, right_x, card_y, card_w, card_h, b)

    # VS 텍스트 (중앙)
    vsf = _font("Bold", 120)
    vs_text = "VS"
    bb = vsf.getbbox(vs_text)
    vw = bb[2] - bb[0]
    vh = bb[3] - bb[1]
    vs_cx = x0 + card_w + gap + vs_w // 2
    vs_cy = card_y + card_h // 2
    d.text((vs_cx - vw / 2, vs_cy - vh / 2 - 18), vs_text,
           font=vsf, fill=VS_RED, stroke_width=4, stroke_fill=WHITE)


def _choice_grid(img: Image.Image, y_start: int,
                 a: Dict, b: Dict, c: Dict, d_m: Dict):
    """하단 4지선다 grid 2x2 — 콤비네이션 카드.
    1: A+C / 2: A+D / 3: B+C / 4: B+D
    """
    draw = ImageDraw.Draw(img)
    # 헤더
    hf = _font("Bold", 48)
    _draw_centered(draw, "💬 댓글에 번호로 투표 ⬇️", hf,
                   CANVAS[0] // 2, y_start, fill=WHITE,
                   stroke=2, stroke_fill=INK)

    combos = [
        (1, a, c),
        (2, a, d_m),
        (3, b, c),
        (4, b, d_m),
    ]
    grid_top = y_start + 70
    cell_w = 480
    cell_h = 110
    gap_x = 24
    gap_y = 18
    grid_x0 = (CANVAS[0] - 2 * cell_w - gap_x) // 2

    cf_num = _font("Bold", 64)
    cf_txt = _font("Bold", 36)

    for i, (n, m1, m2) in enumerate(combos):
        r = i // 2
        c = i % 2
        x = grid_x0 + c * (cell_w + gap_x)
        y = grid_top + r * (cell_h + gap_y)
        # 박스
        draw.rounded_rectangle([x, y, x + cell_w, y + cell_h],
                               radius=20, fill=CARD_BG,
                               outline=PINK, width=4)
        # 번호 배지
        d_ = ImageDraw.Draw(img)
        d_.ellipse([x + 12, y + 18, x + 12 + 74, y + 18 + 74], fill=RED)
        ns = str(n)
        bb = cf_num.getbbox(ns)
        nw = bb[2] - bb[0]
        d_.text((x + 12 + 37 - nw / 2 - 2, y + 22), ns,
                font=cf_num, fill=WHITE)
        # 콤비 텍스트 — "장원영 + 카리나"
        txt = f"{m1['member']} + {m2['member']}"
        bb = cf_txt.getbbox(txt)
        tw = bb[2] - bb[0]
        # 너비 초과 시 폰트 다운
        if tw > cell_w - 110:
            cf_txt2 = _font("Bold", 28)
            bb = cf_txt2.getbbox(txt)
            tw = bb[2] - bb[0]
            d_.text((x + 100 + (cell_w - 110 - tw) / 2, y + 38),
                    txt, font=cf_txt2, fill=INK)
        else:
            d_.text((x + 100 + (cell_w - 110 - tw) / 2, y + 30),
                    txt, font=cf_txt, fill=INK)


def make_worldcup_match_card(
    round_label: str,            # "32강" / "16강" ...
    post_index: int,             # 1-based
    post_total: int,
    match1: Dict,                # {"a": {rank,group,member}, "b": {...}}
    match2: Dict,
    output_path: Path,
    source_note: str = "출처: 한국기업평판연구소 2026.6.21",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
) -> Path:
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # === 헤더 ===
    title_f = _font("Bold", 80)
    sub_f = _font("Bold", 42)
    trophy = "🏆"
    em = _get_emoji_image(trophy, 80)
    title_text = f"걸그룹 월드컵 {round_label}"
    bb = title_f.getbbox(title_text)
    tw = bb[2] - bb[0]
    # 트로피 이모지 + 텍스트 중앙 정렬
    total_w = 90 + tw
    start_x = (CANVAS[0] - total_w) // 2
    if em:
        img.alpha_composite(em, (start_x, 56))
    d.text((start_x + 90, 56), title_text, font=title_f, fill=GOLD,
           stroke_width=3, stroke_fill=INK)

    # 게시글 인덱스
    sub_text = f"게시글 {post_index} / {post_total}"
    _draw_centered(d, sub_text, sub_f, CANVAS[0] // 2, 170,
                   fill=WHITE_DIM)

    # === 매치 1 ===
    _match_block(img, 30, 245, CANVAS[0] - 60, 1,
                 match1["a"], match1["b"])

    # === 매치 2 ===
    _match_block(img, 30, 765, CANVAS[0] - 60, 2,
                 match2["a"], match2["b"])

    # === 4지선다 ===
    _choice_grid(img, 1310, match1["a"], match1["b"],
                 match2["a"], match2["b"])

    # === 풋터 ===
    d = ImageDraw.Draw(img)
    sf = _font("Medium", 26)
    _draw_centered(d, source_note, sf, CANVAS[0] // 2, 1820,
                   fill=WHITE_DIM)
    _draw_centered(d, brand, sf, CANVAS[0] // 2, 1862,
                   fill=(190, 180, 215))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    import json
    ROOT = Path(__file__).parent.parent
    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    posts = bracket["rounds"]["R32"]["posts"]
    out_dir = ROOT / "output_enter" / "publish" / "worldcup_r32"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 샘플: 게시글 1
    p = posts[0]
    out = out_dir / f"post_{p['post_idx']+1:02d}.jpg"
    make_worldcup_match_card(
        round_label="32강",
        post_index=p["post_idx"] + 1,
        post_total=len(posts),
        match1=p["match1"], match2=p["match2"],
        output_path=out,
    )
    print(f"✓ {out} ({out.stat().st_size // 1024} KB)")
