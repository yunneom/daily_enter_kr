"""
스피너 영상 v2 — 일시정지 챌린지 포맷.

[니치 메커니즘]
- 팔(바늘)이 멈추지 않고 같은 속도로 계속 회전
- 옵션 8개 중 짝수 위치(0/90/180/270°)에 '운동가기' 류 옵션 배치
- 프레임당 회전각 = 정확히 90° → 렌더되는 모든 프레임에서 팔이 짝수 위치만 가리킴
- 시청자가 어느 프레임에 일시정지해도 절대 음식(홀수 위치)을 잡을 수 없음
- 고스트 잔상 2개로 "빠르게 돌고 있다"는 회전감 연출 → 지나치는 걸 모르게
- 시청자는 알면서도 계속 시도 → 반복 시청/체류 시간 ↑ (다크 패턴 아님 — 영상 내 게임)

[중앙 캐릭터]
- 시계바늘 대신 근육맨(주황 피부 + 검정 머리 + 반바지)이 팔을 돌리는 그림
- 팔 = 스피너. 어깨 피벗 기준 회전, 손끝이 옵션을 가리킴

[출력]
- 1080x1920 (9:16), 30fps, 8초 (Reels 자동 루프)
"""

import math
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font


CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
BG = (248, 248, 246)
INK = (24, 24, 28)
MUTED = (130, 130, 138)
OPTION_FILL = (44, 62, 130)        # 옵션 박스 — 짙은 남색
OPTION_TEXT = (255, 255, 255)

SKIN = (235, 140, 60)              # 근육맨 주황 피부
SKIN_SHADE = (200, 110, 40)
HAIR = (30, 26, 24)
SHORTS = (70, 75, 90)

FPS = 30
DEG_PER_FRAME = 90                 # 프레임당 90° — 짝수 위치만 노출되는 핵심 트릭
WOBBLE_DEG = 5                     # 위치 스냅 범위 안 미세 흔들림 (기계적 느낌 제거)


def _draw_option_box(draw, text, font, cx, cy,
                     fill=OPTION_FILL, text_color=OPTION_TEXT):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 22, 14
    draw.rounded_rectangle(
        [int(cx - tw/2 - pad_x), int(cy - th/2 - pad_y),
         int(cx + tw/2 + pad_x), int(cy + th/2 + pad_y + 6)],
        radius=12, fill=fill)
    draw.text((cx - tw/2 - bbox[0], cy - th/2 - bbox[1]),
              text, font=font, fill=text_color)


