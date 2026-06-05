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

CARD_SIZE = (1080, 1920)          # 9:16 (Reels/Stories 표준)
SIDE_MARGIN = 110                 # 좌우 여백

# Pretendard (한국 모던 디자인의 사실상 표준) 우선, 시스템 Noto 폴백.
# weight 별로 다른 파일을 쓰므로 dict 로 관리.
_PRETENDARD_DIRS = [
    "/usr/share/fonts/truetype/pretendard",
    "/usr/share/fonts/opentype/pretendard",  # 워크플로우 설치 위치 후보
]
_NOTO_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_NOTO_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def _find_pretendard(weight: str) -> str:
    for d in _PRETENDARD_DIRS:
        p = Path(d) / f"Pretendard-{weight}.otf"
        if p.exists():
            return str(p)
    return None


def _resolve_font(weight: str = "Bold", font_path: str = None) -> str:
    """가중치별 폰트 경로 — Pretendard 우선, 없으면 Noto Sans CJK.
    weight: 'Bold' | 'SemiBold' | 'Medium' | 'Regular'
    """
    if font_path and Path(font_path).exists():
        return font_path
    p = _find_pretendard(weight)
    if p:
        return p
    # Noto 폴백 (가중치는 Bold/Regular 두 단계만)
    if weight in ("Bold", "SemiBold") and Path(_NOTO_BOLD).exists():
        return _NOTO_BOLD
    if Path(_NOTO_REGULAR).exists():
        return _NOTO_REGULAR
    # 마지막 폴백 — 시스템 어디든
    legacy = [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
    ]
    for c in legacy:
        if Path(c).exists():
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
    size_max: int = 140,
    size_min: int = 44,
) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
    """제목 자동 fit — 한 줄 우선, 안 들어가면 두 줄 wrap. 트렁케이트 없음.

    알고리즘 (size_max → size_min 으로 폰트 줄여가며):
      1. 현재 크기로 한 줄에 들어가면 → (font, [text])
      2. 두 줄에 정확히 들어가면 → (font, [line1, line2])
      3. 둘 다 아니면 다음 더 작은 크기 시도
    size_min 까지 가도 두 줄로 못 담으면 size_min 으로 wrap 한 결과 그대로 반환
    (3줄 이상이 될 수도 있지만, 보통 22자 가이드 범위 내에선 발생 안 함).
    """
    if not font_path:
        f = ImageFont.load_default()
        return f, [text]
    for size in range(size_max, size_min - 1, -2):
        font = ImageFont.truetype(font_path, size)
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return font, [text]
        lines = _wrap_text(text, font, max_width)
        if len(lines) <= 2:
            return font, lines
    # 폴백: size_min 에서 wrap (트렁케이트 안 함 — 매우 드문 케이스)
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
    """본문 카드 — 흰 배경 + 검정 제목(중앙 정렬). 1줄 우선, 안 들어가면 2줄.

    제목은 Pretendard SemiBold 사용 — Bold 보다 살짝 가벼워서 영상에서 덜 딱딱해 보임.
    """
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    resolved = _resolve_font(weight="SemiBold", font_path=font_path)
    font, lines = _fit_title(
        title, resolved, max_width=size[0] - SIDE_MARGIN * 2,
    )

    # 줄 단위 중앙 정렬 — 행간은 ascent+descent × 1.15 (느슨하지 않게 빼곡)
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (60, 12)
    line_h = int((ascent + descent) * 1.15)
    block_h = line_h * len(lines) - int(line_h * 0.15)  # 마지막 줄 아래엔 행간 공백 빼기
    y = (size[1] - block_h) // 2
    for line in lines:
        _draw_centered(draw, y, line, font, size[0])
        y += line_h

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_sources_card(
    sources: List[str],
    output_path: Path,
    font_path: str = None,
    size: Tuple[int, int] = CARD_SIZE,
):
    """출처 카드 — '출처' 라벨 + 고유 출처 리스트 (중앙 정렬, 검정/회색)."""
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 라벨(SemiBold 84) + 항목(Medium 58) — 가중치 분리로 위계 만들기
    label_font_path = _resolve_font(weight="SemiBold", font_path=font_path)
    item_font_path = _resolve_font(weight="Medium", font_path=font_path)
    if label_font_path and item_font_path:
        f_label = ImageFont.truetype(label_font_path, 84)
        f_item = ImageFont.truetype(item_font_path, 58)
    else:
        f_label = f_item = ImageFont.load_default()

    # 중복 제거하되 순서 보존
    seen = set()
    unique = []
    for s in sources:
        if s and s not in seen:
            seen.add(s)
            unique.append(s)

    # 라벨 + 빈 줄 + 출처들 — 전체 블록을 수직 중앙 정렬
    label_h = f_label.getbbox("출처")[3]
    item_h = int(f_item.getbbox("가")[3] * 1.7)  # 행간 1.7
    gap_after_label = 60
    block_h = label_h + gap_after_label + item_h * len(unique)
    y = (size[1] - block_h) // 2

    _draw_centered(draw, y, "출처", f_label, size[0], fill=SUBTLE_COLOR)
    y += label_h + gap_after_label
    for src in unique:
        _draw_centered(draw, y, src, f_item, size[0])
        y += item_h

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_cover_card(
    date_str: str,
    output_path: Path,
    cover_label: str = "연예",
    total_cards: int = None,
    font_path: str = None,
    size: Tuple[int, int] = CARD_SIZE,
):
    """표지 — '{cover_label} TOP N' 한 줄 + 날짜. 영상 맨 앞에 들어가는 1.5초 카드.

    이전 디자인의 '오늘의 / K-연예 / TOP N' 3단 → '연예 TOP 8' 한 줄로 단순화.
    Reels 첫 1.5초에 즉시 컨텍스트 전달 → 시청자 retention ↑.
    """
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    bold_path = _resolve_font(weight="Bold", font_path=font_path)
    regular_path = _resolve_font(weight="Regular", font_path=font_path)
    if not bold_path:
        bold_path = regular_path

    n = total_cards if total_cards and total_cards > 0 else 8
    headline = f"{cover_label} TOP {n}"

    # 헤드라인 크기는 가로폭에 맞춰 자동. 글자 수가 많아질 채널(스포츠 TOP 10 등) 대비
    max_w = size[0] - SIDE_MARGIN * 2
    for hsize in range(220, 120 - 1, -4):
        f_big = ImageFont.truetype(bold_path, hsize)
        if f_big.getbbox(headline)[2] <= max_w:
            break
    f_date = ImageFont.truetype(regular_path, 48)

    # 헤드라인은 수직 중앙보다 살짝 위(y=820), 날짜는 하단 안전영역(y=1180)
    h_bbox = f_big.getbbox(headline)
    h_h = h_bbox[3] - h_bbox[1]
    _draw_centered(draw, (size[1] - h_h) // 2 - 40, headline, f_big, size[0])
    _draw_centered(draw, size[1] // 2 + h_h // 2 + 80, date_str, f_date, size[0], fill=SUBTLE_COLOR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_reels_thumbnail(
    top_titles: List[str],
    output_path: Path,
    accent_color: Tuple[int, int, int] = (255, 230, 0),  # 노란 포인트 (브랜드 accent)
    font_path: str = None,
    size: Tuple[int, int] = CARD_SIZE,
):
    """Reels 피드 그리드용 커스텀 썸네일 — IG cover_url 로 전달.

    프로필 그리드(1080px 가로)에서 보이는 첫 인상. 첫 카드(헤드라인 1번)와 다른
    디자인이어야 의미 있음. 강한 컬러 블록 + TOP 1-2 헤드라인 큰 글자.

    Args:
        top_titles: 상위 1-3개 헤드라인 (1-2개만 노출됨)
        accent_color: 상단 컬러 바 색 (브랜드 accent)
    """
    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 상단 noticeable 컬러 바 (약 size[1]*0.18 높이) — 그리드에서 즉시 인지
    bar_h = int(size[1] * 0.18)
    draw.rectangle([(0, 0), (size[0], bar_h)], fill=accent_color)

    bold = _resolve_font(weight="Bold", font_path=font_path)
    semi = _resolve_font(weight="SemiBold", font_path=font_path)
    medium = _resolve_font(weight="Medium", font_path=font_path)
    regular = _resolve_font(weight="Regular", font_path=font_path)

    # 컬러 바 위에 'TODAY'/'오늘' 라벨 (검정 텍스트)
    f_brand = ImageFont.truetype(bold, 96) if bold else ImageFont.load_default()
    label = "오늘의 핫이슈"
    bbox = f_brand.getbbox(label)
    label_w = bbox[2] - bbox[0]
    draw.text(((size[0] - label_w) // 2, (bar_h - (bbox[3] - bbox[1])) // 2 - 10),
              label, font=f_brand, fill=(17, 17, 17))

    # 본문 — 상위 1-2 헤드라인 (큰 글자, 자동 wrap)
    main_y = bar_h + 100
    available_h = size[1] - bar_h - 200  # 하단 200px 여백
    max_w = size[0] - SIDE_MARGIN * 2

    show_n = min(2, len(top_titles))
    block_titles = top_titles[:show_n]

    # 두 줄 wrap 가능하도록 폰트 사이즈 자동 조정 — 단일 제목당 최대 2줄
    sized = []
    for t in block_titles:
        for s in range(120, 60 - 1, -4):
            f = ImageFont.truetype(semi, s)
            lines = _wrap_text(t, f, max_w)
            if len(lines) <= 2:
                sized.append((f, lines, int((f.getmetrics()[0] + f.getmetrics()[1]) * 1.15)))
                break
        else:
            f = ImageFont.truetype(semi, 60)
            sized.append((f, _wrap_text(t, f, max_w)[:2],
                          int((f.getmetrics()[0] + f.getmetrics()[1]) * 1.15)))

    # 블록 총 높이
    total = sum(lh * len(lines) for _, lines, lh in sized)
    gap = 60  # 두 제목 사이 간격
    if show_n > 1:
        total += gap * (show_n - 1)
    y = main_y + (available_h - total) // 2

    for idx, (f, lines, lh) in enumerate(sized):
        # 번호 표시 (작은 회색 라벨)
        f_num = ImageFont.truetype(medium, 36) if medium else f
        num_label = f"#{idx+1}"
        num_bbox = f_num.getbbox(num_label)
        num_w = num_bbox[2] - num_bbox[0]
        draw.text(((size[0] - num_w) // 2, y), num_label, font=f_num, fill=SUBTLE_COLOR)
        y += int(lh * 0.55)
        for line in lines:
            bbox = f.getbbox(line)
            line_w = bbox[2] - bbox[0]
            draw.text(((size[0] - line_w) // 2, y), line, font=f, fill=TEXT_COLOR)
            y += lh
        if idx < show_n - 1:
            y += gap

    # 하단 brand line
    f_brand_sm = ImageFont.truetype(regular, 38) if regular else f_brand
    brand = "@daily_enter_kr · 매일 아침 8시"
    bbox = f_brand_sm.getbbox(brand)
    brand_w = bbox[2] - bbox[0]
    draw.text(((size[0] - brand_w) // 2, size[1] - 90), brand,
              font=f_brand_sm, fill=SUBTLE_COLOR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


if __name__ == "__main__":
    from datetime import datetime

    output_dir = Path(__file__).parent.parent / "output" / "sample"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 슬라이드 순서: 본문 N장 → 출처 (표지 제거됨)
    samples = [
        ("아이브 새 앨범 티저 공개", "스포츠동아"),
        ("지드래곤, 월드투어 8개 도시 추가", "OSEN"),
        ("뉴진스 컴백, 음악 방송 1위", "마이데일리"),
        ("박찬욱 감독 신작 '미스트리스', 칸영화제 경쟁 부문 출품 확정", "씨네21"),
        ("유재석, 신규 예능 진행 합류", "스타뉴스"),
    ]

    for i, (title, _src) in enumerate(samples, 1):
        path = output_dir / f"{i:02d}_card.jpg"
        make_card(title, path)
        print(f"✅ {i:02d}: {title}")

    sources_path = output_dir / "90_sources.jpg"
    make_sources_card([src for _, src in samples], sources_path)
    print(f"✅ 출처: {sources_path.name}")

    # Reels 그리드 썸네일 (Cover_url 용도)
    thumb_path = output_dir / "00_thumb.jpg"
    make_reels_thumbnail([t for t, _ in samples], thumb_path)
    print(f"✅ 그리드 썸네일: {thumb_path.name}")

    # make_cover_card 함수는 유지되어 있어 필요 시 직접 호출 가능 (현재 production 미사용)
    print(f"\n총 {len(samples) + 2}개 이미지 생성")
    print(f"출력 폴더: {output_dir}")
