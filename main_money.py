"""
daily_money_kr 채널 — 절세/재테크 블로그 (Tistory RSS) → Reels.

기존 main.py 와 인프라(state/카드/영상/IG 게시/Discord) 공유, 인풋·로직만 분리.

[흐름]
1. Tistory RSS fetch
2. dedup (state_money.json 의 posted_guids 와 비교)
3. 미게시 포스트 중 최신 1건 픽
4. 핵심 요약 bullets 추출 → 카드: 제목 + bullets N장 + CTA
5. mp4 + BGM
6. Cloudinary 업로드
7. IG Reels publish + Stories
8. state 기록 + Discord 알림

[게시 빈도]
1일 1편 (큐 비면 스킵). 매 cron 마다 RSS 다시 확인 → 신규 포스트 자동 픽업.
"""

import json
import os
import random
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetch_blog import fetch_blog_posts, BlogPost
from make_card import make_card, make_sources_card, make_reels_thumbnail
from make_video import make_slideshow_video, SECONDS_PER_CARD
from post_instagram import (
    InstagramPublisher, upload_video,
    upload_image,
)
import post_threads
from notify import notify_discord


CHANNEL_ID = "daily_money_kr"
BLOG_RSS_URL = os.environ.get("MONEY_BLOG_RSS_URL", "https://editor60277.tistory.com/rss")
BLOG_HOME_URL = os.environ.get("MONEY_BLOG_HOME_URL", "https://editor60277.tistory.com/")
LABEL_SHORT = "절세노트"
COVER_LABEL = "절세"
STATE_PATH = Path(__file__).parent / "state_money.json"
OUTPUT_BASE = Path(__file__).parent / "output_money"

# 카드당 노출 — 정보 텍스트라 살짝 더 길게 (1줄 + 2줄 wrap 가능)
MONEY_SECONDS_PER_CARD = 3.0

DEFAULT_HASHTAGS = [
    "#절세", "#재테크", "#세금", "#연말정산", "#소득공제",
    "#세액공제", "#월급쟁이재테크", "#직장인재테크",
    "#재테크정보", "#실속재테크", "#카드뉴스", "#릴스",
]

# === state ===
def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "posted_guids": [], "runs": []}


def save_state(state: dict):
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_already_posted(state: dict, post: BlogPost) -> bool:
    return post.guid in state.get("posted_guids", [])


def record_posted(state: dict, post: BlogPost, media_id: str = None):
    state.setdefault("posted_guids", []).append(post.guid)
    state.setdefault("runs", []).append({
        "at": datetime.now().isoformat(),
        "status": "success",
        "guid": post.guid,
        "title": post.title,
        "media_id": media_id,
    })
    # runs 최근 90건만 유지
    state["runs"] = state["runs"][-90:]


def record_failure(state: dict, reason: str):
    state.setdefault("runs", []).append({
        "at": datetime.now().isoformat(),
        "status": f"failed: {reason}",
    })
    state["runs"] = state["runs"][-90:]


# === 카드 콘텐츠 빌더 ===
def build_card_texts(post: BlogPost) -> List[str]:
    """포스트 → 카드 텍스트 리스트 (제목 + bullets + CTA).

    bullets 없으면 제목 + 본문 발췌 한 줄 + CTA 만.
    카드 7장 한도 (Reels 최적 길이).
    """
    cards = [post.title]
    if post.summary_bullets:
        cards.extend(post.summary_bullets[:5])  # 5개 bullets 최대
    elif post.body_excerpt:
        # 폴백: 발췌를 한 문장으로
        excerpt = post.body_excerpt.split(".")[0][:80] + "."
        cards.append(excerpt)
    cards.append(f"전체 내용은 프로필 링크에서 ⌁ {LABEL_SHORT}")
    return cards


