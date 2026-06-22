"""
월드컵 매치 영상 — 정적 카드 + 헤더 sparkle motion + BGM.

[모션 선택 근거]
Ken Burns(zoom) → 카드 가장자리 4지선다 텍스트가 잘려나감 = 안 됨.
대신 카드는 100% 정적, 상단 헤더(🏆 걸그룹 월드컵) 영역에 sparkle particle
오버레이만 깜빡임 → 시선 끌기 + 정보 100% 보존.

[성능]
30fps × duration 프레임. ✨ 이모지 사이즈 캐시 + PIL alpha_composite.
"""

import math
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from make_comparison_matrix import _get_emoji_image


FPS = 30
# 헤더(🏆 + "걸그룹 월드컵" 타이틀) 영역. 카드 본문(매치/4지선다)에는 영향 X.
SPARKLE_ZONE = (40, 40, 1040, 240)


def _gen_sparkles(seed: int, count: int) -> List[Tuple[int, int, int, float, float]]:
    """seed 기준 sparkle (x, y, base_size, phase, speed)."""
    rng = random.Random(seed)
    px0, py0, px1, py1 = SPARKLE_ZONE
    out = []
    for _ in range(count):
        x = rng.randint(px0 + 40, px1 - 40)
        y = rng.randint(py0 + 20, py1 - 20)
        size = rng.randint(48, 84)
        phase = rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(0.7, 1.4)  # 깜빡임 주기 (cycles/sec)
        out.append((x, y, size, phase, speed))
    return out


