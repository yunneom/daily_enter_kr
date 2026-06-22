"""
시그니처 사운드 단독 YT 영상 생성 — mp3 + 정적 이미지 → 30s mp4.

[목적]
@daily_enter_kr YT 채널에 "Daily Enter Theme" 단독 영상으로 업로드 →
YT 음원 페이지 생성 → 모든 매트릭스/슬롯/월드컵 영상의 시그니처 사운드 식별.

[출력]
output_enter/publish/signature_theme_a.mp4 (밝은 톤 — 매트릭스/일반용)
output_enter/publish/signature_theme_c.mp4 (게임 톤 — 슬롯/월드컵용)
"""

import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from make_card import _resolve_font

ROOT = Path(__file__).parent.parent
CANVAS = (1080, 1920)


def _font(weight, size):
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _build_cover(variant: str, output: Path):
    """시그니처 정적 이미지 — A 는 밝은 톤 / C 는 다크 게임 톤."""
    if variant == "A":
        top, bot = (255, 126, 182), (6, 214, 160)  # 핑크 → 민트
        ink_color = (24, 24, 32)
        sub_color = (60, 30, 50)
        sub_text = "K-pop · Hyper-pop · Bright"
    else:  # C
        top, bot = (24, 26, 72), (160, 36, 110)  # 네이비 → 마젠타
        ink_color = (255, 255, 255)
        sub_color = (255, 220, 120)
        sub_text = "Game · Slot · Intense"

    img = _vgrad(CANVAS, top, bot).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 메인 타이틀
    tf = _font("Bold", 160)
    title = "Daily"
    bb = tf.getbbox(title)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) / 2, 580), title, font=tf, fill=ink_color,
           stroke_width=4, stroke_fill=sub_color)

    title2 = "Enter"
    tf2 = _font("Bold", 200)
    bb = tf2.getbbox(title2)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) / 2, 740), title2, font=tf2, fill=ink_color,
           stroke_width=5, stroke_fill=sub_color)

    title3 = "Theme"
    tf3 = _font("Bold", 130)
    bb = tf3.getbbox(title3)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) / 2, 970), title3, font=tf3, fill=sub_color,
           stroke_width=3, stroke_fill=ink_color)

    # variant 라벨
    vf = _font("Bold", 90)
    vtext = f"・{variant}・"
    bb = vf.getbbox(vtext)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) / 2, 1130), vtext, font=vf, fill=ink_color,
           stroke_width=2, stroke_fill=sub_color)

    # 부제
    sf = _font("Medium", 48)
    bb = sf.getbbox(sub_text)
    tw = bb[2] - bb[0]
    d.text(((CANVAS[0] - tw) / 2, 1260), sub_text, font=sf, fill=sub_color)

    # 브랜드
    bf = _font("Bold", 56)
    brand = "@daily_enter_kr"
    bb = bf.getbbox(brand)
    bw = bb[2] - bb[0]
    d.text(((CANVAS[0] - bw) / 2, 1700), brand, font=bf, fill=ink_color,
           stroke_width=2, stroke_fill=sub_color)

    output.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output, "JPEG", quality=94)


def _build_video(cover: Path, mp3: Path, output: Path, duration: int = 30):
    """정적 이미지 + mp3 → mp4. duration 길면 음원 loop."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(cover),
        "-stream_loop", "-1", "-i", str(mp3),
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def main():
    bgm_dir = ROOT / "assets" / "bgm"
    out_dir = ROOT / "output_enter" / "publish"
    out_dir.mkdir(parents=True, exist_ok=True)

    for variant, mp3_name in [("A", "daily_enter_theme_a.mp3"),
                              ("C", "daily_enter_theme_c.mp3")]:
        mp3 = bgm_dir / mp3_name
        cover = out_dir / f"signature_theme_{variant.lower()}_cover.jpg"
        mp4 = out_dir / f"signature_theme_{variant.lower()}.mp4"
        _build_cover(variant, cover)
        _build_video(cover, mp3, mp4, duration=30)
        print(f"  ✓ {mp4.relative_to(ROOT)} ({mp4.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
