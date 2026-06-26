"""
HyperFrames-style HTML → mp4 렌더 헬퍼.

HyperFrames CLI 가 환경에 설치되어 있으면 그것을, 안 되면 puppeteer-core +
Chromium + ffmpeg fallback 으로 직접 캡처. Actions ubuntu-latest 에 chromium
설치 가정.

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


def render_with_puppeteer(html_path: Path, output: Path, duration: float = 6.0,
                          fps: int = 30) -> int:
    """puppeteer-core + Chromium 으로 프레임 캡처 → ffmpeg 인코딩."""
    chromium = (shutil.which("chromium-browser") or shutil.which("chromium")
                or shutil.which("google-chrome") or "/usr/bin/chromium-browser")
    if not Path(chromium).exists() and not shutil.which(chromium):
        print(f"❌ Chromium 미설치: {chromium}")
        return 1
    if not _which("ffmpeg"):
        print("❌ ffmpeg 미설치")
        return 1

    n_frames = int(duration * fps)
    frames_dir = Path("/tmp/hf_frames")
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Node 스크립트 작성 — page.evaluate 로 currentTime 강제 + screenshot
    node_script = f"""
const puppeteer = require('puppeteer-core');
(async () => {{
  const browser = await puppeteer.launch({{
    executablePath: '{chromium}',
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-gpu',
           '--disable-dev-shm-usage','--font-render-hinting=none'],
    headless: 'new',
  }});
  const page = await browser.newPage();
  await page.setViewport({{ width:1080, height:1920, deviceScaleFactor:1 }});
  await page.goto('file://{html_path.resolve()}', {{ waitUntil:'networkidle0' }});
  // 폰트 로딩 대기
  await page.evaluate(() => document.fonts.ready);
  const N = {n_frames};
  const FPS = {fps};
  for (let i=0; i<N; i++) {{
    const t = i / FPS;
    // 모든 애니메이션의 currentTime 을 명시적으로 t 로 설정 — 결정론적 렌더
    await page.evaluate((tt) => {{
      document.getAnimations().forEach(a => {{
        try {{ a.pause(); a.currentTime = tt * 1000; }} catch (e) {{}}
      }});
    }}, t);
    await page.screenshot({{
      path: '/tmp/hf_frames/f' + String(i).padStart(4,'0') + '.jpg',
      type:'jpeg', quality:90
    }});
  }}
  await browser.close();
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
    script_path = Path("/tmp/hf_render.js")
    script_path.write_text(node_script, encoding="utf-8")

    # puppeteer-core 글로벌 설치 확인
    pup_check = subprocess.run(
        ["node", "-e", "require.resolve('puppeteer-core')"],
        capture_output=True, env={"NODE_PATH": "/usr/lib/node_modules", **__import__("os").environ})
    if pup_check.returncode != 0:
        print("→ puppeteer-core 설치 중...")
        subprocess.run(["npm", "install", "-g", "puppeteer-core"], check=False)

    import os
    env = os.environ.copy()
    env["NODE_PATH"] = "/usr/lib/node_modules:" + env.get("NODE_PATH", "")
    print(f"→ 프레임 캡처 시작 ({n_frames}개)...")
    rc = subprocess.run(["node", str(script_path)], env=env).returncode
    if rc != 0:
        print(f"❌ 프레임 캡처 실패 (rc={rc})")
        return rc

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
    """Public — HyperFrames CLI 시도 → 실패 시 puppeteer fallback."""
    if _which("hyperframes"):
        cmd = ["hyperframes", "render", str(html_path),
               "--output", str(output),
               "--duration", str(duration),
               "--quality", "standard"]
        rc = subprocess.run(cmd).returncode
        if rc == 0 and output.exists():
            return 0
        print(f"⚠️  hyperframes CLI 실패 (rc={rc}) — puppeteer fallback")
    return render_with_puppeteer(html_path, output, duration, fps)


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
