"""
메인 파이프라인
매일 실행되어 뉴스 수집 → 안전 분류 + 요약 → 카드 생성 → 인스타 업로드까지 전체 처리

[실행 방법]
로컬: python main.py
GitHub Actions: workflow가 자동 실행 (한국시간 매일 오전 8시 + jitter)
"""

import os
import random
import sys
import time
from pathlib import Path
from datetime import datetime

# src 폴더를 path에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetch_news import fetch_google_news_korea
from summarize import summarize_news, filter_postable, SummarizedNews
from make_card import make_card, make_cover_card
from post_instagram import InstagramPublisher, upload_image, build_caption
from state import (
    load_state, save_state, filter_duplicates, record_post, record_run,
    days_until_token_expiry,
)
from image_provider import search_and_download as fetch_bg_image


# === 채널 설정 (CHANNEL 환경변수로 선택; 기본 daily_enter_kr) ===
# 새 채널 추가 방법은 CLAUDE.md 의 "두 번째 토픽 채널 추가" 섹션 참고
CHANNELS = {
    "daily_enter_kr": {
        "topic": "entertainment",         # fetch_news.py의 TOPIC_URLS 키
        "label_short": "K-연예",          # 표지/푸터/캡션 라벨 (한글)
        "label_short_en": "korean entertainment",  # Unsplash 검색용 영문 라벨
        "themes": [
            "neon_seoul", "stage_gold", "kpop_pastel", "noir_cinema", "dream_purple",
            "neon_seoul", "stage_gold", "kpop_pastel", "noir_cinema", "dream_purple",
        ],
        "state_path": "state.json",
        "default_hashtags": ["#K연예", "#연예뉴스", "#오늘의연예", "#연예소식",
                             "#카드뉴스", "#kpop", "#kdrama", "#한국연예"],
    },
    "daily_sports_kr": {
        "topic": "sports",
        "label_short": "K-스포츠",
        "label_short_en": "stadium sports",
        "themes": [
            "stage_gold", "noir_cinema", "neon_seoul", "dream_purple", "stage_gold",
            "noir_cinema", "neon_seoul", "dream_purple", "stage_gold", "noir_cinema",
        ],
        "state_path": "state_sports.json",
        "default_hashtags": ["#스포츠", "#sports", "#오늘의스포츠", "#스포츠뉴스",
                             "#카드뉴스", "#야구", "#축구", "#골프", "#KBO", "#K리그"],
    },
    "daily_economy_kr": {
        "topic": "business",
        "label_short": "K-경제",
        "label_short_en": "stock market finance",
        "themes": [
            "noir_cinema", "stage_gold", "dream_purple", "neon_seoul", "noir_cinema",
            "stage_gold", "dream_purple", "neon_seoul", "noir_cinema", "stage_gold",
        ],
        "state_path": "state_economy.json",
        "default_hashtags": ["#경제", "#economy", "#오늘의경제", "#경제뉴스",
                             "#카드뉴스", "#주식", "#투자", "#증시", "#재테크"],
    },
}
CHANNEL_ID = os.environ.get("CHANNEL", "daily_enter_kr")
CHANNEL = CHANNELS.get(CHANNEL_ID, CHANNELS["daily_enter_kr"])
THEMES = CHANNEL["themes"]

# state.py가 채널별 state 파일을 쓰도록 환경변수 export (import 시점 이전에 설정해야 효과 있음)
os.environ.setdefault("STATE_PATH", CHANNEL["state_path"])

# === 운영 설정 ===
FETCH_LIMIT = 20       # 안전/중복 필터 후 9건 확보를 위해 여유롭게 수집
MIN_CARDS = 3          # 게시 가능한 최소 카드 수 (이보다 적으면 게시 스킵)
MAX_CARDS = 9          # 표지 + 9 = 캐러셀 10장 한도
UPLOAD_RETRIES = 3     # 호스팅 업로드 재시도 횟수
UPLOAD_BACKOFF = 2.0   # 지수 백오프 base (sec)
CRON_JITTER_MAX_SEC = 1800  # CI에서만 적용 (0-30분 랜덤 지연)


