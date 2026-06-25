"""
메시지 카드 — 육성/권위/전환 콘텐츠 공용 렌더러 (게임 매트릭스 아닌 텍스트형).

3-1-2-1 콘텐츠 믹스에서 부족했던 카테고리를 채우는 카드:
- 육성(nurture): 운영자 한마디 / 이번주 커뮤니티 하이라이트 → 친밀함·인간미
- 권위(authority): K-연예 인사이트 / 데이터 → 전문가 신뢰
- 전환(conversion): 추천템 / 참여 유도 → 행동

[디자인] 1080x1920. 상단 배지 + 큰 헤드라인 + 부제 + 본문 bullet + 하단 CTA 박스.
카테고리별 accent 컬러로 시각 구분.
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image


CANVAS = (1080, 1920)
INK = (28, 28, 36)
WHITE = (255, 255, 255)

# 카테고리별 (accent, bg_top, bg_bot)
CATEGORY_THEME = {
    "nurture":   ((255, 126, 182), (255, 244, 250), (255, 224, 238)),  # 핑크 — 친근
    "authority": ((70, 110, 220), (238, 244, 255), (214, 228, 250)),   # 블루 — 신뢰
    "conversion":((245, 158, 30), (255, 248, 232), (255, 232, 198)),   # 골드 — 행동
}


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


def _wrap(text, font, max_w, draw):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_message_card(
    category: str,            # nurture | authority | conversion
    badge: str,              # "💬 이번주 우리 채널"
    headline: str,           # 큰 제목
    lines: List[str],        # 본문 (각 줄 = bullet)
    cta: str,                # 하단 CTA
    output_path: Path,
    subhead: str = "",
    source_note: str = "",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
) -> Path:
    accent, bg_top, bg_bot = CATEGORY_THEME.get(category, CATEGORY_THEME["authority"])
    img = _vgrad(CANVAS, bg_top, bg_bot).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 상단 배지 (accent 캡슐)
    bf = _font("Bold", 44)
    bw = d.textlength(badge, font=bf)
    cap_w = bw + 64
    cx = CANVAS[0] // 2
    d.rounded_rectangle([cx - cap_w / 2, 110, cx + cap_w / 2, 188],
                        radius=39, fill=accent)
    d.text((cx - bw / 2, 124), badge, font=bf, fill=WHITE)

    # 헤드라인 (wrap, 큰 볼드)
    hf = _font("Bold", 92)
    hlines = _wrap(headline, hf, CANVAS[0] - 120, d)
    y = 260
    for ln in hlines:
        lw = d.textlength(ln, font=hf)
        d.text((cx - lw / 2, y), ln, font=hf, fill=INK)
        y += 104
    y += 10

    # 부제
    if subhead:
        sf = _font("Medium", 42)
        for ln in _wrap(subhead, sf, CANVAS[0] - 140, d):
            lw = d.textlength(ln, font=sf)
            d.text((cx - lw / 2, y), ln, font=sf, fill=(110, 110, 120))
            y += 54
    y += 30

    # 본문 bullet (좌측 accent 점 + 텍스트)
    lf = _font("SemiBold", 50)
    sub_f = _font("Medium", 38)
    bx = 110
    for item in lines:
        # "헤드 | 설명" 형식이면 2단
        if "|" in item:
            head, desc = [s.strip() for s in item.split("|", 1)]
        else:
            head, desc = item, ""
        d.ellipse([bx, y + 16, bx + 22, y + 38], fill=accent)
        d.text((bx + 44, y), head, font=lf, fill=INK)
        y += 62
        if desc:
            for ln in _wrap(desc, sub_f, CANVAS[0] - bx - 90, d):
                d.text((bx + 44, y), ln, font=sub_f, fill=(110, 110, 120))
                y += 48
        y += 26

    # 하단 CTA 박스 (accent 배경)
    cta_f = _font("Bold", 52)
    box_y0 = 1640
    d.rounded_rectangle([60, box_y0, CANVAS[0] - 60, box_y0 + 150],
                        radius=28, fill=accent)
    clines = _wrap(cta, cta_f, CANVAS[0] - 200, d)
    cy = box_y0 + (150 - len(clines) * 60) // 2
    for ln in clines:
        lw = d.textlength(ln, font=cta_f)
        d.text((cx - lw / 2, cy), ln, font=cta_f, fill=WHITE,
               stroke_width=1, stroke_fill=(120, 60, 30) if category == "conversion" else (80, 40, 90))
        cy += 60

    # 풋터
    ff = _font("Medium", 26)
    if source_note:
        sw = d.textlength(source_note, font=ff)
        d.text((cx - sw / 2, 1822), source_note, font=ff, fill=(140, 140, 150))
    bw2 = d.textlength(brand, font=ff)
    d.text((cx - bw2 / 2, 1862), brand, font=ff, fill=(150, 150, 160))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "output_enter" / "showcase" / "msg"
    make_message_card(
        "nurture", "💬 이번주 우리 채널",
        "이번주 가장 사랑받은 픽은?",
        ["장원영 | 16강 매치에서 댓글 800개 돌파",
         "카리나 vs 카즈하 | 역대급 접전, 5표 차",
         "여러분 덕분에 | 월드컵 참여 매일 신기록"],
        "💬 다음 픽도 댓글로 함께 만들어요!",
        out / "nurture.jpg",
        subhead="여러분의 댓글이 다음 라운드를 정합니다")
    print("✓ nurture sample")
