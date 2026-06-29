"""
HyperFrames-style HTML → mp4 렌더 헬퍼.

HyperFrames CLI 가 있으면 그걸 쓰고, 없으면 Playwright Python + ffmpeg 로
프레임 캡처 → 인코딩. 로컬과 GitHub Actions 모두 동작.

[환경]
- 로컬: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers (자동 탐지)
- Actions: playwright install chromium 를 이 스크립트가 직접 수행 (lazy)

[사용]
python scripts/render_hf.py <html_path> <output_mp4> [--duration 6] [--fps 30]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _ensure_playwright():
    """Playwright + Chromium 가 없으면 lazy 설치."""
    try:
        from playwright.sync_api import sync_playwright  # noqa
        return True
    except ImportError:
        print("→ playwright 설치 중...")
        rc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright", "-q"]
        ).returncode
        if rc != 0:
            print("❌ playwright pip 설치 실패")
            return False
    # chromium 바이너리 설치
    print("→ playwright chromium 설치 중...")
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps", "-q"],
        check=False
    )
    return True


def render_with_playwright(html_path: Path, output: Path,
                           duration: float = 6.0, fps: int = 30) -> int:
    """Playwright Python 으로 프레임 캡처 → ffmpeg 인코딩."""
    if not _ensure_playwright():
        return 1
    if not _which("ffmpeg"):
        print("❌ ffmpeg 미설치")
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ playwright import 실패")
        return 1

    n_frames = int(duration * fps)
    frames_dir = Path("/tmp/hf_frames")
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ Playwright 프레임 캡처 시작 ({n_frames}개, {fps}fps, {duration}s)...")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-gpu", "--disable-dev-shm-usage",
                      "--font-render-hinting=none"],
            )
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            url = f"file://{html_path.resolve()}"
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_function("document.fonts.ready", timeout=10000)

            for i in range(n_frames):
                t_ms = (i / fps) * 1000
                page.evaluate(f"""() => {{
                    document.getAnimations().forEach(a => {{
                        try {{ a.pause(); a.currentTime = {t_ms}; }} catch(e) {{}}
                    }});
                }}""")
                frame_path = str(frames_dir / f"f{i:04d}.jpg")
                page.screenshot(path=frame_path, type="jpeg", quality=90,
                                clip={"x": 0, "y": 0, "width": 1080, "height": 1920})

            browser.close()
    except Exception as e:
        print(f"❌ Playwright 캡처 실패: {e}")
        return 1

    print("→ ffmpeg 인코딩...")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-framerate", str(fps),
           "-i", str(frames_dir / "f%04d.jpg"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           str(output)]
    rc = subprocess.run(cmd).returncode
    shutil.rmtree(frames_dir, ignore_errors=True)
    if rc != 0:
        print(f"❌ ffmpeg 실패 (rc={rc})")
        return rc
    print(f"✅ {output} ({output.stat().st_size // 1024}KB)")
    return 0


def render_html_to_mp4(html_path: Path, output: Path,
                       duration: float = 6.0, fps: int = 30) -> int:
    """Public entry — HyperFrames CLI 시도 → Playwright fallback."""
    if _which("hyperframes"):
        cmd = ["hyperframes", "render", str(html_path),
               "--output", str(output),
               "--duration", str(duration),
               "--quality", "standard"]
        rc = subprocess.run(cmd).returncode
        if rc == 0 and output.exists():
            return 0
        print(f"⚠️  hyperframes CLI 실패 (rc={rc}) — Playwright fallback")
    return render_with_playwright(html_path, output, duration, fps)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("html")
    p.add_argument("output")
    p.add_argument("--duration", type=float, default=6.0)
    p.add_argument("--fps", type=int, default=30)
    args = p.parse_args()
    return render_html_to_mp4(Path(args.html), Path(args.output),
                              args.duration, args.fps)


if __name__ == "__main__":
    sys.exit(main())
