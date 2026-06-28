"""
16강 홍보 블라스트 — 4종 콘텐츠 즉시 게시

#1 전체 8매치 캐러셀   (기존 post_01-04.jpg → 4-image carousel)
#2 투표 D-1 티저 카드  (PIL → 단일 이미지)
#3 A/B/C/D 조별 릴스  (조별 재그루핑 매치카드 → mp4 Reels × 4)
#4 HyperFrames 릴스   (r16_announce.html → 로컬 puppeteer 렌더 → Reels)

[사용]
python scripts/worldcup_promo_blast.py [--skip 1 2 3 4]
  --skip 번호로 해당 파트 건너뜀
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont
from make_card import _resolve_font
from make_comparison_matrix import _get_emoji_image
from make_worldcup_match_card import make_worldcup_match_card
from make_worldcup_match_video import make_worldcup_match_video, build_worldcup_caption
from post_instagram import InstagramPublisher, upload_image, upload_video
import post_ledger
from notify import notify_discord


# ── 색상 상수 (make_worldcup_bracket_card 와 통일) ──
CANVAS = (1080, 1920)
WHITE = (255, 255, 255)
INK = (24, 24, 32)
BG_TOP = (28, 22, 68)
BG_BOT = (78, 28, 96)
GOLD = (255, 220, 120)
PINK = (255, 102, 184)
WHITE_DIM = (220, 215, 235)

ZONE_NAMES = ["A조", "B조", "C조", "D조"]
ZONE_EMOJIS = ["👑", "🌹", "🦋", "💎"]


def _font(weight, size):
    return ImageFont.truetype(_resolve_font(weight), size)


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[k] * (1 - t) + bot[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def _cx(draw, text, font, cx, y, fill=WHITE, stroke=0, sfill=INK):
    bb = font.getbbox(text)
    w = bb[2] - bb[0]
    kw = dict(font=font, fill=fill)
    if stroke:
        kw["stroke_width"] = stroke
        kw["stroke_fill"] = sfill
    draw.text((cx - w / 2, y), text, **kw)


# ──────────────────────────────────────────────
#  PART #2 — 투표 D-1 티저 카드
# ──────────────────────────────────────────────

def make_teaser_card(zone_matches: list, output_path: Path):
    """zone_matches: [[m_q0s0, m_q0s1], [m_q1s2, m_q1s3], ...]"""
    img = _vgrad(CANVAS, BG_TOP, BG_BOT).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 상단 카운트다운 배너
    d.rounded_rectangle([40, 60, CANVAS[0]-40, 160], radius=24, fill=GOLD)
    _cx(d, "⏰ 투표 마감 D-1!", _font("Bold", 60), CANVAS[0]//2, 74, fill=INK)

    # 날짜 강조
    _cx(d, "6/29(월) 12:00 마감", _font("Bold", 52), CANVAS[0]//2, 196, fill=WHITE,
        stroke=2, sfill=INK)

    # 서브
    _cx(d, "지금 투표 안 하면 내 최애가 탈락할 수도! 😱",
        _font("Medium", 28), CANVAS[0]//2, 278, fill=PINK)

    # 구분선
    d.line([(60, 330), (CANVAS[0]-60, 330)], fill=GOLD, width=2)

    # 조별 매치 목록
    y = 360
    for zi, (zname, emoji, matches) in enumerate(zip(ZONE_NAMES, ZONE_EMOJIS, zone_matches)):
        # 조 헤더
        d.rounded_rectangle([80, y, CANVAS[0]-80, y+52], radius=14,
                             fill=(50, 40, 100))
        _cx(d, f"{emoji} {zname}", _font("Bold", 34), CANVAS[0]//2, y+8, fill=GOLD)
        y += 64
        for m in matches:
            a = m["a"]["member"]
            b = m["b"]["member"]
            _cx(d, f"{a}  ⚡  {b}", _font("Bold", 32), CANVAS[0]//2, y, fill=WHITE)
            y += 52
        y += 16  # 조 사이 여백

    # 구분선
    d.line([(60, y+8), (CANVAS[0]-60, y+8)], fill=GOLD, width=2)
    y += 32

    # CTA
    _cx(d, "💬 각 경기 게시글 댓글에 번호로 투표!", _font("Bold", 36),
        CANVAS[0]//2, y, fill=PINK)
    y += 58
    _cx(d, "🔔 팔로우 + 알림 ON → 결과 알림", _font("Medium", 28),
        CANVAS[0]//2, y, fill=WHITE_DIM)
    y += 50
    _cx(d, "🏆 #걸그룹월드컵 #16강 @daily_enter_kr",
        _font("Medium", 26), CANVAS[0]//2, y, fill=(160, 150, 200))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=94)
    return output_path


# ──────────────────────────────────────────────
#  CAPTION 헬퍼
# ──────────────────────────────────────────────

def _carousel_caption():
    return "\n".join([
        "🏆 걸그룹 월드컵 16강 — 전체 8경기 한눈에!",
        "",
        "A조 👑: 장원영 vs 원희 · 지수 vs 닝닝",
        "B조 🌹: 로제 vs 안유진 · 윈터 vs 조이",
        "C조 🦋: 카리나 vs 리사 · 김채원 vs 태연",
        "D조 💎: 제니 vs 원이 · 정채연 vs 설윤",
        "",
        "🔴 투표 마감: 6/29(월) 12:00",
        "💬 각 경기 게시글에서 1·2·3·4 번호로 투표!",
        "🔔 팔로우 + 알림 ON → 8강 결과 즉시 알림",
        "",
        "#걸그룹월드컵 #16강 #케이팝 #kpop #아이돌투표",
        "#장원영 #카리나 #제니 #로제 #안유진 #윈터 #지수",
    ])


def _teaser_caption():
    return "\n".join([
        "⏰ 걸그룹 월드컵 16강 투표 마감 D-1!",
        "",
        "6/29(월) 12:00까지 투표 가능!",
        "지금 각 경기 게시글에서 댓글로 투표해주세요 🗳️",
        "",
        "👑 A조: 장원영·지수 vs 원희·닝닝",
        "🌹 B조: 로제·윈터 vs 안유진·조이",
        "🦋 C조: 카리나·김채원 vs 리사·태연",
        "💎 D조: 제니·정채연 vs 원이·설윤",
        "",
        "🏆 8강 진출자는 6/29 오후 공개!",
        "🔔 팔로우 + 알림 ON → 결과 놓치지 마세요",
        "",
        "#걸그룹월드컵 #16강마감 #케이팝투표 #kpop #아이돌",
    ])


def _zone_caption(zi, matches):
    zname = ZONE_NAMES[zi]
    emoji = ZONE_EMOJIS[zi]
    lines = [
        f"🏆 걸그룹 월드컵 16강 {emoji} {zname} 매치!",
        "",
    ]
    for m in matches:
        lines.append(f"⚡ {m['a']['member']} vs {m['b']['member']}")
    lines += [
        "",
        "💬 각 매치 게시글 댓글에 번호로 투표!",
        "🔴 마감: 6/29(월) 12:00",
        "🔔 팔로우 + 알림 ON → 결과 알림",
        "",
        "#걸그룹월드컵 #16강 #케이팝 #kpop #아이돌투표",
    ]
    return "\n".join(lines)


def _hf_caption():
    return "\n".join([
        "🏆 걸그룹 월드컵 16강 하이라이트 🔥",
        "",
        "8강 가는 길 — 누가 올라갈까요?",
        "💬 댓글로 우승 예측 남겨주세요!",
        "",
        "🔴 투표 마감: 6/29(월) 12:00",
        "#걸그룹월드컵 #16강 #케이팝 #릴스 #kpop",
    ])


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skip", nargs="*", type=int, default=[], metavar="N",
                   help="건너뛸 파트 번호 (예: --skip 4)")
    args = p.parse_args()
    skip = set(args.skip or [])

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and
            os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    pub = InstagramPublisher(ig_user_id, ig_token)
    if not pub.health_check().get("ok"):
        print("❌ IG 토큰 무효")
        return 1

    bracket = json.loads((ROOT / "data" / "worldcup_bracket.json").read_text())
    r16 = bracket["rounds"]["R16"]
    all_matches = r16["matches"]
    bgm = ROOT / "assets" / "bgm" / "daily_enter_theme_c.mp3"
    if not bgm.exists():
        bgm = None

    # 조별 그루핑
    zone_matches = {q: [] for q in range(4)}
    for m in all_matches:
        zone_matches[m["quarter"]].append(m)
    for q in zone_matches:
        zone_matches[q].sort(key=lambda x: x["slot"])
    zone_list = [zone_matches[q] for q in range(4)]

    out = ROOT / "output_enter" / "publish" / "worldcup_promo_r16"
    out.mkdir(parents=True, exist_ok=True)
    r16_dir = ROOT / "output_enter" / "publish" / "worldcup_r16"

    results = []

    # ── PART #1: 전체 8매치 캐러셀 ──────────────────
    if 1 not in skip:
        print("\n▶ PART #1 — 전체 8매치 캐러셀")
        jpgs = [r16_dir / f"post_{i:02d}.jpg" for i in range(1, 5)]
        missing = [j for j in jpgs if not j.exists()]
        if missing:
            print(f"  ⚠️  이미지 없음: {missing} — 빌드 먼저 필요")
        else:
            urls = []
            for jpg in jpgs:
                url = upload_image(jpg)
                print(f"  ✓ {jpg.name} → {url[:60]}")
                urls.append(url)
            cap = _carousel_caption()
            mid = pub.post_carousel(urls, cap)
            print(f"  ✅ 캐러셀 게시: {mid}")
            time.sleep(5)
            try:
                pub.post_comment(mid, "💬 좌우로 스와이프 → 전체 매치 확인!\n🗳️ 각 경기 게시글 댓글에 번호로 투표해주세요!")
            except Exception as e:
                print(f"  ⚠️ 댓글 실패: {e}")
            post_ledger.record_results([{
                "ok": True, "topic_id": "worldcup_promo_r16_carousel",
                "title": "16강 전체 매치 캐러셀", "style": "worldcup_promo",
                "seed": None, "media_id": mid, "youtube_id": None,
                "threads_id": None, "bgm": None,
            }])
            results.append(("캐러셀", mid))

    # ── PART #2: D-1 티저 카드 ──────────────────────
    if 2 not in skip:
        print("\n▶ PART #2 — D-1 티저 카드")
        teaser_jpg = out / "teaser_d1.jpg"
        make_teaser_card(zone_list, teaser_jpg)
        print(f"  ✓ 티저 카드: {teaser_jpg.stat().st_size // 1024}KB")
        url = upload_image(teaser_jpg)
        mid = pub.post_single_image(url, _teaser_caption())
        print(f"  ✅ 티저 게시: {mid}")
        time.sleep(5)
        try:
            pub.post_comment(mid, "🏆 지금 바로 각 경기 게시글 찾아서 투표! 피드에서 확인하세요 ⬆️")
        except Exception as e:
            print(f"  ⚠️ 댓글 실패: {e}")
        post_ledger.record_results([{
            "ok": True, "topic_id": "worldcup_promo_r16_teaser",
            "title": "16강 D-1 티저", "style": "worldcup_promo",
            "seed": None, "media_id": mid, "youtube_id": None,
            "threads_id": None, "bgm": None,
        }])
        results.append(("D-1 티저", mid))

    # ── PART #3: A/B/C/D 조별 릴스 (4개) ───────────
    if 3 not in skip:
        print("\n▶ PART #3 — 조별 릴스 (A/B/C/D조)")
        for zi in range(4):
            zname = ZONE_NAMES[zi]
            matches = zone_list[zi]
            if len(matches) < 2:
                print(f"  ⚠️ {zname} 매치 부족 ({len(matches)}개) — 스킵")
                continue
            m1, m2 = matches[0], matches[1]

            jpg = out / f"zone_{chr(65+zi)}.jpg"
            mp4 = out / f"zone_{chr(65+zi)}.mp4"
            make_worldcup_match_card(
                round_label="16강", post_index=zi+1, post_total=4,
                match1=m1, match2=m2, output_path=jpg,
                source_note="출처: 한국기업평판연구소 2026.6.21",
            )
            make_worldcup_match_video(card_jpg=jpg, output_path=mp4,
                                      duration=15.0, bgm_path=bgm)
            print(f"  ✓ {zname}: {jpg.stat().st_size//1024}KB jpg / {mp4.stat().st_size//1024}KB mp4")
            url = upload_video(mp4)
            mid = pub.post_reel(url, _zone_caption(zi, matches))
            print(f"  ✅ {zname} 릴스: {mid}")
            time.sleep(30)  # IG API 안정화
            try:
                pub.post_comment(mid, f"🏆 {zname} 투표 현황이 궁금하다면? 6/29(월) 집계 결과 공개!")
            except Exception as e:
                print(f"  ⚠️ 댓글 실패: {e}")
            post_ledger.record_results([{
                "ok": True, "topic_id": f"worldcup_promo_r16_zone_{chr(65+zi).lower()}",
                "title": f"16강 {zname} 릴스", "style": "worldcup_promo",
                "seed": None, "media_id": mid, "youtube_id": None,
                "threads_id": None, "bgm": None,
            }])
            results.append((f"{zname} 릴스", mid))

    # ── PART #4: HyperFrames 릴스 ────────────────────
    if 4 not in skip:
        print("\n▶ PART #4 — HyperFrames 릴스")
        hf_html = ROOT / "compositions" / "r16_announce.html"
        if not hf_html.exists():
            print(f"  ⚠️ {hf_html} 없음 — 스킵")
        else:
            hf_mp4 = out / "r16_hf.mp4"
            sys.path.insert(0, str(ROOT / "scripts"))
            from render_hf import render_html_to_mp4
            rc = render_html_to_mp4(hf_html, hf_mp4, duration=6.0, fps=30)
            if rc == 0 and hf_mp4.exists():
                url = upload_video(hf_mp4)
                mid = pub.post_reel(url, _hf_caption())
                print(f"  ✅ HF 릴스: {mid}")
                time.sleep(5)
                try:
                    pub.post_comment(mid, "🏆 누가 결승까지 갈까요? 예측 댓글 ⬇️")
                except Exception as e:
                    print(f"  ⚠️ 댓글 실패: {e}")
                post_ledger.record_results([{
                    "ok": True, "topic_id": "worldcup_promo_r16_hf_reels",
                    "title": "16강 HF 릴스", "style": "worldcup_promo",
                    "seed": None, "media_id": mid, "youtube_id": None,
                    "threads_id": None, "bgm": None,
                }])
                results.append(("HF 릴스", mid))
            else:
                print(f"  ⚠️ HF 렌더 실패 (rc={rc}) — 스킵")

    # ── 완료 요약 ────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"✅ 홍보 블라스트 완료 ({len(results)}개 게시)")
    for label, mid in results:
        print(f"  {label}: {mid}")

    notify_discord(
        f"🔥 **16강 홍보 블라스트 완료** — {len(results)}개 게시\n"
        + "\n".join(f"  {l}: `{m}`" for l, m in results),
        username="daily_enter_kr worldcup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
