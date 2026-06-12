"""
스피너 영상 — 중앙 화살표(또는 팔)가 회전 → 감속 → 한 옵션에 정착.

[디자인]
- 1080x1920 (9:16) Reels
- N개 옵션 (보통 8) 원형 배치, 중앙에 회전 화살표
- 감속 물리 (ease-out): 빠르게 시작 → 천천히 멈춤
- 마지막 1초 정착 옵션 강조 (노란 펄스)
- 호기심 유발 — 시청자가 "어디 멈출까?" 끝까지 봄

[안전]
- 클릭 유발 X (영상만 봄)
- 결과는 사전 결정 (chosen_idx) → 알고리즘 조작 X
"""

import math
import shutil
import subprocess
from pathlib import Path
from typing import List
from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 28)
MUTED = (130, 130, 138)
OPTION_FILL = (60, 90, 180)        # 옵션 박스 — 짙은 파란
OPTION_TEXT = (255, 255, 255)
HIGHLIGHT = (255, 220, 0)          # 정착 시 강조 색
ARROW_COLOR = (220, 50, 50)        # 화살표 빨강

FPS = 30


def _ease_out_cubic(t: float) -> float:
    """0→1 입력, 부드러운 감속 곡선."""
    return 1 - (1 - t) ** 3


def _draw_option_box(draw, text, font, cx, cy, fill=OPTION_FILL, text_color=OPTION_TEXT):
    """원형 둘레의 옵션 라벨 박스 — 둥근 사각형 + 글자."""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 22, 14
    x0 = int(cx - tw/2 - pad_x)
    y0 = int(cy - th/2 - pad_y)
    x1 = int(cx + tw/2 + pad_x)
    y1 = int(cy + th/2 + pad_y + 6)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=fill)
    draw.text((cx - tw/2 - bbox[0], cy - th/2 - bbox[1]),
              text, font=font, fill=text_color)


def _draw_arrow(draw, cx, cy, angle_deg, length, head_size=42, color=ARROW_COLOR):
    """중심에서 angle 방향으로 화살표. 0° = 위, 시계 방향."""
    rad = math.radians(angle_deg - 90)  # -90 보정 — 0°가 위쪽
    tip_x = cx + math.cos(rad) * length
    tip_y = cy + math.sin(rad) * length
    # 두꺼운 본체 (라인)
    draw.line([(cx, cy), (tip_x, tip_y)], fill=color, width=18)
    # 중심 원
    draw.ellipse([cx-22, cy-22, cx+22, cy+22], fill=color)
    draw.ellipse([cx-10, cy-10, cx+10, cy+10], fill=WHITE)
    # 화살촉 (삼각형)
    perp = rad + math.pi / 2
    h_left_x = tip_x - math.cos(rad) * head_size + math.cos(perp) * (head_size * 0.6)
    h_left_y = tip_y - math.sin(rad) * head_size + math.sin(perp) * (head_size * 0.6)
    h_right_x = tip_x - math.cos(rad) * head_size - math.cos(perp) * (head_size * 0.6)
    h_right_y = tip_y - math.sin(rad) * head_size - math.sin(perp) * (head_size * 0.6)
    draw.polygon([(tip_x, tip_y), (h_left_x, h_left_y), (h_right_x, h_right_y)],
                 fill=color)


def _frame(title: str, hint: str, options: List[str], arrow_angle: float,
           chosen_idx: int, highlight_alpha: int, font_paths: dict) -> Image.Image:
    """한 프레임 렌더."""
    img = Image.new("RGB", CANVAS, WHITE)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(font_paths["Bold"], 78)
    f_hint = ImageFont.truetype(font_paths["Medium"], 38)
    f_opt = ImageFont.truetype(font_paths["Bold"], 40)

    # 제목 (safe area 220)
    tw = draw.textlength(title, font=f_title)
    draw.text(((CANVAS[0] - tw) / 2, 220), title, font=f_title, fill=INK)
    # 힌트
    hw = draw.textlength(hint, font=f_hint)
    draw.text(((CANVAS[0] - hw) / 2, 340), hint, font=f_hint, fill=MUTED)

    # 원형 배치 — 중심 (cx, cy), 반지름 r
    cx, cy = CANVAS[0] // 2, 1100
    r = 360
    n = len(options)

    for i, opt in enumerate(options):
        angle = (360 / n) * i - 90  # 0번은 위쪽
        rad = math.radians(angle)
        ox = cx + math.cos(rad) * r
        oy = cy + math.sin(rad) * r
        # 정착 옵션 강조 (highlight_alpha 0~255)
        if i == chosen_idx and highlight_alpha > 0:
            # 노란 글로우 (RGBA 위에 합성)
            glow_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            gd.ellipse([int(ox - 130), int(oy - 90),
                        int(ox + 130), int(oy + 90)],
                       fill=(*HIGHLIGHT, highlight_alpha))
            img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")
            draw = ImageDraw.Draw(img)
            _draw_option_box(draw, opt, f_opt, ox, oy,
                             fill=HIGHLIGHT, text_color=INK)
        else:
            _draw_option_box(draw, opt, f_opt, ox, oy)

    # 화살표
    _draw_arrow(draw, cx, cy, arrow_angle, length=290)

    return img


def make_spinner_video(
    options: List[str],
    chosen_idx: int,
    output_path: Path,
    title: str = "오늘 뭐 할지?",
    hint: str = "운명을 맡겨봐 🎯",
    spin_seconds: float = 6.0,
    settle_seconds: float = 1.5,
    total_rotations: float = 4.0,
):
    """N개 옵션 중 chosen_idx 에 정착하는 스피너 영상.

    Args:
        options: 옵션 텍스트 N개
        chosen_idx: 정착 옵션 인덱스
        spin_seconds: 회전 시간
        settle_seconds: 정착 후 강조 시간
        total_rotations: 총 회전 바퀴 수
    """
    n = len(options)
    final_angle = (360 / n) * chosen_idx  # 정착 각도
    start_angle = 0
    end_angle = 360 * total_rotations + final_angle

    spin_frames = int(FPS * spin_seconds)
    settle_frames = int(FPS * settle_seconds)
    total_frames = spin_frames + settle_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = output_path.parent / f"_frames_{output_path.stem}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()

    font_paths = {
        "Bold": _resolve_font("Bold"),
        "Medium": _resolve_font("Medium"),
    }

    # 회전 단계
    for i in range(spin_frames):
        t = i / max(spin_frames - 1, 1)
        eased = _ease_out_cubic(t)
        angle = start_angle + (end_angle - start_angle) * eased
        img = _frame(title, hint, options, angle, chosen_idx=-1,
                     highlight_alpha=0, font_paths=font_paths)
        img.save(frames_dir / f"frame_{i:04d}.jpg", "JPEG", quality=88)

    # 정착 단계 — 노란 글로우 펄스
    for j in range(settle_frames):
        # 펄스 (0→255→0) 절반 알파
        p = j / max(settle_frames - 1, 1)
        # 펄스 두 번 (사인 곡선)
        alpha = int(180 * abs(math.sin(p * math.pi * 2)))
        img = _frame(title, hint, options, end_angle, chosen_idx=chosen_idx,
                     highlight_alpha=alpha, font_paths=font_paths)
        img.save(frames_dir / f"frame_{spin_frames + j:04d}.jpg",
                 "JPEG", quality=88)

    # ffmpeg 합성
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "frame_%04d.jpg"),
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-1500:]}")
    return output_path
