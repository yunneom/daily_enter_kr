"""
스피너 영상 v3 — 일시정지 챌린지.

[니치 메커니즘]
- 팔이 멈추지 않고 일정 속도 무한 회전
- 프레임당 90° 점프 → 8옵션 중 짝수 위치만 노출. 음식 옵션(홀수)은 어떤 프레임에도 안 나옴 → 일시정지 불가
- 시청자는 알면서도 반복 시도 → 체류 시간 ↑

[캐릭터]
- 만화체 근육맨. 슈퍼샘플링 + 음영 레이어로 매끄럽게 렌더
- 어깨 피벗에서 팔이 곧 스피너
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
BG = (248, 248, 246)
INK = (24, 24, 28)
MUTED = (130, 130, 138)
OPTION_FILL = (44, 62, 130)
OPTION_TEXT = (255, 255, 255)

# 근육맨 컬러 팔레트 (3톤: 하이라이트/베이스/섀도우 — 입체감)
SKIN_BASE = (236, 165, 109)
SKIN_HIGH = (248, 195, 145)
SKIN_SHADE = (190, 120, 70)
HAIR_BASE = (40, 32, 30)
HAIR_HIGH = (75, 60, 55)
SHORTS_BASE = (54, 64, 92)
SHORTS_SHADE = (32, 40, 64)

FPS = 30
DEG_PER_FRAME = 90
WOBBLE_DEG = 5
SS = 2  # supersample factor — 2x 렌더 후 다운스케일 (AA)


def _draw_option_box(draw, text, font, cx, cy):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 22, 14
    draw.rounded_rectangle(
        [int(cx - tw/2 - pad_x), int(cy - th/2 - pad_y),
         int(cx + tw/2 + pad_x), int(cy + th/2 + pad_y + 6)],
        radius=12, fill=OPTION_FILL)
    draw.text((cx - tw/2 - bbox[0], cy - th/2 - bbox[1]),
              text, font=font, fill=OPTION_TEXT)


def _render_muscle_character(size: int, arm_angle_deg: float,
                              font_paths: dict) -> Image.Image:
    """근육맨 캐릭터를 size x size 정사각 RGBA 로 렌더 — 슈퍼샘플링.

    어깨 피벗은 정사각의 중심점.
    """
    W = size * SS
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W // 2
    shoulder_y = W // 2  # 피벗 = 캐릭터 정사각의 중심

    # ── 머리 ──────────────────────────────────────
    head_w = int(W * 0.18)
    head_h = int(W * 0.20)
    head_cy = shoulder_y - int(head_h * 1.10)
    # 베이스 두상 (살짝 세로로 긴 타원)
    head_box = [cx - head_w, head_cy - head_h, cx + head_w, head_cy + head_h]
    d.ellipse(head_box, fill=SKIN_BASE)
    # 턱 그림자 (아래 절반 음영)
    shade_box = [cx - head_w + 4, head_cy + 2,
                 cx + head_w - 4, head_cy + head_h]
    d.chord(shade_box, start=10, end=170, fill=SKIN_SHADE)
    d.ellipse(head_box, outline=INK, width=int(SS * 3))

    # 머리카락 — 슬릭 백 스타일 (정수리에 살짝 봉긋)
    hair_top = [
        (cx - head_w + 6, head_cy - 6),
        (cx - head_w + 22, head_cy - head_h + 4),
        (cx - head_w // 3, head_cy - head_h - 14),
        (cx + head_w // 3, head_cy - head_h - 14),
        (cx + head_w - 22, head_cy - head_h + 4),
        (cx + head_w - 6, head_cy - 6),
        (cx + head_w - 10, head_cy - head_h // 2),
        (cx - head_w + 10, head_cy - head_h // 2),
    ]
    d.polygon(hair_top, fill=HAIR_BASE)
    # 머리카락 하이라이트 (한 줄)
    d.line([(cx - head_w + 30, head_cy - head_h + 6),
            (cx + head_w // 3, head_cy - head_h - 6)],
           fill=HAIR_HIGH, width=int(SS * 4))

    # 눈 (자신감 있는 슬릿)
    eye_y = head_cy - 6
    eye_dx = int(head_w * 0.42)
    eye_w = int(head_w * 0.16)
    eye_h = int(head_h * 0.07)
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        d.ellipse([ex - eye_w, eye_y - eye_h, ex + eye_w, eye_y + eye_h],
                  fill=INK)
        # 눈썹 (살짝 위쪽 사선)
        bx0 = ex - eye_w - 2
        by0 = eye_y - eye_h - 18
        bx1 = ex + eye_w + 2
        by1 = eye_y - eye_h - 8
        d.line([(bx0, by0 if sign < 0 else by1),
                (bx1, by1 if sign < 0 else by0)],
               fill=INK, width=int(SS * 5))

    # 미소 (살짝 비대칭 smirk)
    mouth_cx = cx + 8
    mouth_cy = head_cy + int(head_h * 0.42)
    d.arc([mouth_cx - 34, mouth_cy - 14, mouth_cx + 34, mouth_cy + 30],
          start=10, end=160, fill=INK, width=int(SS * 4))

    # ── 목 ──────────────────────────────────────
    neck_w = int(head_w * 0.45)
    neck_h = int(head_h * 0.30)
    d.rectangle([cx - neck_w, head_cy + head_h - 8,
                 cx + neck_w, head_cy + head_h + neck_h],
                fill=SKIN_SHADE)

    # ── 몸통 (V자 실루엣) ─────────────────────────
    shoulder_w = int(W * 0.38)
    waist_w = int(W * 0.20)
    torso_h = int(W * 0.30)
    torso_pts = [
        (cx - shoulder_w, shoulder_y),
        (cx + shoulder_w, shoulder_y),
        (cx + waist_w, shoulder_y + torso_h),
        (cx - waist_w, shoulder_y + torso_h),
    ]
    d.polygon(torso_pts, fill=SKIN_BASE)
    # 가슴 음영 — 두 흉근의 경계 (역 V)
    pec_top = shoulder_y + int(torso_h * 0.10)
    pec_mid_y = shoulder_y + int(torso_h * 0.40)
    pec_w = int(shoulder_w * 0.85)
    # 좌측 흉근 하이라이트
    d.polygon([(cx - pec_w, pec_top),
               (cx - 8, pec_top + 10),
               (cx - 8, pec_mid_y),
               (cx - int(pec_w * 0.6), pec_mid_y)],
              fill=SKIN_HIGH)
    # 우측 흉근 하이라이트
    d.polygon([(cx + 8, pec_top + 10),
               (cx + pec_w, pec_top),
               (cx + int(pec_w * 0.6), pec_mid_y),
               (cx + 8, pec_mid_y)],
              fill=SKIN_HIGH)
    # 흉근 경계선
    d.line([(cx, pec_top + 14), (cx, pec_mid_y - 4)],
           fill=SKIN_SHADE, width=int(SS * 5))
    # 복근 음영 (살짝)
    abs_top = pec_mid_y + 10
    abs_bot = shoulder_y + int(torso_h * 0.85)
    d.line([(cx, abs_top), (cx, abs_bot)],
           fill=SKIN_SHADE, width=int(SS * 3))
    for y_frac in (0.30, 0.55, 0.78):
        ay = abs_top + int((abs_bot - abs_top) * y_frac)
        d.arc([cx - 50, ay - 18, cx + 50, ay + 8],
              start=200, end=340, fill=SKIN_SHADE, width=int(SS * 3))
    # 몸통 외곽선
    d.polygon(torso_pts, outline=INK, width=int(SS * 3))

    # ── 반대쪽 팔 (허리에 자신감 있게) ────────────
    arm_w = int(W * 0.05)
    sh_lx = cx - shoulder_w + arm_w
    sh_ly = shoulder_y + int(arm_w * 0.3)
    elbow_lx = sh_lx - int(arm_w * 2.0)
    elbow_ly = sh_ly + int(torso_h * 0.45)
    hand_lx = cx - waist_w - int(arm_w * 0.4)
    hand_ly = sh_ly + int(torso_h * 0.70)
    # 어깨→팔꿈치 (위팔, 바이셉 살짝 부풀게)
    d.line([(sh_lx, sh_ly), (elbow_lx, elbow_ly)],
           fill=SKIN_BASE, width=int(arm_w * 1.8))
    # 바이셉 하이라이트 (위팔 안쪽)
    mid_x = (sh_lx + elbow_lx) // 2 + 6
    mid_y = (sh_ly + elbow_ly) // 2
    d.ellipse([mid_x - 28, mid_y - 36, mid_x + 28, mid_y + 28],
              fill=SKIN_HIGH)
    # 팔꿈치→손
    d.line([(elbow_lx, elbow_ly), (hand_lx, hand_ly)],
           fill=SKIN_BASE, width=int(arm_w * 1.5))
    # 주먹
    d.ellipse([hand_lx - arm_w, hand_ly - arm_w,
               hand_lx + arm_w, hand_ly + arm_w], fill=SKIN_BASE)

    # ── 반바지 ──────────────────────────────────
    shorts_top = shoulder_y + torso_h
    shorts_h = int(W * 0.10)
    sx0 = cx - waist_w - 6
    sx1 = cx + waist_w + 6
    d.rounded_rectangle([sx0, shorts_top, sx1, shorts_top + shorts_h],
                        radius=int(W * 0.015), fill=SHORTS_BASE)
    # 가운데 솔기
    d.line([(cx, shorts_top + 4), (cx, shorts_top + shorts_h - 4)],
           fill=SHORTS_SHADE, width=int(SS * 3))
    d.rounded_rectangle([sx0, shorts_top, sx1, shorts_top + shorts_h],
                        radius=int(W * 0.015), outline=INK,
                        width=int(SS * 3))

    # ── 다리 ────────────────────────────────────
    leg_w = int(W * 0.055)
    leg_h = int(W * 0.16)
    legs_top = shorts_top + shorts_h
    for lx in (cx - waist_w // 2 - 4, cx + waist_w // 2 + 4):
        # 허벅지
        d.line([(lx, legs_top), (lx, legs_top + leg_h)],
               fill=SKIN_BASE, width=int(leg_w * 2.0))
        # 발 (윤곽 있는 신발 느낌)
        d.ellipse([lx - leg_w, legs_top + leg_h - 8,
                   lx + leg_w + 12, legs_top + leg_h + 22],
                  fill=INK)

    # ── 회전 팔 (스피너) ────────────────────────
    rad = math.radians(arm_angle_deg - 90)
    arm_len = int(W * 0.32)
    pivot_x = cx + int(shoulder_w * 0.85)
    pivot_y = shoulder_y + int(arm_w * 0.3)
    tip_x = pivot_x + math.cos(rad) * arm_len
    tip_y = pivot_y + math.sin(rad) * arm_len
    # 어깨→손 (한 줄, 끝점 둥글게)
    d.line([(pivot_x, pivot_y), (tip_x, tip_y)],
           fill=SKIN_BASE, width=int(arm_w * 2.2))
    # 어깨 둥글게 마무리 (라인 캡)
    d.ellipse([pivot_x - int(arm_w * 1.1), pivot_y - int(arm_w * 1.1),
               pivot_x + int(arm_w * 1.1), pivot_y + int(arm_w * 1.1)],
              fill=SKIN_BASE)
    # 바이셉 하이라이트 (회전 팔 안쪽)
    midf = 0.45
    bx = pivot_x + math.cos(rad) * arm_len * midf
    by = pivot_y + math.sin(rad) * arm_len * midf
    perp = rad + math.pi / 2
    hx = bx + math.cos(perp) * arm_w * 0.6
    hy = by + math.sin(perp) * arm_w * 0.6
    d.ellipse([hx - arm_w * 1.0, hy - arm_w * 1.0,
               hx + arm_w * 1.0, hy + arm_w * 1.0],
              fill=SKIN_HIGH)
    # 주먹
    hand_r = int(arm_w * 1.25)
    d.ellipse([tip_x - hand_r, tip_y - hand_r,
               tip_x + hand_r, tip_y + hand_r], fill=SKIN_BASE)
    # 검지 (가리키는 손가락)
    f_len = int(arm_w * 1.6)
    fx = tip_x + math.cos(rad) * f_len
    fy = tip_y + math.sin(rad) * f_len
    d.line([(tip_x, tip_y), (fx, fy)],
           fill=SKIN_BASE, width=int(arm_w * 0.85))
    # 손가락 끝 둥글게
    d.ellipse([fx - int(arm_w * 0.42), fy - int(arm_w * 0.42),
               fx + int(arm_w * 0.42), fy + int(arm_w * 0.42)],
              fill=SKIN_BASE)

    # 다운스케일 (AA)
    return layer.resize((size, size), Image.LANCZOS)


def _frame(title: str, hint: str, options: List[str], arm_angle: float,
           font_paths: dict) -> Image.Image:
    img = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(font_paths["Bold"], 78)
    f_hint = ImageFont.truetype(font_paths["Medium"], 38)
    f_opt = ImageFont.truetype(font_paths["Bold"], 40)

    # 제목 + 힌트 (safe area)
    tw = draw.textlength(title, font=f_title)
    draw.text(((CANVAS[0] - tw) / 2, 220), title, font=f_title, fill=INK)
    hw = draw.textlength(hint, font=f_hint)
    draw.text(((CANVAS[0] - hw) / 2, 340), hint, font=f_hint, fill=MUTED)

    # 옵션 링
    ring_cx, ring_cy = CANVAS[0] // 2, 1100
    r = 400
    for i, opt in enumerate(options):
        angle = (360 / len(options)) * i - 90
        rad = math.radians(angle)
        _draw_option_box(draw, opt, f_opt,
                         ring_cx + math.cos(rad) * r,
                         ring_cy + math.sin(rad) * r)

    # 캐릭터 — 어깨 피벗을 옵션 링 중심에 정렬
    char_size = 700
    character = _render_muscle_character(char_size, arm_angle, font_paths)
    cx0 = ring_cx - char_size // 2
    cy0 = ring_cy - char_size // 2
    img.paste(character, (cx0, cy0), character)

    return img


def make_pause_challenge_video(
    options: List[str],
    output_path: Path,
    title: str = "먹을지 vs 운동 갈지",
    hint: str = "⏸ 일시정지로 메뉴 골라봐!",
    duration_seconds: float = 8.0,
):
    """일시정지 챌린지 — 팔이 무한 회전, 짝수 위치 옵션만 노출."""
    assert len(options) == 8, "8개 옵션 전용"
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

