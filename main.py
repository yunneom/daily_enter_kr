"""
메인 파이프라인
매일 실행되어 뉴스 수집 → 요약 → 카드 생성 → 인스타 업로드까지 전체 처리

[실행 방법]
로컬: python main.py
GitHub Actions: workflow가 자동 실행
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# src 폴더를 path에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetch_news import fetch_google_news_korea
from summarize import summarize_news
from make_card import make_card, make_cover_card
from post_instagram import InstagramPublisher, upload_to_imgur, build_caption


# 카드별 색상 테마 순환
THEMES = ["default", "warm", "cool", "default", "warm", 
          "cool", "default", "warm", "cool", "default"]


def main():
    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    output_dir = Path(__file__).parent / "output" / today.strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # === 1. 뉴스 수집 ===
    print("\n" + "="*60)
    print("1️⃣  뉴스 수집")
    print("="*60)
    news_items = fetch_google_news_korea(limit=10)
    for i, n in enumerate(news_items, 1):
        print(f"  [{i}] {n.title[:50]}...")
    
    # === 2. 요약 ===
    print("\n" + "="*60)
    print("2️⃣  Claude API로 요약")
    print("="*60)
    if os.environ.get("ANTHROPIC_API_KEY"):
        summaries = summarize_news(news_items)
    else:
        print("⚠️  ANTHROPIC_API_KEY 미설정 → 원제목을 카드 내용으로 사용")
        from summarize import SummarizedNews
        summaries = [
            SummarizedNews(
                original_title=n.title,
                card_title=n.title[:18],
                card_body=n.title,
                hashtags=["#오늘의뉴스"],
                source=n.source,
                link=n.link,
            )
            for n in news_items
        ]
    for i, s in enumerate(summaries, 1):
        print(f"  [{i}] {s.card_title}")
    
    # === 3. 카드 이미지 생성 ===
    print("\n" + "="*60)
    print("3️⃣  카드뉴스 이미지 생성")
    print("="*60)
    image_paths = []
    
    # 표지
    cover_path = output_dir / "00_cover.jpg"
    make_cover_card(date_str=date_str, output_path=cover_path)
    image_paths.append(cover_path)
    print(f"  ✓ 표지: {cover_path.name}")
    
    # 각 뉴스 카드 (9개, 표지 포함 총 10개)
    for i, s in enumerate(summaries[:9], 1):
        path = output_dir / f"{i:02d}_card.jpg"
        make_card(
            rank=i,
            title=s.card_title,
            body=s.card_body,
            source=s.source,
            output_path=path,
            theme=THEMES[i-1],
        )
        image_paths.append(path)
        print(f"  ✓ {path.name}: {s.card_title}")
    
    # === 4. 인스타그램 업로드 ===
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    imgur_id = os.environ.get("IMGUR_CLIENT_ID")
    
    if not (ig_user_id and ig_token and imgur_id):
        print("\n⚠️  인스타그램 환경변수 미설정 → 업로드 스킵")
        print("    이미지는 output 폴더에서 확인 가능합니다.")
        print(f"    위치: {output_dir}")
        return
    
    print("\n" + "="*60)
    print("4️⃣  Imgur에 이미지 업로드")
    print("="*60)
    image_urls = []
    for path in image_paths:
        url = upload_to_imgur(path, imgur_id)
        image_urls.append(url)
        print(f"  ✓ {path.name} → {url}")
    
    print("\n" + "="*60)
    print("5️⃣  인스타그램 캐러셀 게시")
    print("="*60)
    publisher = InstagramPublisher(ig_user_id, ig_token)
    caption = build_caption(summaries[:9], date_str)
    media_id = publisher.post_carousel(image_urls, caption)
    
    print(f"\n🎉 완료! 게시물 ID: {media_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
