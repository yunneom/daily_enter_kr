"""
슬라이드쇼 mp4 빌더 — 9:16 카드 이미지 리스트 → 단일 mp4 (h264, no audio).

[설계]
- FFmpeg concat demuxer 사용 (정렬 강제 위해)
- 카드당 SECONDS_PER_CARD 초씩 노출 + 카드 사이 짧은 페이드(crossfade)
- 출력: 1080x1920, h264 high-profile, yuv420p (IG Reels 호환)
- 오디오 트랙 없음 (BGM 필요 시 별도 단계로 mux)

[IG Reels 제약]
- 길이: 3~90초
- 비율: 9:16 권장 (1080x1920)
- 코덱: H.264 video, AAC audio(있다면) — 우리는 무음
- 컨테이너: MP4
"""

import shutil
import subprocess
from pathlib import Path
from typing import List


SECONDS_PER_CARD = 3.0      # 카드당 노출 시간
CROSSFADE_SEC = 0.4         # 카드 전환 페이드 길이 (0이면 컷)
TARGET_W, TARGET_H = 1080, 1920
FPS = 30


def _ensure_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg 가 PATH 에 없습니다. apt: 'apt-get install -y ffmpeg' / brew: 'brew install ffmpeg'"
        )


def make_slideshow_video(
    image_paths: List[Path],
    output_path: Path,
    seconds_per_card: float = SECONDS_PER_CARD,
    crossfade: float = CROSSFADE_SEC,
) -> Path:
    """이미지 리스트 → mp4 (h264, yuv420p, 무음).

    Args:
        image_paths: 카드 이미지 경로 리스트 (게시 순서대로)
        output_path: 출력 mp4 경로
        seconds_per_card: 카드당 노출 초
        crossfade: 카드 사이 페이드 길이(초). 0 이면 하드 컷.

    Returns: output_path
    """
    _ensure_ffmpeg()
    if not image_paths:
        raise ValueError("image_paths is empty")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # crossfade > 0 이면 filter_complex 로 합성(품질 좋음·코드 복잡), 0 이면 concat demuxer (단순).
    if crossfade > 0:
        cmd = _build_crossfade_cmd(image_paths, output_path, seconds_per_card, crossfade)
    else:
        cmd = _build_concat_cmd(image_paths, output_path, seconds_per_card)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # stderr 가 길어서 마지막 1500자만 표시 (디스크 사용량 안내·warning 컷)
        tail = proc.stderr[-1500:] if proc.stderr else "(no stderr)"
        raise RuntimeError(f"ffmpeg failed (rc={proc.returncode}):\n{tail}")
    return output_path


def _build_concat_cmd(image_paths: List[Path], output_path: Path,
                      seconds_per_card: float) -> List[str]:
    """간단한 concat demuxer — 컷 전환만."""
    # concat 데모서는 텍스트 파일 입력이 필요
    list_file = output_path.with_suffix(".txt")
    lines = []
    for p in image_paths:
        lines.append(f"file '{p.resolve()}'")
        lines.append(f"duration {seconds_per_card}")
    # concat demuxer 의 알려진 quirk: 마지막 파일은 duration 없이 한 번 더 명시해야 함
    lines.append(f"file '{image_paths[-1].resolve()}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    return [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
               f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:white,setsar=1,fps={FPS}",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(output_path),
    ]


def _build_crossfade_cmd(image_paths: List[Path], output_path: Path,
                         seconds_per_card: float, crossfade: float) -> List[str]:
    """xfade 체인으로 카드 간 페이드. 짧은 슬라이드쇼에 적합."""
    n = len(image_paths)
    # 입력: 각 이미지를 seconds_per_card 길이의 영상으로 (loop)
    inputs: List[str] = []
    for p in image_paths:
        inputs += [
            "-loop", "1",
            "-t", f"{seconds_per_card}",
            "-i", str(p.resolve()),
        ]

    # 각 입력을 9:16 캔버스에 맞춰 정규화
    fc_parts = []
    for i in range(n):
        fc_parts.append(
            f"[{i}:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:white,"
            f"setsar=1,fps={FPS},format=yuv420p[v{i}]"
        )

    # xfade 체인: [v0][v1] -> [x1], [x1][v2] -> [x2], ...
    last_label = "v0"
    offset = seconds_per_card - crossfade
    for i in range(1, n):
        out = f"x{i}" if i < n - 1 else "vout"
        fc_parts.append(
            f"[{last_label}][v{i}]xfade=transition=fade:duration={crossfade}:"
            f"offset={offset:.3f}[{out}]"
        )
        last_label = out
        offset += seconds_per_card - crossfade

    if n == 1:
        # 단일 카드는 xfade 가 의미 없음 → v0 그대로 사용
        last_label = "v0"

    filter_complex = ";".join(fc_parts)

    return [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-r", str(FPS),
        "-an",
        str(output_path),
    ]


if __name__ == "__main__":
    sample_dir = Path(__file__).parent.parent / "output" / "sample"
    images = sorted(sample_dir.glob("*.jpg"))
    if not images:
        print(f"❌ 샘플 이미지 없음. 먼저 'python src/make_card.py' 실행")
        raise SystemExit(1)

    out = sample_dir / "reel.mp4"
    print(f"🎬 {len(images)}장 → {out.name} (카드당 {SECONDS_PER_CARD}s, fade {CROSSFADE_SEC}s)")
    make_slideshow_video(images, out)
    print(f"✅ {out}")
