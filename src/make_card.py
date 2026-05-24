"""
카드뉴스 이미지 생성 모듈
PIL(Pillow)로 템플릿 기반 카드뉴스 이미지를 생성합니다.

[디자인 컨셉]
- 인스타그램 정사각형 1080x1080 (캐러셀 표준)
- 그라데이션 배경 + 큰 제목 + 본문 + 출처
- 한글 폰트 필요 (Pretendard, NotoSans 등)
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from typing import Tuple
import random
import textwrap


# K-엔터 색상 팔레트 (5가지 시네마틱 톤)
COLOR_THEMES = {
    "neon_seoul": {
        # 한국 야경/네온사인 무드 — 마젠타+시안+딥 네이비
        "bg_top": (20, 10, 50),
        "bg_bottom": (5, 0, 25),
        "bokeh": [(255, 80, 180), (80, 200, 255), (180, 100, 255), (255, 220, 100)],
        "accent": (255, 220, 100),
        "text": (255, 255, 255),
        "subtext": (210, 210, 240),
    },
    "stage_gold": {
        # 콘서트 스테이지 — 다크 레드+골드+블랙
        "bg_top": (70, 15, 15),
        "bg_bottom": (15, 5, 5),
        "bokeh": [(255, 200, 80), (255, 100, 50), (220, 150, 100), (255, 230, 150)],
        "accent": (255, 215, 0),
        "text": (255, 255, 255),
        "subtext": (255, 220, 180),
    },
    "kpop_pastel": {
        # 아이돌 / 화보 무드 — 핑크+라벤더+페일 옐로우
        "bg_top": (110, 60, 130),
        "bg_bottom": (60, 30, 80),
        "bokeh": [(255, 200, 230), (200, 220, 255), (255, 240, 200), (255, 180, 220)],
        "accent": (255, 255, 220),
        "text": (255, 255, 255),
        "subtext": (255, 230, 240),
    },
    "noir_cinema": {
        # 드라마/영화 — 와인+버건디+골드
        "bg_top": (45, 15, 25),
        "bg_bottom": (10, 5, 10),
        "bokeh": [(220, 60, 70), (250, 200, 100), (140, 100, 90), (255, 180, 130)],
        "accent": (240, 200, 100),
        "text": (255, 255, 255),
        "subtext": (230, 210, 200),
    },
    "dream_purple": {
        # 모던 MV — 퍼플+마젠타+딥 블루
        "bg_top": (60, 25, 100),
        "bg_bottom": (20, 10, 60),
        "bokeh": [(180, 100, 255), (255, 100, 200), (100, 150, 255), (255, 220, 120)],
        "accent": (255, 220, 100),
        "text": (255, 255, 255),
        "subtext": (220, 200, 255),
    },
}


def create_gradient(size: Tuple[int, int], top_color, bottom_color) -> Image.Image:
    """세로 그라데이션 배경 생성"""
    w, h = size
    base = Image.new("RGB", (w, h), top_color)
    top = Image.new("RGB", (w, h), top_color)
    bottom = Image.new("RGB", (w, h), bottom_color)
    mask = Image.new("L", (w, h))
    mask_data = []
    for y in range(h):
        mask_data.extend([int(255 * (y / h))] * w)
    mask.putdata(mask_data)
    base = Image.composite(bottom, top, mask)
    return base


def make_cinematic_background(
    size: Tuple[int, int],
    palette: dict,
    seed: int = None,
) -> Image.Image:
    """K-엔터 시네마틱 배경 — 그라데이션 + 보케 라이트 + 비네팅

    Args:
        size: (w, h)
        palette: COLOR_THEMES의 한 항목
        seed: 결정론적 결과를 위한 시드 (없으면 랜덤)
    """
    rng = random.Random(seed)
    w, h = size

    # 1. 베이스 그라데이션
    img = create_gradient(size, palette["bg_top"], palette["bg_bottom"]).convert("RGBA")

    # 2. 보케 원 12-20개를 별도 레이어에 그리고 강하게 블러
    bokeh_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bokeh_layer)
    n = rng.randint(12, 20)
    for _ in range(n):
        # 일부는 화면 밖으로 살짝 걸치게 (자연스러운 비네팅 효과)
        cx = rng.randint(-150, w + 150)
        cy = rng.randint(-150, h + 150)
        radius = rng.randint(80, 280)
        color = rng.choice(palette["bokeh"])
        alpha = rng.randint(40, 110)
        bdraw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=color + (alpha,),
        )
    # 부드럽고 dreamy한 보케를 위한 강한 블러
    bokeh_layer = bokeh_layer.filter(ImageFilter.GaussianBlur(radius=50))
    img = Image.alpha_composite(img, bokeh_layer)

    # 3. 비네팅 — 가장자리 어둡게 (시네마틱)
    vignette = Image.new("L", size, 0)
    vdraw = ImageDraw.Draw(vignette)
    # 중앙은 밝게(흰색), 가장자리로 갈수록 검게 — radial mask
    margin = int(min(w, h) * 0.35)
    vdraw.ellipse(
        [-margin, -margin, w + margin, h + margin],
        fill=255,
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=int(min(w, h) * 0.25)))
    # 비네팅 마스크를 사용해 검정색을 합성
    dark_layer = Image.new("RGBA", size, (0, 0, 0, 180))
    # vignette가 흰색(255)인 곳은 alpha=0, 검정(0)인 곳은 alpha=180
    inverted = Image.eval(vignette, lambda v: 255 - v)
    dark_layer.putalpha(Image.eval(inverted, lambda v: int(v * 0.5)))
    img = Image.alpha_composite(img, dark_layer)

    return img.convert("RGB")


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """텍스트를 max_width에 맞춰 줄바꿈"""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def make_card(
    rank: int,
    title: str,
    body: str,
    source: str,
    output_path: Path,
    theme: str = "neon_seoul",
    font_path: str = None,
    size: Tuple[int, int] = (1080, 1080),
    seed: int = None,
    total_cards: int = 9,
):
    """단일 카드뉴스 이미지 생성 (K-엔터 시네마틱 배경).

    Args:
        total_cards: 캐러셀의 총 카드 수 (표지 제외). 페이지 인디케이터 표시용.
    """
    if theme not in COLOR_THEMES:
        theme = "neon_seoul"
    colors = COLOR_THEMES[theme]

    # 1. 시네마틱 배경 (그라데이션 + 보케 라이트 + 비네팅)
    if seed is None:
        seed = hash(title) % (2 ** 31)
    img = make_cinematic_background(size, colors, seed=seed)
    draw = ImageDraw.Draw(img)
    
    # 2. 폰트 로드 (없으면 기본)
    if font_path and Path(font_path).exists():
        font_rank = ImageFont.truetype(font_path, 120)
        font_title = ImageFont.truetype(font_path, 72)
        font_body = ImageFont.truetype(font_path, 42)
        font_source = ImageFont.truetype(font_path, 28)
    else:
        # 시스템 한글 폰트 자동 탐색
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "C:/Windows/Fonts/malgunbd.ttf",
        ]
        font_file = None
        for c in candidates:
            if Path(c).exists():
                font_file = c
                break
        if font_file:
            font_rank = ImageFont.truetype(font_file, 120)
            font_title = ImageFont.truetype(font_file, 72)
            font_body = ImageFont.truetype(font_file, 42)
            font_source = ImageFont.truetype(font_file, 28)
        else:
            font_rank = font_title = font_body = font_source = ImageFont.load_default()
    
    # 3. 상단 액센트 라인
    draw.rectangle([(60, 60), (220, 70)], fill=colors["accent"])

    # 4. 랭크 (큰 숫자)
    draw.text((60, 90), f"#{rank}", font=font_rank, fill=colors["accent"])

    # 4-b. 우상단 페이지 인디케이터 (캐러셀 위치 안내)
    page_label = f"{rank:02d} / {total_cards:02d}"
    page_bbox = font_source.getbbox(page_label)
    draw.text(
        (size[0] - 60 - (page_bbox[2] - page_bbox[0]), 90),
        page_label,
        font=font_source,
        fill=colors["subtext"],
    )
    
    # 5. 제목 (자동 줄바꿈)
    y_pos = 280
    title_lines = wrap_text(title, font_title, size[0] - 120)
    for line in title_lines[:3]:  # 최대 3줄
        draw.text((60, y_pos), line, font=font_title, fill=colors["text"])
        y_pos += 90
    
    # 6. 본문 (자동 줄바꿈)
    y_pos += 40
    body_lines = wrap_text(body, font_body, size[0] - 120)
    for line in body_lines[:6]:
        draw.text((60, y_pos), line, font=font_body, fill=colors["subtext"])
        y_pos += 56
    
    # 7. 하단 출처 + 액센트 라인
    draw.rectangle([(60, size[1] - 100), (220, size[1] - 95)], fill=colors["accent"])
    draw.text((60, size[1] - 75), f"{source}  |  오늘의 K-연예",
              font=font_source, fill=colors["subtext"])
    
    # 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_cover_card(date_str: str, output_path: Path, theme: str = "neon_seoul",
                    font_path: str = None, size=(1080, 1080), seed: int = None,
                    total_cards: int = None):
    """캐러셀 첫 장(표지) 생성 — K-엔터 시네마틱 배경

    Args:
        total_cards: 본문 카드 수 (표지 제외). None이면 'HOT NEWS' 라벨 사용.
                     그 외에는 'TOP {N}' 동적 표시.
    """
    if theme not in COLOR_THEMES:
        theme = "neon_seoul"
    colors = COLOR_THEMES[theme]
    if seed is None:
        seed = hash(date_str) % (2 ** 31)
    img = make_cinematic_background(size, colors, seed=seed)
    draw = ImageDraw.Draw(img)

    candidates = [
        font_path,
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
    ]
    font_file = next((c for c in candidates if c and Path(c).exists()), None)

    if font_file:
        font_big = ImageFont.truetype(font_file, 140)
        font_mid = ImageFont.truetype(font_file, 80)
        font_small = ImageFont.truetype(font_file, 40)
    else:
        font_big = font_mid = font_small = ImageFont.load_default()

    # 본문 카드 수에 맞춰 라벨 결정 (불일치 방지)
    if total_cards is None or total_cards <= 0:
        rank_label = "HOT NEWS"
    else:
        rank_label = f"TOP {total_cards}"

    # 중앙 정렬
    draw.text((100, 380), "오늘의", font=font_mid, fill=colors["subtext"])
    draw.text((100, 470), "K-연예", font=font_big, fill=colors["accent"])
    draw.text((100, 640), rank_label, font=font_big, fill=colors["text"])
    draw.text((100, 820), date_str, font=font_small, fill=colors["subtext"])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


if __name__ == "__main__":
    from datetime import datetime

    # 5가지 K-엔터 팔레트 미리보기 (테스트용)
    output_dir = Path(__file__).parent.parent / "output" / "sample"
    output_dir.mkdir(parents=True, exist_ok=True)

    make_cover_card(
        date_str=datetime.now().strftime("%Y년 %m월 %d일"),
        output_path=output_dir / "00_cover.jpg",
        theme="neon_seoul",
    )

    samples = [
        (1, "neon_seoul",   "아이브 새 앨범 티저 공개",      "신곡 'XYZ' 콘셉트 영상이 깜짝 공개됐다. 비주얼 디렉터는 누구일지 팬들 관심 집중.",          "스포츠동아"),
        (2, "stage_gold",   "지드래곤, 월드투어 8개 도시 추가", "기존 발표된 12개 도시에 8개가 추가됐다. 아시아 우선, 북미는 9월부터 시작 예정.",                "OSEN"),
        (3, "kpop_pastel",  "뉴진스 컴백, 음악 방송 1위",     "발매 첫 주 음원 차트 상위권 진입에 이어 지상파 음악 방송에서 1위를 차지했다.",                "마이데일리"),
        (4, "noir_cinema",  "박찬욱 감독 신작, 칸 출품 확정",  "이번 작품은 미스터리 스릴러 장르로, 주연 배우 라인업이 곧 공개될 예정이다.",                  "씨네21"),
        (5, "dream_purple", "유재석, 신규 예능 진행 합류",     "케이블 채널 새 프로그램에 단독 MC로 합류한다. 첫 녹화는 다음 달 초로 알려졌다.",              "스타뉴스"),
    ]
    for rank, theme, title, body, source in samples:
        path = output_dir / f"{rank:02d}_{theme}.jpg"
        make_card(rank, title, body, source, path, theme=theme, total_cards=len(samples))
        print(f"✅ 생성: {path}")

    print(f"\n총 {len(samples) + 1}개 이미지 생성 완료")
    print(f"출력 폴더: {output_dir}")