def make_worldcup_match_video(
    card_jpg: Path,
    output_path: Path,
    duration: float = 18.0,
    bgm_path: Optional[Path] = None,
    sparkle_count: int = 8,
) -> Path:
    """정적 카드 + sparkle motion → mp4. BGM 옵션."""
    base = Image.open(card_jpg).convert("RGBA")
    seed_int = hash(str(card_jpg)) & 0xffff
    sparkles = _gen_sparkles(seed_int, sparkle_count)

    # 사이즈 캐시 (사이즈 펄스 폭 ±12px, 4px 격자에 스냅)
    cache = {}
    def _get(em_size: int):
        sz = max(20, (em_size // 4) * 4)
        if sz not in cache:
            em = _get_emoji_image("✨", sz)
            if em:
                cache[sz] = em
        return cache.get(sz)

    tmp = Path("/tmp/wc_frames")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    n_frames = int(FPS * duration)
    for f in range(n_frames):
        t = f / FPS
        frame = base.copy()
        for (x, y, base_size, phase, speed) in sparkles:
            v = (math.sin(t * speed * 2 * math.pi + phase) + 1) / 2  # 0~1
            cur_size = base_size + int(v * 16) - 8
            em = _get(cur_size)
            if em is None:
                continue
            # 투명도 0.35 ~ 1.0
            opacity = int(89 + v * 166)
            em_a = em.copy()
            alpha = em_a.split()[3].point(lambda p, op=opacity: int(p * op / 255))
            em_a.putalpha(alpha)
            ox = x - cur_size // 2
            oy = y - cur_size // 2
            frame.alpha_composite(em_a, (ox, oy))

        frame.convert("RGB").save(tmp / f"f{f:04d}.jpg", quality=88)

    # ffmpeg
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if bgm_path and Path(bgm_path).exists():
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", str(tmp / "f%04d.jpg"),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-t", str(duration),
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
            "-i", str(tmp / "f%04d.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            str(out),
        ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-800:]}")
    return out


# ─── 캡션 / 자동 댓글 — 1·2·3·4 안내 명확히 ───

def build_worldcup_caption(round_label: str, post_idx: int, post_total: int,
                            match1: dict, match2: dict,
                            source_date: str = "2026.6.21") -> str:
    """본문 캡션 — 매치 정보 + 4지선다 + 팔로우 CTA + 출처 + 해시태그."""
    a, b = match1["a"], match1["b"]
    c, d = match2["a"], match2["b"]
    hashtags = [
        "#걸그룹월드컵", "#월드컵토너먼트", "#아이돌투표", "#밸런스게임",
        "#케이팝", "#kpop", "#kpopfan", "#아이돌조합",
        "#카드뉴스", "#일상공감", "#밈", "#릴스", "#reels",
        f"#{a['group']}", f"#{b['group']}", f"#{c['group']}", f"#{d['group']}",
        f"#{a['member']}", f"#{b['member']}", f"#{c['member']}", f"#{d['member']}",
    ]
    # 중복 제거 + 30개 한도
    seen, uniq = set(), []
    for h in hashtags:
        k = h.lower()
        if k not in seen:
            seen.add(k); uniq.append(h)
        if len(uniq) >= 30:
            break

    lines = [
        f"🏆 걸그룹 월드컵 {round_label} · {post_idx}/{post_total}",
        "",
        f"매치 1: {a['member']} ({a['group']}) vs {b['member']} ({b['group']})",
        f"매치 2: {c['member']} ({c['group']}) vs {d['member']} ({d['group']})",
        "",
        "💬 댓글에 본인 픽 번호 ⬇️ (1·2·3·4 중 하나)",
        f"  1️⃣ {a['member']} + {c['member']}",
        f"  2️⃣ {a['member']} + {d['member']}",
        f"  3️⃣ {b['member']} + {c['member']}",
        f"  4️⃣ {b['member']} + {d['member']}",
        "",
        "🏆 결승까지 매 라운드 알림받기:",
        "  → 팔로우 + 알림(🔔) ON",
        "  → 친구 소환해서 픽 대결",
        "  → 스토리에 본인 픽 공유",
        "",
        f"📊 출처: 한국기업평판연구소 {source_date}",
        "",
        " ".join(uniq),
    ]
    return "\n".join(lines)


def build_worldcup_auto_comment(match1: dict, match2: dict) -> str:
    """자동 첫 댓글 — 캡션 핵심만 간결히. 댓글 노출이 가장 강한 신호라
    번호 안내가 댓글에 다시 나와야 시청자가 바로 행동."""
    a, b = match1["a"], match1["b"]
    c, d = match2["a"], match2["b"]
    return "\n".join([
        "💬 본인 픽 번호 댓글로 ⬇️",
        f"1️⃣ {a['member']} + {c['member']}",
        f"2️⃣ {a['member']} + {d['member']}",
        f"3️⃣ {b['member']} + {c['member']}",
        f"4️⃣ {b['member']} + {d['member']}",
        "",
        "👯 친구 소환 → 둘이서 픽 대결!",
        "🔔 팔로우 + 알림 ON = 다음 매치 자동 안내",
    ])


if __name__ == "__main__":
    import json
    ROOT = Path(__file__).parent.parent
    card = ROOT / "output_enter" / "publish" / "worldcup_r32" / "post_01.jpg"
    mp4 = ROOT / "output_enter" / "publish" / "worldcup_r32" / "post_01.mp4"
    bgm = ROOT / "assets" / "bgm" / "daily_enter_theme_c.mp3"
    make_worldcup_match_video(card, mp4, duration=18.0,
                              bgm_path=bgm if bgm.exists() else None)
    print(f"✓ {mp4} ({mp4.stat().st_size // 1024} KB)")

    # 캡션·댓글 텍스트 미리보기
    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text(encoding="utf-8"))
    p = bracket["rounds"]["R32"]["posts"][0]
    print()
    print("=" * 60)
    print("📋 본문 캡션 (IG/YT 공통):")
    print("=" * 60)
    print(build_worldcup_caption("32강", p["post_idx"] + 1, 8, p["match1"], p["match2"]))
    print()
    print("=" * 60)
    print("💬 자동 첫 댓글:")
    print("=" * 60)
    print(build_worldcup_auto_comment(p["match1"], p["match2"]))
