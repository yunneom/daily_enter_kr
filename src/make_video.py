"""
슬라이드쇼 mp4 빌더 — 9:16 카드 이미지 리스트 → mp4 + (선택) BGM mux.

[설계]
- FFmpeg 직접 호출. 카드별 가변 노출 시간 지원 (durations 리스트).
- BGM: bgm_path 지정 시 ffmpeg 가 자동 mux. 음원이 영상보다 짧으면 loop, 길면 -shortest 로 자름.
- 출력: 1080x1920, h264 high-profile, yuv420p, AAC 128kbps (BGM 있을 때).
- 카드 사이 짧은 xfade.

[IG Reels 제약]
- 길이 3-90초, 9:16 권장, H.264 + AAC, mp4 컨테이너.
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


SECONDS_PER_CARD = 2.5      # 본문 카드 기본 노출 시간
COVER_SECONDS = 1.5         # 표지(첫 카드)는 더 짧게 — 즉시 콘텐츠로 진입
CROSSFADE_SEC = 0.3         # 카드 전환 페이드
TARGET_W, TARGET_H = 1080, 1920
FPS = 30
BGM_VOLUME = 0.35           # BGM 볼륨 (0~1). 텍스트 카드라 너무 크면 산만함


def _ensure_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg 가 PATH 에 없습니다. apt: 'apt-get install -y ffmpeg' / brew: 'brew install ffmpeg'"
        )


def make_slideshow_video(
    image_paths: List[Path],
    output_path: Path,
    durations: Optional[List[float]] = None,
    crossfade: float = CROSSFADE_SEC,
    bgm_path: Optional[Path] = None,
    bgm_volume: float = BGM_VOLUME,
) -> Path:
    """이미지 리스트 → mp4 (h264, yuv420p). BGM 있으면 AAC 트랙 추가.

    Args:
        image_paths: 카드 이미지 경로 리스트 (순서대로)
        output_path: 출력 mp4 경로
        durations: 카드별 노출 초 리스트. None 이면 모든 카드 SECONDS_PER_CARD.
        crossfade: 카드 사이 페이드 (초)
        bgm_path: 선택적 BGM mp3. None 이면 무음.
        bgm_volume: 0~1, BGM 볼륨 배율.
    """
    _ensure_ffmpeg()
    if not image_paths:
        raise ValueError("image_paths is empty")

    if durations is None:
        durations = [SECONDS_PER_CARD] * len(image_paths)
    if len(durations) != len(image_paths):
        raise ValueError(f"durations({len(durations)}) != image_paths({len(image_paths)})")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1단계: 비디오만 빌드 (xfade 체인). filter_complex 가 안 복잡할 때 더 안정적.
    video_only = output_path.with_name(output_path.stem + "_v.mp4")
    cmd_v = _build_video_cmd(image_paths, durations, crossfade, video_only)
    _run_ffmpeg(cmd_v, step="video")

    # 2단계: BGM 있으면 mux (오디오 전용 패스 — 가볍고 빠름)
    if bgm_path:
        cmd_a = _build_mux_cmd(video_only, bgm_path, bgm_volume,
                               total_duration=sum(durations) - max(0, (len(image_paths) - 1) * crossfade),
                               output_path=output_path)
        _run_ffmpeg(cmd_a, step="mux")
        video_only.unlink(missing_ok=True)
    else:
        video_only.rename(output_path)
    return output_path


def _run_ffmpeg(cmd: List[str], step: str):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = proc.stderr[-1500:] if proc.stderr else "(no stderr)"
        raise RuntimeError(f"ffmpeg {step} failed (rc={proc.returncode}):\n{tail}")


def _build_video_cmd(image_paths: List[Path], durations: List[float],
                     crossfade: float, output_path: Path) -> List[str]:
    """비디오 트랙만 빌드 (xfade 체인). 오디오는 별도 mux 단계에서 처리."""
    n = len(image_paths)

    inputs: List[str] = []
    for p, d in zip(image_paths, durations):
        inputs += ["-loop", "1", "-t", f"{d:.3f}", "-i", str(p.resolve())]

    fc_parts = []
    for i in range(n):
        fc_parts.append(
            f"[{i}:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:white,"
            f"setsar=1,fps={FPS},format=yuv420p[v{i}]"
        )

    # xfade 체인. i-th xfade 의 offset = sum(durations[:i]) - i*crossfade
    if n == 1:
        map_label = "v0"
    else:
        last_label = "v0"
        cumulative = durations[0]
        for i in range(1, n):
            out = f"x{i}" if i < n - 1 else "vout"
            offset = cumulative - crossfade
            fc_parts.append(
                f"[{last_label}][v{i}]xfade=transition=fade:duration={crossfade}:"
                f"offset={offset:.3f}[{out}]"
            )
            last_label = out
            cumulative += durations[i] - crossfade
        map_label = last_label

    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", ";".join(fc_parts),
        "-map", f"[{map_label}]",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-r", str(FPS),
        "-an",
        str(output_path),
    ]


def _build_mux_cmd(video_path: Path, bgm_path: Path, bgm_volume: float,
                   total_duration: float, output_path: Path) -> List[str]:
    """완성된 mp4 비디오에 BGM 트랙 추가 (별도 인코딩 패스).

    BGM 이 영상보다 짧으면 -stream_loop -1 으로 반복 → -shortest 로 영상 길이에 맞춤.
    afade in/out 으로 자연스러운 entry/exit.
    """
    fade_out_start = max(0.0, total_duration - 1.5)
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path.resolve()),
        "-stream_loop", "-1", "-i", str(bgm_path.resolve()),
        "-filter_complex",
        f"[1:a]volume={bgm_volume},"
        f"afade=t=in:d=0.8,afade=t=out:st={fade_out_start:.2f}:d=1.5[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",  # 비디오 재인코딩 안 함 (속도 +, 품질 손실 0)
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]


if __name__ == "__main__":
    sample_dir = Path(__file__).parent.parent / "output" / "sample"
    images = sorted(sample_dir.glob("*.jpg"))
    if not images:
        print(f"❌ 샘플 이미지 없음. 먼저 'python src/make_card.py' 실행")
        raise SystemExit(1)

    # 카드 전부 균일 2.5초 (표지 제거됨)
    durations = [SECONDS_PER_CARD] * len(images)

    out = sample_dir / "reel.mp4"
    bgm_dir = Path(__file__).parent.parent / "assets" / "bgm"
    bgm = None
    if bgm_dir.exists():
        candidates = sorted(bgm_dir.glob("*.mp3"))
        if candidates:
            import random
            bgm = random.choice(candidates)
            print(f"🎵 BGM: {bgm.name}")

    total = sum(durations) - max(0, (len(images) - 1) * CROSSFADE_SEC)
    print(f"🎬 {len(images)}장 → {out.name} ({SECONDS_PER_CARD}s × {len(images)}, fade {CROSSFADE_SEC}s, ≈{total:.1f}s)")
    make_slideshow_video(images, out, durations=durations, bgm_path=bgm)
    print(f"✅ {out}")
