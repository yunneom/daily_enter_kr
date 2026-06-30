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
from make_card import make_card, make_sources_card
from post_instagram import (
    InstagramPublisher, upload_image,
    build_caption_with_variant,
)
import post_threads
from notify import notify_discord
from state import (
    load_state, save_state, filter_duplicates, record_post, record_run,
    days_until_token_expiry,
)


# === 채널 설정 (CHANNEL 환경변수로 선택; 기본 daily_enter_kr) ===
# 카드 디자인은 단일 미니멀 스타일 (흰 배경 + 검정 제목) 고정.
CHANNELS = {
    "daily_enter_kr": {
        "topic": "entertainment",         # fetch_news.py의 TOPIC_URLS 키
        "label_short": "K-연예",          # 캡션/요약 프롬프트 라벨
        "cover_label": "연예",            # 표지 한 줄 라벨 — '{cover_label} TOP N' 식으로 표시
        "state_path": "state.json",
        "default_hashtags": ["#K연예", "#연예뉴스", "#오늘의연예", "#연예소식",
                             "#카드뉴스", "#kpop", "#kdrama", "#한국연예"],
    },
    "daily_sports_kr": {
        "topic": "sports",
        "label_short": "K-스포츠",
        "cover_label": "스포츠",
        "state_path": "state_sports.json",
        "default_hashtags": ["#스포츠", "#sports", "#오늘의스포츠", "#스포츠뉴스",
                             "#카드뉴스", "#야구", "#축구", "#골프", "#KBO", "#K리그"],
    },
    "daily_economy_kr": {
        "topic": "business",
        "label_short": "K-경제",
        "cover_label": "경제",
        "state_path": "state_economy.json",
        "default_hashtags": ["#경제", "#economy", "#오늘의경제", "#경제뉴스",
                             "#카드뉴스", "#주식", "#투자", "#증시", "#재테크"],
    },
}
CHANNEL_ID = os.environ.get("CHANNEL", "daily_enter_kr")
CHANNEL = CHANNELS.get(CHANNEL_ID, CHANNELS["daily_enter_kr"])

# state.py가 채널별 state 파일을 쓰도록 환경변수 export (import 시점 이전에 설정해야 효과 있음)
os.environ.setdefault("STATE_PATH", CHANNEL["state_path"])

# === 운영 설정 ===
FETCH_LIMIT = 20       # 안전/중복 필터 후 충분히 확보를 위해 여유롭게 수집
MIN_CARDS = 3          # 게시 가능한 최소 본문 카드 수 (이보다 적으면 게시 스킵)
MAX_CARDS = 9          # 캐러셀 최대 10장 — 뉴스 9 + 출처 1 = 10장 딱 맞춤
UPLOAD_RETRIES = 3     # 호스팅 업로드 재시도 횟수
UPLOAD_BACKOFF = 2.0   # 지수 백오프 base (sec)
CRON_JITTER_MAX_SEC = 1800  # CI cron 만 적용 (0-30분 랜덤 지연). 90분에서 축소 — 사용자가 게시 시각 예측 가능하도록.


def _card_style_for_date(date_str: str) -> str:  # noqa: ARG001
    return "minimal"


