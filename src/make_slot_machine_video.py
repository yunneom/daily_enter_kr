"""
슬롯머신 매트릭스 — 3열이 서로 다른 방향으로 끊임없이 스크롤.
시청자가 일시정지(IG: 길게누름 / YT: 탭) 시 중앙 빨강 zone 에 들어온 멤버 3명이 그 사람의 픽.

[메커닉]
- 3열 × 5명/열 = 5^3 = 125가지 조합 (만원 fixed 9-cell 대비 압도적 풍부)
- 1열↑ / 2열↓ / 3열↑ — 서로 다른 방향이라 한 손가락으로 다 잡기 어려움 = 재시도 유발
- "기회 3번" rule: 재생/일시정지 3번 안에 원하는 조합 만들기 → 자연스러운 재생 + 댓글 유도
- 중앙 행에 빨강 박스 = landing zone

[프레임]
30fps × 10s = 300 frames. 셀은 사전 렌더(125 cache hit) + 정적 base 사전 합성.
열별 strip 은 모듈러 스크롤 (offset_abs % (n*CELL_H)).

[출력]
mp4 9:16 1080x1920. publish_matrix.py 가 BGM mux 안 함 — make_motion_video 와 달리
이 함수가 자체 ffmpeg 호출로 끝.
"""

import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image


CANVAS = (1080, 1920)
FPS = 30
DEFAULT_DURATION = 10.0
SPEED_PX_PER_SEC = 520  # 약 1.8 셀/초 (셀 580ms 노출) — 멈추기 적당히 까다로움

# 셀 (열 너비 × 셀 높이) — 3열 × 320 + 2 gap × 20 = 1000 (1080 캔버스에 40 마진)
CELL_W = 320
CELL_H = 280
GAP = 20

# 슬롯 영역 — 세로 3 셀 보임 (위 1, 중앙=빨강 1, 아래 1)
SLOT_TOP = 500
SLOT_VISIBLE_H = 3 * CELL_H
LANDING_TOP = SLOT_TOP + CELL_H
LANDING_BOTTOM = SLOT_TOP + 2 * CELL_H

# 색
BG = (255, 251, 240)
INK = (24, 24, 32)
RED = (220, 60, 60)
RED_FILL = (220, 60, 60, 28)
GOLD = (255, 220, 120)
MUTED = (140, 140, 140)


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    p = _resolve_font(weight)
    return ImageFont.truetype(p, size)


