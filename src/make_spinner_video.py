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
SS = 2

# 운동복 (sport_woman) 추가 컬러
SPORTSWEAR_TOP = (220, 80, 130)
SPORTSWEAR_SHADE = (170, 50, 95)
SPORTSWEAR_BOT = (60, 70, 100)
HAIR_LIGHT_BASE = (75, 50, 38)
HAIR_LIGHT_HIGH = (115, 85, 65)


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


def _render_character(size: int, arm_angle_deg: float,
                      style: str = "muscle_man") -> Image.Image:
    """캐릭터를 size×size RGBA 로 렌더 — 슈퍼샘플링.

    style: 'muscle_man' (근육맨 반바지) / 'sport_woman' (스포츠 운동복)
    피벗: (W//2, W//2) — 회전 팔의 어깨 = 캐릭터 이미지 정중앙.
    """
    W = size * SS
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W // 2
    pivot_y = W // 2  # 회전 팔의 피벗 (가슴 중앙)

    is_woman = style == "sport_woman"
    hair_base = HAIR_LIGHT_BASE if is_woman else HAIR_BASE
    hair_high = HAIR_LIGHT_HIGH if is_woman else HAIR_HIGH

    # ── 머리 ──
    head_w = int(W * 0.13)
    head_h = int(W * 0.15)
    head_cy = pivot_y - head_h - int(W * 0.02)
    d.ellipse([cx - head_w, head_cy - head_h,
               cx + head_w, head_cy + head_h], fill=SKIN_BASE)
    d.chord([cx - head_w + 4, head_cy + 2,
             cx + head_w - 4, head_cy + head_h],
            start=10, end=170, fill=SKIN_SHADE)
    d.ellipse([cx - head_w, head_cy - head_h,
               cx + head_w, head_cy + head_h],
              outline=INK, width=int(SS * 3))

    if is_woman:
        # 긴 머리 — 옆으로 흘러내림 + 정수리 봉긋
        d.polygon([
            (cx - head_w + 4, head_cy - 4),
            (cx - head_w - 10, head_cy - head_h + 6),
            (cx - head_w // 2, head_cy - head_h - 14),
            (cx + head_w // 2, head_cy - head_h - 14),
            (cx + head_w + 10, head_cy - head_h + 6),
            (cx + head_w - 4, head_cy - 4),
        ], fill=hair_base)
        # 어깨 위로 내려오는 머리카락 (좌우)
        d.polygon([
            (cx - head_w - 4, head_cy + 2),
            (cx - head_w + 6, head_cy + head_h + int(W * 0.08)),
            (cx - head_w - 14, head_cy + head_h + int(W * 0.10)),
            (cx - head_w - 18, head_cy + head_h - 6),
        ], fill=hair_base)
        d.polygon([
            (cx + head_w + 4, head_cy + 2),
            (cx + head_w - 6, head_cy + head_h + int(W * 0.08)),
            (cx + head_w + 14, head_cy + head_h + int(W * 0.10)),
            (cx + head_w + 18, head_cy + head_h - 6),
        ], fill=hair_base)
    else:
        # 슬릭 백
        d.polygon([
            (cx - head_w + 6, head_cy - 6),
            (cx - head_w + 22, head_cy - head_h + 4),
            (cx - head_w // 3, head_cy - head_h - 14),
            (cx + head_w // 3, head_cy - head_h - 14),
            (cx + head_w - 22, head_cy - head_h + 4),
            (cx + head_w - 6, head_cy - 6),
            (cx + head_w - 10, head_cy - head_h // 2),
            (cx - head_w + 10, head_cy - head_h // 2),
        ], fill=hair_base)
    # 머리카락 하이라이트
    d.line([(cx - int(head_w * 0.5), head_cy - head_h + 4),
            (cx + int(head_w * 0.3), head_cy - head_h - 4)],
           fill=hair_high, width=int(SS * 3))

    # 눈
    eye_y = head_cy - 4
    eye_dx = int(head_w * 0.42)
    eye_w = int(head_w * 0.16)
    eye_h = int(head_h * 0.08)
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        d.ellipse([ex - eye_w, eye_y - eye_h,
                   ex + eye_w, eye_y + eye_h], fill=INK)
        bx0 = ex - eye_w - 2
        by0 = eye_y - eye_h - 14
        bx1 = ex + eye_w + 2
        by1 = eye_y - eye_h - 6
        d.line([(bx0, by0 if sign < 0 else by1),
                (bx1, by1 if sign < 0 else by0)],
               fill=INK, width=int(SS * 4))

    # 미소
    mouth_cx = cx + 6
    mouth_cy = head_cy + int(head_h * 0.40)
    d.arc([mouth_cx - 28, mouth_cy - 10, mouth_cx + 28, mouth_cy + 24],
          start=10, end=160, fill=INK, width=int(SS * 3))

    # ── 목 ── (머리 바닥에서 약간만 — 몸통이 위로 올라가서 길게 그릴 필요 X)
    neck_w = int(head_w * 0.4)
    neck_y0 = head_cy + head_h - 8
    neck_y1 = neck_y0 + int(W * 0.04)
    d.rectangle([cx - neck_w, neck_y0, cx + neck_w, neck_y1],
                fill=SKIN_SHADE)

    # ── 몸통 (V자, 피벗을 어깨선 기준) ──
    shoulder_w = int(W * (0.24 if is_woman else 0.27))
    waist_w = int(W * (0.13 if is_woman else 0.16))
    torso_h = int(W * 0.24)
    body_top = pivot_y - int(W * 0.03)
    body_bot = body_top + torso_h
    torso_pts = [
        (cx - shoulder_w, body_top),
        (cx + shoulder_w, body_top),
        (cx + waist_w, body_bot),
        (cx - waist_w, body_bot),
    ]
    d.polygon(torso_pts, fill=SKIN_BASE)

    if is_woman:
        # 스포츠 브라 — 가슴 라인 따라 띠 모양
        bra_top = body_top - int(W * 0.005)
        bra_bot = body_top + int(W * 0.075)
        bra_pts = [
            (cx - shoulder_w + 8, bra_top + 4),
            (cx + shoulder_w - 8, bra_top + 4),
            (cx + shoulder_w - 14, bra_bot),
            (cx - shoulder_w + 14, bra_bot),
        ]
        d.polygon(bra_pts, fill=SPORTSWEAR_TOP)
        # 브라 하단 곡선 (가슴 라인)
        d.arc([cx - shoulder_w + 14, bra_bot - 18,
               cx, bra_bot + 12],
              start=10, end=170, fill=SPORTSWEAR_SHADE, width=int(SS * 4))
        d.arc([cx, bra_bot - 18,
               cx + shoulder_w - 14, bra_bot + 12],
              start=10, end=170, fill=SPORTSWEAR_SHADE, width=int(SS * 4))
        # 어깨끈
        d.line([(cx - int(shoulder_w * 0.55), body_top + 2),
                (cx - int(shoulder_w * 0.55), head_cy + head_h - 10)],
               fill=SPORTSWEAR_TOP, width=int(SS * 6))
        d.line([(cx + int(shoulder_w * 0.55), body_top + 2),
                (cx + int(shoulder_w * 0.55), head_cy + head_h - 10)],
               fill=SPORTSWEAR_TOP, width=int(SS * 6))
        # 복근 라인 (살짝)
        abs_top = bra_bot + 14
        d.line([(cx, abs_top), (cx, body_bot - 10)],
               fill=SKIN_SHADE, width=int(SS * 3))
        for y_frac in (0.30, 0.65):
            ay = abs_top + int((body_bot - abs_top) * y_frac)
            d.arc([cx - 36, ay - 14, cx + 36, ay + 6],
                  start=200, end=340, fill=SKIN_SHADE, width=int(SS * 2))
    else:
        # 흉근 하이라이트
        pec_top = body_top + int(torso_h * 0.10)
        pec_mid = body_top + int(torso_h * 0.42)
        pec_w = int(shoulder_w * 0.85)
        d.polygon([(cx - pec_w, pec_top), (cx - 6, pec_top + 8),
                   (cx - 6, pec_mid), (cx - int(pec_w * 0.6), pec_mid)],
                  fill=SKIN_HIGH)
        d.polygon([(cx + 6, pec_top + 8), (cx + pec_w, pec_top),
                   (cx + int(pec_w * 0.6), pec_mid), (cx + 6, pec_mid)],
                  fill=SKIN_HIGH)
        d.line([(cx, pec_top + 12), (cx, pec_mid - 4)],
               fill=SKIN_SHADE, width=int(SS * 4))
        # 복근
        abs_top = pec_mid + 8
        d.line([(cx, abs_top), (cx, body_bot - 8)],
               fill=SKIN_SHADE, width=int(SS * 3))
        for y_frac in (0.30, 0.58, 0.80):
            ay = abs_top + int((body_bot - abs_top) * y_frac)
            d.arc([cx - 44, ay - 14, cx + 44, ay + 6],
                  start=200, end=340, fill=SKIN_SHADE, width=int(SS * 3))

    # 몸통 외곽선
    d.polygon(torso_pts, outline=INK, width=int(SS * 3))

    # ── 반대쪽 팔 (왼쪽 어깨에서 허리로 자연스럽게) ──
    arm_thick = int(W * (0.038 if is_woman else 0.045))
    off_sh_x = cx - shoulder_w + arm_thick
    off_sh_y = body_top + int(W * 0.005)
    off_el_x = off_sh_x - int(W * 0.07)
    off_el_y = off_sh_y + int(torso_h * 0.45)
    off_hand_x = cx - waist_w - int(W * 0.005)
    off_hand_y = off_sh_y + int(torso_h * 0.75)
    d.line([(off_sh_x, off_sh_y), (off_el_x, off_el_y)],
           fill=SKIN_BASE, width=int(arm_thick * 1.8))
    d.line([(off_el_x, off_el_y), (off_hand_x, off_hand_y)],
           fill=SKIN_BASE, width=int(arm_thick * 1.55))
    d.ellipse([off_hand_x - arm_thick, off_hand_y - arm_thick,
               off_hand_x + arm_thick, off_hand_y + arm_thick],
              fill=SKIN_BASE)

    # ── 하의 (반바지 / 운동복 쇼츠) ──
    shorts_top = body_bot
    shorts_h = int(W * (0.085 if is_woman else 0.10))
    sx0 = cx - waist_w - 4
    sx1 = cx + waist_w + 4
    shorts_color = SPORTSWEAR_BOT if is_woman else SHORTS_BASE
    shorts_shade = (40, 50, 75) if is_woman else SHORTS_SHADE
    d.rounded_rectangle([sx0, shorts_top, sx1, shorts_top + shorts_h],
                        radius=int(W * 0.014), fill=shorts_color)
    d.line([(cx, shorts_top + 4), (cx, shorts_top + shorts_h - 4)],
           fill=shorts_shade, width=int(SS * 3))
    d.rounded_rectangle([sx0, shorts_top, sx1, shorts_top + shorts_h],
                        radius=int(W * 0.014), outline=INK,
                        width=int(SS * 3))

    # ── 다리 ──
    leg_w = int(W * 0.05)
    leg_h = int(W * 0.13)
    legs_top = shorts_top + shorts_h
    for lx in (cx - waist_w // 2 - 3, cx + waist_w // 2 + 3):
        d.line([(lx, legs_top), (lx, legs_top + leg_h)],
               fill=SKIN_BASE, width=int(leg_w * 2.0))
        d.ellipse([lx - leg_w, legs_top + leg_h - 8,
                   lx + leg_w + 10, legs_top + leg_h + 20], fill=INK)

    # ── 회전 팔 (스피너) — 피벗 = 캔버스 정중앙 (cx, pivot_y) ──
    rad = math.radians(arm_angle_deg - 90)
    arm_len = int(W * 0.32)
    tip_x = cx + math.cos(rad) * arm_len
    tip_y = pivot_y + math.sin(rad) * arm_len
    arm_w = int(W * (0.038 if is_woman else 0.045))
    # 팔 본체
    d.line([(cx, pivot_y), (tip_x, tip_y)],
           fill=SKIN_BASE, width=int(arm_w * 2.2))
    # 어깨 둥글게 마무리
    d.ellipse([cx - int(arm_w * 1.1), pivot_y - int(arm_w * 1.1),
               cx + int(arm_w * 1.1), pivot_y + int(arm_w * 1.1)],
              fill=SKIN_BASE)
    # 바이셉 하이라이트
    midf = 0.45
    bx = cx + math.cos(rad) * arm_len * midf
    by = pivot_y + math.sin(rad) * arm_len * midf
    perp = rad + math.pi / 2
    hx = bx + math.cos(perp) * arm_w * 0.6
    hy = by + math.sin(perp) * arm_w * 0.6
    d.ellipse([hx - arm_w, hy - arm_w, hx + arm_w, hy + arm_w],
              fill=SKIN_HIGH)
    # 주먹
    hand_r = int(arm_w * 1.25)
    d.ellipse([tip_x - hand_r, tip_y - hand_r,
               tip_x + hand_r, tip_y + hand_r], fill=SKIN_BASE)
    # 검지
    f_len = int(arm_w * 1.6)
    fx = tip_x + math.cos(rad) * f_len
    fy = tip_y + math.sin(rad) * f_len
    d.line([(tip_x, tip_y), (fx, fy)],
           fill=SKIN_BASE, width=int(arm_w * 0.85))
    d.ellipse([fx - int(arm_w * 0.42), fy - int(arm_w * 0.42),
               fx + int(arm_w * 0.42), fy + int(arm_w * 0.42)],
              fill=SKIN_BASE)

    return layer.resize((size, size), Image.LANCZOS)


def _frame(title: str, hint: str, options: List[str], arm_angle: float,
           font_paths: dict, character_style: str) -> Image.Image:
    img = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(font_paths["Bold"], 78)
    f_hint = ImageFont.truetype(font_paths["Medium"], 38)
    f_opt = ImageFont.truetype(font_paths["Bold"], 40)

    tw = draw.textlength(title, font=f_title)
    draw.text(((CANVAS[0] - tw) / 2, 220), title, font=f_title, fill=INK)
    hw = draw.textlength(hint, font=f_hint)
    draw.text(((CANVAS[0] - hw) / 2, 340), hint, font=f_hint, fill=MUTED)

    # 옵션 링 — 중심 = 캐릭터 이미지 중앙 = 팔 피벗
    ring_cx, ring_cy = CANVAS[0] // 2, 1100
    r = 400
    for i, opt in enumerate(options):
        angle = (360 / len(options)) * i - 90
        rad = math.radians(angle)
        _draw_option_box(draw, opt, f_opt,
                         ring_cx + math.cos(rad) * r,
                         ring_cy + math.sin(rad) * r)

    char_size = 700
    character = _render_character(char_size, arm_angle, style=character_style)
    # 캐릭터 이미지 중앙 = 피벗 = ring_cx, ring_cy
    img.paste(character, (ring_cx - char_size // 2,
                          ring_cy - char_size // 2), character)
    return img


def make_pause_challenge_video(
    options: List[str],
    output_path: Path,
    title: str = "먹을지 vs 운동 갈지",
    hint: str = "⏸ 일시정지로 메뉴 골라봐!",
    duration_seconds: float = 8.0,
    character_style: str = "muscle_man",
):
    """일시정지 챌린지 — 팔이 무한 회전, 짝수 위치 옵션만 노출.

    character_style: 'muscle_man' / 'sport_woman'
    """
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
        img = _frame(title, hint, options, base + wobble,
                     font_paths, character_style)
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