def _draw_muscle_body(draw, cx, shoulder_y):
    """근육맨 몸통 (팔 제외) — 정면, 단순 만화체.

    shoulder_y = 어깨(팔 피벗) 높이. 몸은 그 아래로 그려짐.
    """
    # 머리
    head_r = 64
    head_cy = shoulder_y - head_r - 22
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=SKIN, outline=INK, width=5)
    # 머리카락 (윗 반원)
    draw.pieslice([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                  start=180, end=360, fill=HAIR)
    # 웃는 입
    draw.arc([cx - 26, head_cy + 6, cx + 26, head_cy + 44],
             start=10, end=170, fill=INK, width=5)
    # 눈 (점 2개)
    draw.ellipse([cx - 30, head_cy - 6, cx - 16, head_cy + 8], fill=INK)
    draw.ellipse([cx + 16, head_cy - 6, cx + 30, head_cy + 8], fill=INK)

    # 몸통 (어깨 넓고 허리 좁은 사다리꼴)
    torso_h = 190
    draw.polygon([
        (cx - 110, shoulder_y),
        (cx + 110, shoulder_y),
        (cx + 70, shoulder_y + torso_h),
        (cx - 70, shoulder_y + torso_h),
    ], fill=SKIN, outline=INK)
    # 가슴 라인 (만화 근육)
    draw.arc([cx - 60, shoulder_y + 18, cx - 4, shoulder_y + 70],
             start=300, end=120, fill=SKIN_SHADE, width=4)
    draw.arc([cx + 4, shoulder_y + 18, cx + 60, shoulder_y + 70],
             start=60, end=240, fill=SKIN_SHADE, width=4)

    # 반대쪽 팔 (허리에 고정)
    draw.line([(cx - 100, shoulder_y + 14), (cx - 150, shoulder_y + 110)],
              fill=SKIN, width=34)
    draw.line([(cx - 150, shoulder_y + 110), (cx - 92, shoulder_y + 160)],
              fill=SKIN, width=30)

    # 반바지
    shorts_top = shoulder_y + torso_h
    draw.rounded_rectangle([cx - 78, shorts_top, cx + 78, shorts_top + 105],
                           radius=18, fill=SHORTS, outline=INK, width=4)
    # 다리
    draw.line([(cx - 40, shorts_top + 100), (cx - 44, shorts_top + 240)],
              fill=SKIN, width=38)
    draw.line([(cx + 40, shorts_top + 100), (cx + 44, shorts_top + 240)],
              fill=SKIN, width=38)
    # 발
    draw.ellipse([cx - 78, shorts_top + 228, cx - 14, shorts_top + 262], fill=INK)
    draw.ellipse([cx + 14, shorts_top + 228, cx + 78, shorts_top + 262], fill=INK)


def _draw_spinning_arm(draw, pivot_x, pivot_y, angle_deg, length,
                       alpha_color=None):
    """회전 팔 — 어깨 피벗에서 angle 방향. 0°=위, 시계방향.

    alpha_color 지정 시 고스트 잔상용 (연한 색).
    """
    rad = math.radians(angle_deg - 90)
    color = alpha_color or SKIN
    outline = None if alpha_color else INK

    # 팔 (상완 → 전완 살짝 꺾기 없이 곧게 — 만화 단순화)
    tip_x = pivot_x + math.cos(rad) * length
    tip_y = pivot_y + math.sin(rad) * length
    if outline:
        draw.line([(pivot_x, pivot_y), (tip_x, tip_y)], fill=outline, width=40)
    draw.line([(pivot_x, pivot_y), (tip_x, tip_y)], fill=color, width=32)

    # 손 (주먹) + 검지
    hand_r = 26
    draw.ellipse([tip_x - hand_r, tip_y - hand_r, tip_x + hand_r, tip_y + hand_r],
                 fill=color, outline=outline, width=4 if outline else 0)
    # 검지 (가리키는 손가락)
    f_len = 38
    fx = tip_x + math.cos(rad) * f_len
    fy = tip_y + math.sin(rad) * f_len
    draw.line([(tip_x, tip_y), (fx, fy)], fill=color, width=16)


def _frame(title: str, hint: str, options: List[str], arm_angle: float,
           font_paths: dict) -> Image.Image:
    img = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(font_paths["Bold"], 78)
    f_hint = ImageFont.truetype(font_paths["Medium"], 38)
    f_opt = ImageFont.truetype(font_paths["Bold"], 40)

    # 제목 (Reels safe area)
    tw = draw.textlength(title, font=f_title)
    draw.text(((CANVAS[0] - tw) / 2, 220), title, font=f_title, fill=INK)
    hw = draw.textlength(hint, font=f_hint)
    draw.text(((CANVAS[0] - hw) / 2, 340), hint, font=f_hint, fill=MUTED)

    # 옵션 링
    cx, cy = CANVAS[0] // 2, 1080
    r = 380
    n = len(options)
    for i, opt in enumerate(options):
        angle = (360 / n) * i - 90
        rad = math.radians(angle)
        _draw_option_box(draw, opt, f_opt,
                         cx + math.cos(rad) * r, cy + math.sin(rad) * r)

    # 어깨 피벗 = 링 중심. 몸은 피벗 아래로.
    shoulder_y = cy
    _draw_muscle_body(draw, cx, shoulder_y)

    # 고스트 잔상 (회전감) — 30°/60° 뒤, 연하게
    ghost1 = (245, 200, 160)
    ghost2 = (250, 225, 200)
    _draw_spinning_arm(draw, cx, shoulder_y, arm_angle - 60, 300, alpha_color=ghost2)
    _draw_spinning_arm(draw, cx, shoulder_y, arm_angle - 30, 300, alpha_color=ghost1)
    # 본 팔
    _draw_spinning_arm(draw, cx, shoulder_y, arm_angle, 300)

    return img


def make_pause_challenge_video(
    options: List[str],
    output_path: Path,
    title: str = "먹을지 vs 운동 갈지",
    hint: str = "⏸ 일시정지로 메뉴 골라봐!",
    duration_seconds: float = 8.0,
):
    """일시정지 챌린지 스피너 — 팔이 같은 속도로 무한 회전, 절대 안 멈춤.

    프레임당 90° 회전 → 옵션 8개 기준 짝수 위치(0/2/4/6번)만 프레임에 잡힘.
    홀수 위치(음식 등)는 어느 프레임에도 없음 → 일시정지로 잡기 불가능.

    Args:
        options: 8개 옵션. **짝수 인덱스(0,2,4,6) = 잡히는 옵션** (운동가기 등),
                 홀수 인덱스 = 잡을 수 없는 옵션 (음식 등).
    """
    n = len(options)
    assert n == 8, "8개 옵션 전용 (45° 간격, 90°/frame 트릭)"

    total_frames = int(FPS * duration_seconds)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = output_path.parent / f"_frames_{output_path.stem}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()

    font_paths = {
        "Bold": _resolve_font("Bold"),
        "Medium": _resolve_font("Medium"),
    }

    for i in range(total_frames):
        # 핵심: 프레임당 정확히 90° + 스냅 범위 내 흔들림 → 짝수 위치만 노출
        base = (i * DEG_PER_FRAME) % 360
        wobble = WOBBLE_DEG * math.sin(i * 0.7)
        img = _frame(title, hint, options, base + wobble, font_paths)
        img.save(frames_dir / f"frame_{i:04d}.jpg", "JPEG", quality=88)

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