def apply_cron_jitter():
    """CI에서만 봇 패턴 회피용 0-30분 랜덤 지연."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    jitter = random.randint(0, CRON_JITTER_MAX_SEC)
    print(f"⏱️  cron jitter: {jitter}초 대기 (봇 패턴 회피)")
    time.sleep(jitter)


def upload_with_retry(path: Path) -> str:
    """업로드 실패 시 지수 백오프 재시도."""
    last_exc = None
    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            return upload_image(path)
        except Exception as e:
            last_exc = e
            wait = UPLOAD_BACKOFF ** attempt
            print(f"   ⚠️  업로드 실패 ({attempt}/{UPLOAD_RETRIES}): {e} → {wait:.1f}s 후 재시도")
            time.sleep(wait)
    raise RuntimeError(f"{path.name} 업로드 {UPLOAD_RETRIES}회 실패: {last_exc}")


def main():
    apply_cron_jitter()

    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    output_dir = Path(__file__).parent / "output" / today.strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    # state 로드 (중복 게시 방지 + 토큰 만료 추적)
    state = load_state()

    # 토큰 만료 임박 경고 (정보가 있는 경우만)
    days_left = days_until_token_expiry(state)
    if days_left is not None:
        if days_left < 7:
            print(f"🚨🚨 IG 토큰 만료 {days_left:.1f}일 남음 — 지금 'python exchange_token.py --refresh' 실행 필요")
        elif days_left < 14:
            print(f"⚠️  IG 토큰 만료 {days_left:.1f}일 남음 — 곧 갱신 필요")

    # === 1. 뉴스 수집 ===
    print("\n" + "="*60)
    print("1️⃣  뉴스 수집")
    print("="*60)
    news_items = fetch_google_news_korea(topic=CHANNEL["topic"], limit=FETCH_LIMIT)
    if not news_items:
        print("❌ 수집된 뉴스가 0건입니다. RSS 응답 이상 가능성. 종료.")
        record_run(state, "failed_no_news")
        save_state(state)
        sys.exit(1)
    print(f"  수집 {len(news_items)}건")

    # 중복 제거 (최근 14일 이내에 게시한 동일 제목 제외)
    fresh, dupes = filter_duplicates(news_items, state)
    if dupes:
        print(f"  ⊘ 중복 제거 {len(dupes)}건 (최근 14일 이내 동일 제목 게시 이력)")
        for d in dupes:
            print(f"     - {d.title[:50]}")
    news_items = fresh
    print(f"  → 신규 {len(news_items)}건")
    for i, n in enumerate(news_items, 1):
        print(f"  [{i}] {n.title[:50]}...")

    if not news_items:
        print("❌ 중복 제거 후 남은 뉴스가 0건입니다. 오늘은 게시 스킵.")
        record_run(state, "skipped_all_duplicates")
        save_state(state)
        sys.exit(0)

    # === 2. 요약 + 안전 분류 ===
    print("\n" + "="*60)
    print("2️⃣  Claude API로 요약 + 안전 분류")
    print("="*60)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY 미설정 → 안전 분류 없이는 게시 불가 → 카드만 생성")
        summaries = [
            SummarizedNews(
                original_title=n.title,
                card_title=n.title,
                card_body="",
                hashtags=["#오늘의뉴스"],
                source=n.source,
                link=n.link,
                decision="post",
            )
            for n in news_items[:MAX_CARDS]
        ]
    else:
        summaries_all = summarize_news(news_items)
        summaries = filter_postable(summaries_all)
        print(f"\n  → 안전 분류 후 {len(summaries)}/{len(summaries_all)}건 게시 가능")

    # 게시 가능한 카드가 너무 적으면 게시 스킵
    if len(summaries) < MIN_CARDS:
        print(f"\n❌ 게시 가능한 카드가 {len(summaries)}개 (최소 {MIN_CARDS}개 필요). 오늘은 게시 스킵.")
        record_run(state, "skipped_too_few_cards")
        save_state(state)
        sys.exit(0)

    summaries = summaries[:MAX_CARDS]
    for i, s in enumerate(summaries, 1):
        marker = "🔸" if s.decision == "respectful" else "  "
        print(f"  [{i}]{marker} {s.card_title}")

    # === 3. 카드 이미지 생성 ===
    print("\n" + "="*60)
    print("3️⃣  카드뉴스 이미지 생성")
    print("="*60)
    image_paths = []

    total_cards = len(summaries)

    # 표지용 배경 이미지 (채널 라벨 컨셉으로 fetch)
    cover_bg_query = f"cinematic {CHANNEL['label_short_en']} dramatic lighting" if CHANNEL.get("label_short_en") else None
    cover_bg = fetch_bg_image(cover_bg_query) if cover_bg_query else None
    cover_path = output_dir / "00_cover.jpg"
    make_cover_card(date_str=date_str, output_path=cover_path,
                    total_cards=total_cards, label_short=CHANNEL["label_short"],
                    bg_image_path=cover_bg)
    image_paths.append(cover_path)
    print(f"  ✓ 표지: {cover_path.name} (TOP {total_cards}){' [bg]' if cover_bg else ''}")

    for i, s in enumerate(summaries, 1):
        path = output_dir / f"{i:02d}_card.jpg"
        # 뉴스마다 visual_concept으로 배경 이미지 fetch (Unsplash). 실패 시 None 폴백.
        bg_path = fetch_bg_image(s.visual_concept) if s.visual_concept else None
        make_card(
            rank=i,
            title=s.card_title,
            body=s.card_body,
            source=s.source,
            output_path=path,
            theme=THEMES[(i - 1) % len(THEMES)],
            total_cards=total_cards,
            label_short=CHANNEL["label_short"],
            bg_image_path=bg_path,
        )
        image_paths.append(path)
        bg_indicator = " [bg]" if bg_path else " [proc]"
        print(f"  ✓ {path.name}{bg_indicator}: {s.card_title}")

    # === 4. 인스타그램 업로드 사전 체크 ===
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    has_hosting = (
        os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    ) or os.environ.get("IMGUR_CLIENT_ID")

    if not (ig_user_id and ig_token and has_hosting):
        print("\n⚠️  인스타그램/호스팅 환경변수 미설정 → 업로드 스킵")
        print(f"    이미지는 {output_dir}에서 확인 가능합니다.")
        record_run(state, "skipped_no_upload_credentials")
        save_state(state)
        return

    # === 5. 이미지 호스팅 업로드 (재시도 포함) ===
    print("\n" + "="*60)
    print("4️⃣  이미지 호스팅 업로드")
    print("="*60)
    image_urls = []
    for path in image_paths:
        url = upload_with_retry(path)
        image_urls.append(url)
        print(f"  ✓ {path.name} → {url}")

    # === 6. 인스타그램 캐러셀 게시 ===
    print("\n" + "="*60)
    print("5️⃣  인스타그램 캐러셀 게시")
    print("="*60)
    publisher = InstagramPublisher(ig_user_id, ig_token)

    # 토큰 health check (만료/무효 토큰 사전 감지)
    health = publisher.health_check()
    if not health["ok"]:
        print(f"❌ Instagram 토큰 무효: {health['error_message']}")
        print("   1. 'python exchange_token.py --refresh' 로 토큰 갱신")
        print("   2. .env의 INSTAGRAM_ACCESS_TOKEN을 새 값으로 교체")
        print("   3. GitHub Secrets의 INSTAGRAM_ACCESS_TOKEN도 같이 업데이트")
        record_run(state, f"failed_token_invalid")
        save_state(state)
        sys.exit(1)
    print(f"✓ 토큰 유효: @{health['username']} ({health['account_type']})")

    caption = build_caption(summaries, date_str, label_short=CHANNEL["label_short"],
                            default_hashtags=CHANNEL["default_hashtags"])
    media_id = publisher.post_carousel(image_urls, caption)

    print(f"\n🎉 완료! 게시물 ID: {media_id}")

    # === 7. state 기록 (다음 실행의 중복 방지) ===
    record_post(
        state,
        [(s.original_title, s.card_title) for s in summaries],
        status="success",
    )
    save_state(state)
    print(f"📝 state.json 업데이트됨 (총 {len(state['posted_history'])}개 history)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        # state에 실패 기록 (가능하면)
        try:
            st = load_state()
            record_run(st, f"failed: {type(e).__name__}")
            save_state(st)
        except Exception:
            pass
        sys.exit(1)