def apply_cron_jitter():
    """CI cron 실행에서만 봇 패턴 회피용 0-90분 랜덤 지연.
    cron 시각(KST 08:00)부터 90분 윈도우 내 무작위 지연 → IG 봇 탐지 약화.
    workflow_dispatch(수동 트리거) 와 로컬은 jitter 스킵 — 테스트 시 즉시 실행되게.
    워크플로우 timeout-minutes는 jitter 최대값 + 처리 시간 여유를 합쳐 책정해야 함."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("⏭️  manual dispatch — jitter 스킵 (테스트 모드)")
        return
    jitter = random.randint(0, CRON_JITTER_MAX_SEC)
    print(f"⏱️  cron jitter: {jitter}초 대기 (봇 패턴 회피)")
    time.sleep(jitter)


def _upload_with_retry(path: Path, uploader, kind: str) -> str:
    """업로드 실패 시 지수 백오프 재시도. uploader 는 upload_image/upload_video."""
    last_exc = None
    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            return uploader(path)
        except Exception as e:
            last_exc = e
            wait = UPLOAD_BACKOFF ** attempt
            print(f"   ⚠️  {kind} 업로드 실패 ({attempt}/{UPLOAD_RETRIES}): {e} → {wait:.1f}s 후 재시도")
            time.sleep(wait)
    raise RuntimeError(f"{path.name} {kind} 업로드 {UPLOAD_RETRIES}회 실패: {last_exc}")


def upload_with_retry(path: Path) -> str:
    return _upload_with_retry(path, upload_image, "image")


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
        summaries_all = summarize_news(news_items, channel_label=CHANNEL["label_short"])
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

    # === 3. 카드 이미지 생성 (9:16 미니멀: 흰 배경 + 검정 제목) ===
    # 캐러셀 순서: 본문 N장 → 출처 카드 마지막.
    # 카드 스타일 — 날짜 기반 격일 회전 (minimal / manhwa) → A/B 분석 가능.
    print("\n" + "="*60)
    print("3️⃣  카드 이미지 생성 (9:16)")
    print("="*60)
    image_paths = []

    card_style = _card_style_for_date(date_str)
    print(f"  🎨 카드 스타일: {card_style}")

    for i, s in enumerate(summaries, 1):
        path = output_dir / f"{i:02d}_card.jpg"
        make_card(title=s.card_title, output_path=path)
        image_paths.append(path)
        print(f"  ✓ {path.name}: {s.card_title}")

    sources_path = output_dir / "90_sources.jpg"
    make_sources_card(
        sources=[s.source for s in summaries],
        output_path=sources_path,
    )
    image_paths.append(sources_path)
    print(f"  ✓ {sources_path.name}: 출처 카드")

    # === 4. 인스타그램 업로드 사전 체크 ===
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    has_image_hosting = (
        os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    )

    if not (ig_user_id and ig_token and has_image_hosting):
        print("\n⚠️  인스타그램/Cloudinary 환경변수 미설정 → 업로드 스킵")
        print(f"    카드 이미지는 {output_dir}에서 확인 가능합니다.")
        record_run(state, "skipped_no_upload_credentials")
        save_state(state)
        return

    # === 5. 이미지 호스팅 업로드 (재시도 포함) ===
    print("\n" + "="*60)
    print("4️⃣  이미지 호스팅 업로드 (Cloudinary)")
    print("="*60)
    image_urls = []
    for img_path in image_paths:
        url = upload_with_retry(img_path)
        image_urls.append(url)
        print(f"  ✓ {img_path.name} → {url}")

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

    caption, caption_variant = build_caption_with_variant(
        summaries, date_str, label_short=CHANNEL["label_short"],
        default_hashtags=CHANNEL["default_hashtags"])
    print(f"  📝 캡션 variant: {caption_variant}")

    media_id = publisher.post_carousel(image_urls=image_urls, caption=caption)
    print(f"\n완료! 캐러셀 Media ID: {media_id}")

    # === 6-b. Threads cross-post (A3 자동화) ===
    threads_id = None
    if post_threads.is_configured():
        try:
            threads_id = post_threads.post_thread(
                top_titles=[s.card_title for s in summaries],
                date_str=date_str,
                label_short=CHANNEL["label_short"],
                reel_link=None,
            )
        except Exception as e:
            print(f"  ⚠️  Threads 게시 실패 ({e}) — 계속 진행")

    # === 6-c. Discord 게시 완료 알림 ===
    notify_discord(
        f"✅ **daily_enter_kr 캐러셀 게시 완료**\n"
        f"• 미디어: `{media_id}`\n"
        f"• 캡션 variant: `{caption_variant}` · 카드 스타일: `{card_style}`\n"
        f"• 카드 {len(image_urls)}장 · Threads: {'✅' if threads_id else '⏭️'}\n"
        f"• 헤드라인 #1: {summaries[0].card_title if summaries else '-'}",
        username="daily_enter_kr",
    )

    # === 7. state 기록 (다음 실행의 중복 방지 + A/B variant + card_style) ===
    record_post(
        state,
        [(s.original_title, s.card_title) for s in summaries],
        caption_variant=caption_variant,
        media_id=media_id,
        card_style=card_style,
        status="success",
    )
    save_state(state)
    print(f"state.json 업데이트됨 (총 {len(state['posted_history'])}개 history)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        # state에 실패 기록 (가능하면) — 타입명 + 메시지 일부도 남겨 사후 진단 가능하도록
        try:
            st = load_state()
            msg = str(e).strip().replace("\n", " ")[:240]
            status = f"failed: {type(e).__name__}: {msg}" if msg else f"failed: {type(e).__name__}"
            record_run(st, status)
            save_state(st)
        except Exception:
            pass
        sys.exit(1)