def build_caption(post: BlogPost) -> str:
    """절세/재테크 캡션 — 블로그 톤 보존 + save/share 유도 + 1차 자료 신뢰성 어필."""
    bullets = post.summary_bullets[:3] if post.summary_bullets else []

    # 첫 줄 훅 — 카테고리 기반 (있으면) + 제목
    hook = post.title
    if len(hook) > 120:
        hook = hook[:117] + "..."

    lines = [
        hook,
        "",
        "💡 절세·재테크 핵심 요약 — 영상으로 한눈에 보세요 ▶",
        "",
    ]

    if bullets:
        for i, b in enumerate(bullets, 1):
            lines.append(f"{i}. {b}")
        lines.append("")

    lines.append("📌 국세청·기획재정부 등 1차 자료 기반 작성")
    lines.append("🔗 전체 글은 프로필 링크에서 확인하세요")
    lines.append("")
    lines.append("💬 적용해보셨나요? 후기·질문 댓글로 부탁드려요")
    lines.append("📩 도움될 만한 친구에게 공유 / 🔖 북마크해두면 다시 보기 좋아요")
    lines.append("")
    lines.append("⌁ 매일 새로운 절세·재테크 정보 큐레이션. 팔로우하고 받아보세요.")
    lines.append("")
    lines.append("본 게시물은 작성 시점 일반 정보이며,")
    lines.append("개별 세무·금융 상황은 전문가 상담을 권장합니다.")
    lines.append("")

    # 해시태그 — niche (post 카테고리) + medium (default)
    seen, tags = set(), []
    for c in post.categories:
        # 카테고리 → 해시태그 변환 (공백 제거)
        ht = "#" + c.replace(" ", "").replace("-", "")
        if ht.lower() not in seen:
            seen.add(ht.lower())
            tags.append(ht)
    for ht in DEFAULT_HASHTAGS:
        if ht.lower() not in seen:
            seen.add(ht.lower())
            tags.append(ht)
        if len(tags) >= 28:
            break
    lines.append(" ".join(tags[:28]))

    return "\n".join(lines)


# === 메인 ===
def upload_with_retry(path: Path, uploader, kind: str, retries: int = 3) -> str:
    last = None
    for attempt in range(1, retries + 1):
        try:
            return uploader(path)
        except Exception as e:
            last = e
            wait = 2 ** attempt
            print(f"   ⚠️  {kind} 업로드 실패 ({attempt}/{retries}): {e} → {wait}s 재시도")
            time.sleep(wait)
    raise RuntimeError(f"{path.name} {kind} 업로드 {retries}회 실패: {last}")


