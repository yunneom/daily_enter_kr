"""
YouTube 채널 자산 생성 — 프로필 사진 + 채널 아트.

[톤]
인스타와 동일 — 핑크(#ff7eb6) → 옐로(#ffd166) → 민트(#06d6a0) 그라데이션 +
Pretendard 폰트. 우리 랜딩 페이지 / 캡션 / 자동 댓글과 통일된 브랜드 신호.

[규격]
- 프로필 사진: 800x800 (YT 최소 98, 권장 800+) — 원형으로 잘림
- 채널 아트(배너): 2560x1440 (전체 표시 안전 영역: 1546x423 중앙)
  · TV ~ 데스크탑 ~ 모바일 다 다른 크기로 잘림. 핵심 텍스트는 중앙 1546x423 안.

[출력]
docs/youtube/profile_800.png
docs/youtube/banner_2560x1440.png
"""

import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from make_card import _resolve_font

OUT_DIR = ROOT / "docs" / "youtube"


# 브랜드 컬러 (인스타 랜딩이랑 동일)
C_PINK = (255, 126, 182)
C_YELLOW = (255, 209, 102)
C_MINT = (6, 214, 160)
C_INK = (24, 24, 32)


def _gradient(size, colors, vertical=False):
    """다색 그라데이션 — colors 리스트를 균등 분할."""
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    n = len(colors) - 1
    for i in range(h if vertical else w):
        t = i / max((h if vertical else w) - 1, 1)
        idx = min(int(t * n), n - 1)
        local = t * n - idx
        c0 = colors[idx]; c1 = colors[idx + 1]
        c = tuple(int(c0[k] * (1 - local) + c1[k] * local) for k in range(3))
        if vertical:
            for x in range(w):
                px[x, i] = c
        else:
            for y in range(h):
                px[i, y] = c
    return img


def make_profile():
    """800x800 프로필 — 그라데이션 배경 + 중앙 emoji + 핸들."""
    size = 800
    img = _gradient((size, size), [C_PINK, C_YELLOW, C_MINT])
    img = img.filter(ImageFilter.GaussianBlur(radius=8))

    draw = ImageDraw.Draw(img)

    # 살짝 어두운 원형 오버레이 (텍스트 가독)
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.ellipse([60, 60, size - 60, size - 60],
                    fill=(255, 255, 255, 40))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    # 중앙 emoji (📰 — IG·랜딩이랑 동일)
    try:
        from make_comparison_matrix import _get_emoji_image
        em = _get_emoji_image("📰", 360)
        if em:
            img.alpha_composite(em, (size // 2 - 180, size // 2 - 220))
    except Exception:
        pass

    # 핸들 (하단)
    bold = _resolve_font("Bold")
    f_handle = ImageFont.truetype(bold, 64)
    handle = "@daily_enter_kr"
    bb = f_handle.getbbox(handle)
    hw = bb[2] - bb[0]
    draw.text(((size - hw) / 2, size - 200), handle, font=f_handle,
              fill=(255, 255, 255), stroke_width=3, stroke_fill=C_INK)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "profile_800.png"
    img.convert("RGB").save(out, "PNG", quality=95)
    print(f"✓ {out}")
    return out


def make_banner():
    """2560x1440 채널 아트 — 안전 영역 1546x423 중앙 텍스트."""
    W, H = 2560, 1440
    img = _gradient((W, H), [C_PINK, C_YELLOW, C_MINT])
    # 좌하/우상 방향 그라데이션 느낌으로 약간 회전 효과
    img = img.filter(ImageFilter.GaussianBlur(radius=20))
    draw = ImageDraw.Draw(img)

    # 안전 영역(TV-safe = 데스크/모바일 모두 노출): 중앙 1546x423
    # 우리는 더 좁게 1200x400 으로 잡아서 디바이스별 잘림 안전 확보
    safe_w, safe_h = 1200, 400
    sx0 = (W - safe_w) // 2
    sy0 = (H - safe_h) // 2

    # 핵심 카피 — 짧고 강한 hook
    bold = _resolve_font("Bold")
    medium = _resolve_font("Medium")
    f_main = ImageFont.truetype(bold, 130)
    f_sub = ImageFont.truetype(medium, 64)
    f_meta = ImageFont.truetype(medium, 44)

    main = "오늘의 K-연예 밸런스"
    sub = "매일 새로운 매트릭스 시리즈"
    meta = "📅 매일 KST 09 · 13 · 18시 · 새 영상"

    # 흰색 + 진한 INK 외곽선으로 어떤 배경색에서도 가독
    def centered(text, font, y, fill=(255, 255, 255)):
        bb = font.getbbox(text)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=fill,
                  stroke_width=4, stroke_fill=C_INK)

    centered(main, f_main, sy0 + 40)
    centered(sub,  f_sub,  sy0 + 200)
    centered(meta, f_meta, sy0 + 300)

    # 핸들 (좌측 상단, 작게)
    f_handle = ImageFont.truetype(bold, 56)
    draw.text((80, 60), "@daily_enter_kr", font=f_handle,
              fill=(255, 255, 255), stroke_width=3, stroke_fill=C_INK)

    out = OUT_DIR / "banner_2560x1440.png"
    img.save(out, "PNG", quality=95)
    print(f"✓ {out}")
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = make_profile()
    b = make_banner()
    print(f"\n사용법:")
    print(f"  1) {p} → YouTube Studio → 맞춤설정 → 브랜딩 → 사진")
    print(f"  2) {b} → 같은 메뉴 → 배너 이미지")
    return 0


if __name__ == "__main__":
    sys.exit(main())
