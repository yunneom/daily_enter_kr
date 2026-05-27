"""
카드뉴스 이미지 생성 — 미니멀 디자인.

순백 배경 + 검정 제목 한 줄(또는 자동 줄바꿈)만. 랭크/출처/채널 라벨/배경 이미지 모두 제거.
"제목만으로 설명" 컨셉. 시각 위계는 폰트 크기/굵기/공간으로만 표현.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Tuple, List


# === 디자인 토큰 (단일 미니멀 스타일) ===
BG_COLOR = (255, 255, 255)        # 순백
TEXT_COLOR = (17, 17, 17)         # 거의 검정 (#111)
SUBTLE_COLOR = (170, 170, 170)    # 옅은 회색 (cover 날짜용)

CARD_SIZE = (1080, 1080)
SIDE_MARGIN = 110                 # 좌우 여백

# 시스템 한글 폰트 자동 탐색 후보 (대부분 Bold/Heavy 자체가 미니멀 룩에 어울림)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]


def _resolve_font(font_path: str = None) -> str:
    """첫 번째로 존재하는 폰트 경로 반환. 못 찾으면 None → load_default 폴백."""
    for c in [font_path] + FONT_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """글자 단위 줄바꿈 (한글이라 공백 단위 wrap이 부정확함)."""
    lines = []
    current = ""
    for ch in text:
        bbox = font.getbbox(current + ch)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = current + ch
    if current:
        lines.append(current)
    return lines


def _fit_title(
    text: str,
    font_path: str,
    max_width: int,
    max_lines: int = 4,
    size_max: int = 110,
    size_min: int = 56,
) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
    """제목 길이에 따라 폰트 크기 자동 조정 — max_lines 안에 들어오는 가장 큰 사이즈 선택."""
    if not font_path:
        f = ImageFont.load_default()
        return f, _wrap_text(text, f, max_width)
    for size in range(size_max, size_min - 1, -6):
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_text(text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = ImageFont.truetype(font_path, size_min)
    return font, _wrap_text(text, font, max_width)


def _draw_centered(draw, y: int, text: str, font: ImageFont.FreeTypeFont,
                   canvas_w: int, fill=TEXT_COLOR):
    bbox = font.getbbox(text)
    line_w = bbox[2] - bbox[0]
    draw.text(((canvas_w - line_w) // 2, y), text, font=font, fill=fill)


def make_card(
    title: str,
    output_path: Path,
    font_path: str = None,
    size: Tuple[int, int] = CARD_SIZE,
):
    """본문 카드 — 흰 배경 위 검정 제목 중앙 정렬."""
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    resolved = _resolve_font(font_path)
    font, lines = _fit_title(title, resolved, max_width=size[0] - SIDE_MARGIN * 2)

    # 줄 높이 = ascent+descent + 25% 행간
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (60, 12)
    line_height = int((ascent + descent) * 1.25)
    block_h = line_height * len(lines)
    y0 = (size[1] - block_h) // 2

    for i, line in enumerate(lines):
        _draw_centered(draw, y0 + i * line_height, line, font, size[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_cover_card(
    date_str: str,
    output_path: Path,
    label_short: str = "K-연예",
    total_cards: int = None,
    font_path: str = None,
    size: Tuple[int, int] = CARD_SIZE,
):
    """표지 — '오늘의 / {label_short} / TOP N' + 날짜. 동일 미니멀 룩 유지."""
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    resolved = _resolve_font(font_path)
    if resolved:
        f_big = ImageFont.truetype(resolved, 140)
        f_mid = ImageFont.truetype(resolved, 70)
        f_date = ImageFont.truetype(resolved, 40)
    else:
        f_big = f_mid = f_date = ImageFont.load_default()

    rank_label = f"TOP {total_cards}" if total_cards and total_cards > 0 else "HOT NEWS"

    _draw_centered(draw, 320, "오늘의", f_mid, size[0])
    _draw_centered(draw, 420, label_short, f_big, size[0])
    _draw_centered(draw, 620, rank_label, f_big, size[0])
    _draw_centered(draw, 840, date_str, f_date, size[0], fill=SUBTLE_COLOR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


if __name__ == "__main__":
    from datetime import datetime

    output_dir = Path(__file__).parent.parent / "output" / "sample"
    output_dir.mkdir(parents=True, exist_ok=True)

    make_cover_card(
        date_str=datetime.now().strftime("%Y년 %m월 %d일"),
        output_path=output_dir / "00_cover.jpg",
        label_short="K-연예",
        total_cards=5,
    )
    print(f"✅ 표지: {output_dir / '00_cover.jpg'}")

    samples = [
        "아이브 새 앨범 티저 공개",
        "지드래곤, 월드투어 8개 도시 추가",
        "뉴진스 컴백, 음악 방송 1위",
        "박찬욱 감독 신작, 칸 출품 확정",
        "유재석, 신규 예능 진행 합류",
    ]
    for i, title in enumerate(samples, 1):
        path = output_dir / f"{i:02d}_card.jpg"
        make_card(title, path)
        print(f"✅ {i:02d}: {title}")

    print(f"\n총 {len(samples) + 1}개 이미지 생성")
    print(f"출력 폴더: {output_dir}")
