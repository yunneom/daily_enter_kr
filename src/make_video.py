"""
슬라이드쇼 mp4 빌더 — 9:16 카드 이미지 리스트 → mp4 + (선택) BGM mux.

[설계]
- FFmpeg 직접 호출. 카드별 가변 노출 시간 지원 (durations 리스트).
- BGM: bgm_path 지정 시 ffmpeg 가 자동 mux. 음원이 영상보다 짧으면 loop, 길면 -shortest 로 자름.
- 출력: 1080x1920, h264 high-profile, yuv420p, AAC 192kbps (BGM 있을 때).
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


def make_motion_video(
    image_path: Path,
    output_path: Path,
    duration: float = 18.0,
    bgm_path: Optional[Path] = None,
    motion: str = "kenburns_in",
) -> Path:
    """단일 정적 이미지에 Ken Burns(줌·팬) 모션 적용 → 동적 mp4.

    [왜] YouTube Shorts 알고리즘은 60s 미만 65% retention 임계. 정적 6s mp4 는
    시청자가 1초만에 스킵 → retention ~17% → 알고리즘 즉시 킬 → 0 view.
    Ken Burns 효과로 영상에 모션 줘서 retention + watch-time 신호 부스트.

    [모션 종류]
    - kenburns_in: 1.0x → 1.18x 천천히 줌인 (가장 자연스러움, 매트릭스 카드 보기 좋음)
    - kenburns_out: 1.18x → 1.0x 줌아웃 (호기심 자극 — 전체 → 디테일 → 풀)
    - pan_down: 위→아래 천천히 (긴 매트릭스 카드에 적합)

    [길이]
    18초 = YouTube Shorts sweet spot. 너무 짧으면(6초) "보자마자 끝" 신호 X.
    15-25초 구간이 retention·재생회수 양쪽에서 베스트.
    """
    _ensure_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = int(duration * FPS)
    if motion == "kenburns_in":
        # 줌 1.0 → 1.18 선형. d=총프레임 으로 한 번에 부드럽게.
        zoom_expr = f"min(zoom+0.0015,1.18)"
        # 중앙 약간 위쪽으로 (제목 영역 안 잘리게)
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2.6-(ih/zoom/2.6)"
    elif motion == "kenburns_out":
        zoom_expr = f"max(zoom-0.0015,1.0)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2.6-(ih/zoom/2.6)"
    else:  # pan_down
        zoom_expr = "1.18"
        x_expr = "iw/2-(iw/zoom/2)"
        # y 가 0 → ih*0.4 로 천천히 이동
        y_expr = f"(ih/zoom-ih/zoom*0.6)*on/{total_frames}"

    # 입력 해상도가 zoompan 후 출력 크기보다 작으면 scale 먼저
    vf = (
        f"scale=8000:-1,"  # 줌 화질 보존 위해 미리 확대 (메모리는 ffmpeg 가 알아서)
        f"zoompan=z='{zoom_expr}':"
        f"x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s={TARGET_W}x{TARGET_H}:fps={FPS},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
    ]
    if bgm_path and bgm_path.exists():
        cmd += ["-i", str(bgm_path)]
    cmd += [
        "-vf", vf,
        "-t", str(duration),
        "-r", str(FPS),
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if bgm_path and bgm_path.exists():
        cmd += [
            "-filter:a", f"volume={BGM_VOLUME},afade=t=in:st=0:d=0.4,"
                         f"afade=t=out:st={duration-0.5}:d=0.5",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
        ]
    else:
        cmd += ["-an"]
    cmd += [str(output_path)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg motion video 실패: {proc.stderr[-1500:]}")
    print(f"🎬 motion {motion} {duration}s → {output_path.name}")
    return output_path


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
        # AAC 128k → 192k. IG Reels 2026 알고리즘의 'audio fidelity' 신호 강화 목적.
        # 파일 크기 차이 미미(텍스트 reel 22s 기준 +150KB).
        "-c:a", "aac", "-b:a", "192k",
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