def main() -> int:
    print("=" * 60)
    print(f"💰 {CHANNEL_ID} — 절세/재테크 Reels 파이프라인")
    print("=" * 60)

    state = load_state()

    # === 1. RSS fetch ===
    print(f"\n1️⃣  블로그 RSS 가져오기 ({BLOG_RSS_URL})")
    posts = fetch_blog_posts(BLOG_RSS_URL, limit=20)
    if not posts:
        print("❌ RSS 응답 없음 (403/네트워크 등). 게시 스킵.")
        record_failure(state, "rss_unreachable")
        save_state(state)
        return 1
    print(f"  ✓ {len(posts)}개 포스트 수신")

    # === 2. 미게시 픽 ===
    unposted = [p for p in posts if not is_already_posted(state, p)]
    if not unposted:
        print("✓ 모든 포스트가 이미 게시됨. 오늘은 스킵.")
        record_failure(state, "no_new_post")
        save_state(state)
        return 0
    pick = unposted[0]  # latest first (RSS 가 보통 최신순)
    print(f"  ✓ 미게시 {len(unposted)}건 중 픽: {pick.title}")
    print(f"     URL: {pick.url}")
    print(f"     bullets: {len(pick.summary_bullets)}개")

    # === 3. 카드 콘텐츠 ===
    cards_texts = build_card_texts(pick)
    print(f"\n2️⃣  카드 {len(cards_texts)}장:")
    for i, t in enumerate(cards_texts, 1):
        print(f"  [{i}] {t[:60]}")

    # === 4. 카드 렌더 ===
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_BASE / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n3️⃣  카드 이미지 생성")
    image_paths = []
    for i, txt in enumerate(cards_texts, 1):
        path = output_dir / f"{i:02d}_card.jpg"
        make_card(title=txt, output_path=path)
        image_paths.append(path)
        print(f"  ✓ {path.name}")

    # 그리드 썸네일 (제목 + 첫 bullet)
    thumb_path = output_dir / "00_thumb.jpg"
    make_reels_thumbnail(
        top_titles=[pick.title] + pick.summary_bullets[:1],
        output_path=thumb_path,
    )

    # === 5. mp4 빌드 ===
    print(f"\n4️⃣  슬라이드쇼 mp4 빌드 (BGM)")
    bgm_dir = Path(__file__).parent / "assets" / "bgm"
    bgm_path = None
    if bgm_dir.exists():
        candidates = sorted(bgm_dir.glob("*.mp3"))
        if candidates:
            bgm_path = random.choice(candidates)
            print(f"  🎵 BGM: {bgm_path.name}")
    durations = [MONEY_SECONDS_PER_CARD] * len(image_paths)
    video_path = output_dir / "reel.mp4"
    make_slideshow_video(image_paths, video_path, durations=durations, bgm_path=bgm_path)
    total = sum(durations) - max(0, (len(image_paths) - 1) * 0.3)
    print(f"  ✓ {video_path.name} ({video_path.stat().st_size/1024/1024:.1f} MB, ≈{total:.1f}s)")

    # === 6. IG 업로드 사전 체크 ===
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID_MONEY") or os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN_MONEY") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    has_video_hosting = (
        os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    )
    if not (ig_user_id and ig_token and has_video_hosting):
        print("\n⚠️  IG/Cloudinary 환경변수 미설정 → 게시 스킵 (로컬 mp4 만 생성)")
        record_failure(state, "no_upload_creds")
        save_state(state)
        return 0

    # === 7. Cloudinary 업로드 ===
    print(f"\n5️⃣  Cloudinary 비디오 업로드")
    video_url = upload_with_retry(video_path, upload_video, "video")
    print(f"  ✓ {video_url}")

    cover_url = None
    try:
        cover_url = upload_with_retry(thumb_path, upload_image, "image")
        print(f"  🖼  썸네일: {cover_url}")
    except Exception as e:
        print(f"  ⚠️  썸네일 업로드 실패 ({e})")

    # === 8. Reels 게시 ===
    print(f"\n6️⃣  IG Reels 게시")
    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health["ok"]:
        print(f"❌ IG 토큰 무효: {health['error_message']}")
        record_failure(state, "token_invalid")
        save_state(state)
        return 1
    print(f"✓ 토큰: @{health['username']}")

    caption = build_caption(pick)
    media_id = publisher.post_reel(video_url=video_url, caption=caption,
                                   cover_url=cover_url, share_to_feed=True)
    print(f"  ✅ Reels Media ID: {media_id}")

    # Stories
    try:
        story_id = publisher.post_story_video(video_url)
        print(f"  📖 Stories: {story_id}")
    except Exception as e:
        print(f"  ⚠️  Stories 실패: {e}")
        story_id = None

    # Threads (선택)
    threads_id = None
    if post_threads.is_configured():
        try:
            top = [pick.title] + pick.summary_bullets[:3]
            threads_id = post_threads.post_thread(
                top_titles=top, date_str=date_str,
                label_short=LABEL_SHORT, reel_link=BLOG_HOME_URL,
            )
        except Exception as e:
            print(f"  ⚠️  Threads 실패: {e}")

    # Discord 알림
    notify_discord(
        f"💰 **{CHANNEL_ID} 게시 완료**\n"
        f"• 포스트: {pick.title}\n"
        f"• URL: {pick.url}\n"
        f"• Media: `{media_id}`\n"
        f"• Stories: {'✅' if story_id else '❌'} · Threads: {'✅' if threads_id else '⏭️'}",
        username=CHANNEL_ID,
    )

    record_posted(state, pick, media_id=media_id)
    save_state(state)
    print(f"\n🎉 완료. state_money.json 업데이트됨.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        try:
            st = load_state()
            record_failure(st, f"{type(e).__name__}: {str(e)[:120]}")
            save_state(st)
        except Exception:
            pass
        sys.exit(1)
