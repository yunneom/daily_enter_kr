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
import textwrap


# 색상 팔레트 (카테고리별)
COLOR_THEMES = {
    "default": {
        "bg_top": (30, 41, 59),     # 진한 남색
        "bg_bottom": (15, 23, 42),   # 거의 검정
        "accent": (251, 191, 36),    # 골드
        "text": (255, 255, 255),
        "subtext": (203, 213, 225),
    },
    "warm": {
        "bg_top": (190, 18, 60),
        "bg_bottom": (88, 28, 135),
        "accent": (251, 191, 36),
        "text": (255, 255, 255),
        "subtext": (253, 224, 71),
    },
    "cool": {
        "bg_top": (37, 99, 235),
        "bg_bottom": (16, 185, 129),
        "accent": (255, 255, 255),
        "text": (255, 255, 255),
        "subtext": (219, 234, 254),
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
    theme: str = "default",
    font_path: str = None,
    size: Tuple[int, int] = (1080, 1080),
):
    """단일 카드뉴스 이미지 생성"""
    colors = COLOR_THEMES[theme]
    
    # 1. 배경 그라데이션
    img = create_gradient(size, colors["bg_top"], colors["bg_bottom"])
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
    draw.text((60, size[1] - 75), f"{source}  |  오늘의 핫이슈",
              font=font_source, fill=colors["subtext"])
    
    # 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


def make_cover_card(date_str: str, output_path: Path, theme: str = "default", 
                    font_path: str = None, size=(1080, 1080)):
    """캐러셀 첫 장(표지) 생성"""
    colors = COLOR_THEMES[theme]
    img = create_gradient(size, colors["bg_top"], colors["bg_bottom"])
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
    
    # 중앙 정렬
    draw.text((100, 380), "오늘의", font=font_mid, fill=colors["subtext"])
    draw.text((100, 470), "핫이슈", font=font_big, fill=colors["accent"])
    draw.text((100, 640), "TOP 10", font=font_big, fill=colors["text"])
    draw.text((100, 820), date_str, font=font_small, fill=colors["subtext"])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return output_path


if __name__ == "__main__":
    from datetime import datetime
    
    # 테스트 카드 생성 (스크립트 위치 기준 상대 경로)
    output_dir = Path(__file__).parent.parent / "output" / "sample"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 표지
    make_cover_card(
        date_str=datetime.now().strftime("%Y년 %m월 %d일"),
        output_path=output_dir / "00_cover.jpg",
        theme="default",
    )
    
    # 샘플 카드들
    samples = [
        (1, "삼성전자 총파업 위기", "노조와의 최후 협상이 오늘 진행됩니다. 합의 실패 시 사상 첫 총파업으로 이어질 전망입니다.", "매일경제", "default"),
        (2, "이란-미국 일촉즉발", "이란이 새 협상안을 제출했고 트럼프는 공격 중단을 지시했습니다. 긴장은 여전히 남아있는 상황입니다.", "경향신문", "warm"),
        (3, "초여름 더위 31도", "오늘 낮 최고기온이 31도까지 오르며 초여름 더위가 절정에 달합니다. 밤부터 비 소식이 있습니다.", "한겨레", "cool"),
    ]
    
    for rank, title, body, source, theme in samples:
        path = output_dir / f"{rank:02d}_card.jpg"
        make_card(rank, title, body, source, path, theme=theme)
        print(f"✅ 생성: {path}")
    
    print(f"\n총 {len(samples) + 1}개 이미지 생성 완료")
    print(f"출력 폴더: {output_dir}")