def _render_cell(member: dict) -> Image.Image:
    """엠블럼-스타일 셀 — 흰 카드 + 역할 이모지 + 멤버명 + 그룹."""
    w, h = CELL_W, CELL_H
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    # 외곽
    d.rounded_rectangle([6, 6, w - 6, h - 6], radius=22,
                        outline=INK, width=3)
    # 역할 이모지
    em = _get_emoji_image(member.get("role_emoji", ""), 110)
    if em:
        img.alpha_composite(em, ((w - 110) // 2, 28))
    # 멤버명
    name = member.get("name", "")
    fnt = _font("Bold", 54)
    bb = fnt.getbbox(name)
    nw = bb[2] - bb[0]
    d.text(((w - nw) // 2, 162), name, font=fnt, fill=INK)
    # 그룹명
    sub = member.get("subtitle", "")
    if sub:
        fs = _font("Medium", 30)
        bb = fs.getbbox(sub)
        sw = bb[2] - bb[0]
        d.text(((w - sw) // 2, 224), sub, font=fs, fill=MUTED)
    return img


def _build_base(title: str, rule_hint: str, chances_text: str,
                col_headers: List[str], col_xs: List[int],
                cta: str, brand: str) -> Image.Image:
    """프레임마다 동일한 정적 레이어 — header / 컬럼헤더 / footer."""
    base = Image.new("RGBA", CANVAS, BG + (255,))
    d = ImageDraw.Draw(base)

    # 제목
    title_f = _font("Bold", 78)
    bb = title_f.getbbox(title)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) // 2, 80), title, font=title_f, fill=INK)

    # 룰
    rule_f = _font("Medium", 40)
    bb = rule_f.getbbox(rule_hint)
    rw = bb[2] - bb[0]
    d.text(((CANVAS[0] - rw) // 2, 190), rule_hint, font=rule_f, fill=MUTED)

    # 기회 인디케이터 — "🎰 기회 3번"
    ch_f = _font("Bold", 52)
    bb = ch_f.getbbox(chances_text)
    cw = bb[2] - bb[0]
    d.text(((CANVAS[0] - cw) // 2, 260), chances_text,
           font=ch_f, fill=RED)

    # 컬럼 헤더
    hf = _font("Bold", 42)
    for i, hdr in enumerate(col_headers):
        bb = hf.getbbox(hdr)
        hw = bb[2] - bb[0]
        d.text((col_xs[i] + (CELL_W - hw) // 2, SLOT_TOP - 62),
               hdr, font=hf, fill=INK)

    # CTA 하단
    cta_f = _font("Bold", 40)
    bb = cta_f.getbbox(cta)
    cw = bb[2] - bb[0]
    d.text(((CANVAS[0] - cw) // 2, 1800), cta, font=cta_f, fill=INK)

    # 브랜드
    bf = _font("Medium", 28)
    bb = bf.getbbox(brand)
    bw = bb[2] - bb[0]
    d.text(((CANVAS[0] - bw) // 2, 1860), brand, font=bf, fill=MUTED)

    return base


def _build_landing_overlay(col_xs: List[int]) -> Image.Image:
    """빨강 landing zone — strip 위에 매 프레임 합성."""
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    x0 = col_xs[0] - 12
    x1 = col_xs[2] + CELL_W + 12
    # 살짝 반투명 빨강 fill 로 강조
    d.rectangle([x0, LANDING_TOP - 8, x1, LANDING_BOTTOM + 8],
                fill=RED_FILL)
    # 두꺼운 외곽선
    d.rectangle([x0, LANDING_TOP - 8, x1, LANDING_BOTTOM + 8],
                outline=RED, width=10)
    # 좌측 화살표 라벨 "PICK"
    pf = _font("Bold", 36)
    label = "▶ PICK"
    d.text((x0 - 130, LANDING_TOP + CELL_H // 2 - 18), label,
           font=pf, fill=RED)
    return overlay


def make_slot_machine_video(
    title: str,
    rule_hint: str,
    col_headers: List[str],
    col_pools: List[List[dict]],
    output_path: Path,
    chances_text: str = "🎰 기회 3번",
    duration: float = DEFAULT_DURATION,
    cta: str = "⏸ 일시정지로 멈춰서 조합 댓글 ⬇️",
    brand: str = "@daily_enter_kr · 매일 새로운 픽",
    bgm_path: Optional[Path] = None,
) -> Path:
    """3열 슬롯머신 mp4 생성."""
    if len(col_pools) != 3 or len(col_headers) != 3:
        raise ValueError("3열 전용 — col_pools/col_headers 길이 3")
    if not all(len(p) >= 3 for p in col_pools):
        raise ValueError("열당 최소 3 멤버 필요 (5 권장)")

    # 셀 사전 렌더 — 한 멤버 1번만 그림
    cells_per_col = [[_render_cell(m) for m in pool] for pool in col_pools]
    n_per_col = [len(p) for p in col_pools]

    # 열 X 좌표 (중앙 정렬)
    total_w = 3 * CELL_W + 2 * GAP
    start_x = (CANVAS[0] - total_w) // 2
    col_xs = [start_x + i * (CELL_W + GAP) for i in range(3)]

    # 정적 base + landing 오버레이 사전 합성
    base = _build_base(title, rule_hint, chances_text,
                       col_headers, col_xs, cta, brand)
    landing = _build_landing_overlay(col_xs)

    # 스크롤 방향 — 1열↑, 2열↓, 3열↑
    dirs = [-1, +1, -1]

    tmp = Path("/tmp/slot_frames")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)

    n_frames = int(FPS * duration)
    for f in range(n_frames):
        t = f / FPS
        frame = base.copy()

        for i, cells in enumerate(cells_per_col):
            modulo = n_per_col[i] * CELL_H
            offset_abs = SPEED_PX_PER_SEC * t
            if dirs[i] == -1:  # 위로 흐름
                offset = offset_abs % modulo
            else:              # 아래로 흐름
                offset = (-offset_abs) % modulo
            offset = int(offset)

            first_idx = offset // CELL_H
            first_y = -(offset % CELL_H)

            # 열 클리핑 영역 (CELL_W × SLOT_VISIBLE_H)
            col_clip = Image.new("RGBA", (CELL_W, SLOT_VISIBLE_H), (0, 0, 0, 0))
            # 4개 셀 그리면 보이는 3 셀 영역 충분히 채움
            for j in range(4):
                idx = (first_idx + j) % n_per_col[i]
                y = first_y + j * CELL_H
                col_clip.alpha_composite(cells[idx], (0, y))
            frame.alpha_composite(col_clip, (col_xs[i], SLOT_TOP))

        # 빨강 landing zone — strip 위에 덮어 그림
        frame.alpha_composite(landing)

        frame.convert("RGB").save(tmp / f"frame_{f:04d}.jpg", quality=88)

    # ffmpeg encode (+ BGM mux 옵션)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if bgm_path and Path(bgm_path).exists():
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", str(tmp / "frame_%04d.jpg"),
            "-i", str(bgm_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-filter:a", "volume=0.35",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", str(tmp / "frame_%04d.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            str(out),
        ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-800:]}")
    return out


if __name__ == "__main__":
    # 샘플 — 걸그룹 5x3 (5세대 + 4세대 섞은 풍부한 풀)
    sample_pools = [
        # 메인보컬 5
        [{"role_emoji": "🎤", "name": "카리나", "subtitle": "에스파"},
         {"role_emoji": "🎤", "name": "민지", "subtitle": "뉴진스"},
         {"role_emoji": "🎤", "name": "안유진", "subtitle": "IVE"},
         {"role_emoji": "🎤", "name": "김채원", "subtitle": "르세라핌"},
         {"role_emoji": "🎤", "name": "닝닝", "subtitle": "에스파"}],
        # 메인댄서 5
        [{"role_emoji": "💃", "name": "카즈하", "subtitle": "르세라핌"},
         {"role_emoji": "💃", "name": "하니", "subtitle": "뉴진스"},
         {"role_emoji": "💃", "name": "지젤", "subtitle": "에스파"},
         {"role_emoji": "💃", "name": "사쿠라", "subtitle": "르세라핌"},
         {"role_emoji": "💃", "name": "해린", "subtitle": "뉴진스"}],
        # 비주얼 5
        [{"role_emoji": "✨", "name": "장원영", "subtitle": "IVE"},
         {"role_emoji": "✨", "name": "윈터", "subtitle": "에스파"},
         {"role_emoji": "✨", "name": "리즈", "subtitle": "IVE"},
         {"role_emoji": "✨", "name": "허윤진", "subtitle": "르세라핌"},
         {"role_emoji": "✨", "name": "다니엘", "subtitle": "뉴진스"}],
    ]
    out = Path("output_enter/publish/slot_idol_girlgroup_5x3.mp4")
    make_slot_machine_video(
        title="🎰 슬롯머신 걸그룹 조합",
        rule_hint="멈춰서 본인 픽 만들기!",
        col_headers=["메인보컬", "메인댄서", "비주얼"],
        col_pools=sample_pools,
        output_path=out,
        chances_text="🎰 기회 3번 — 일시정지로 멈춰!",
        duration=10.0,
    )
    print(f"✓ {out} ({out.stat().st_size // 1024} KB)")
