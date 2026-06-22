"""
시그니처 영상 YT 자동 업로드 — output/signature_theme_{a,c}.mp4 → @daily_enter_kr YT.

[전제]
- YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN 환경변수 설정됨 (Actions secret 재사용)
- scripts/build_signature_videos.py 가 미리 mp4 생성

[출력]
- YT 영상 URL 2개 (A·C). 그 URL 을 MUSIC_YT_URL 시크릿에 넣으면 음악 크레딧 자동 노출.
- post_youtube.upload_short 재사용 (이미 60s 미만 Shorts 호환).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import post_youtube  # noqa: E402


META = {
    "A": {
        "title": "Daily Enter Theme A — Bright K-pop Hook (Original) #Shorts",
        "description": "\n".join([
            "Daily Enter Theme A — 시그니처 사운드",
            "@daily_enter_kr 의 모든 K-연예 매트릭스/밸런스게임 콘텐츠 BGM",
            "",
            "🎵 본인 채널: youtube.com/@daily_enter_kr",
            "📲 매일 새로운 픽: instagram.com/daily_enter_kr",
            "",
            "#DailyEnterTheme #Shorts #쇼츠 #케이팝 #kpop #밸런스게임 #시그니처사운드",
        ]),
        "tags": ["#DailyEnterTheme", "#Shorts", "#쇼츠", "#케이팝", "#밸런스게임"],
        "category": "10",  # Music
    },
    "C": {
        "title": "Daily Enter Theme C — Dark Slot Game BGM (Original) #Shorts",
        "description": "\n".join([
            "Daily Enter Theme C — 게임/슬롯/월드컵 시그니처 사운드",
            "@daily_enter_kr 의 모든 슬롯머신·월드컵 토너먼트 BGM",
            "",
            "🎵 본인 채널: youtube.com/@daily_enter_kr",
            "📲 매일 새로운 픽: instagram.com/daily_enter_kr",
            "",
            "#DailyEnterTheme #Shorts #쇼츠 #슬롯머신 #월드컵 #밸런스게임 #시그니처사운드",
        ]),
        "tags": ["#DailyEnterTheme", "#Shorts", "#쇼츠", "#슬롯머신", "#월드컵"],
        "category": "10",  # Music
    },
}


def main():
    if not post_youtube.is_configured():
        print("❌ YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN 미설정 — Actions secret 확인")
        return 1
    out_dir = ROOT / "output_enter" / "publish"
    results = []
    for variant in ["A", "C"]:
        mp4 = out_dir / f"signature_theme_{variant.lower()}.mp4"
        if not mp4.exists():
            print(f"❌ {mp4} 없음 — build_signature_videos.py 먼저 실행")
            return 1
        meta = META[variant]
        print(f"\n📤 업로드 시작: {meta['title'][:50]}...")
        try:
            yt_id = post_youtube.upload_short(
                mp4, meta["title"], meta["description"],
                tags=meta["tags"], category_id=meta["category"],
            )
            url = f"https://youtu.be/{yt_id}" if yt_id else None
            results.append((variant, yt_id, url))
            print(f"  ✓ {variant}: {url}")
        except Exception as e:
            print(f"  ❌ {variant} 실패: {e}")
            results.append((variant, None, None))

    # 결과 요약 — MUSIC_YT_URL 시크릿 설정 가이드
    print("\n" + "=" * 60)
    print("✅ 시그니처 영상 업로드 결과:")
    for variant, yt_id, url in results:
        if url:
            print(f"  {variant}: {url}")
    print()
    print("📌 GitHub Secret 설정 (음악 크레딧 자동 노출용):")
    for variant, yt_id, url in results:
        if url:
            label = "A (메인)" if variant == "A" else "C (게임/슬롯)"
            print(f"  MUSIC_YT_URL_{variant} = {url}  → {label}")
    print()
    print("→ 현재 music_credit.py 는 MUSIC_YT_URL 단일 변수 — A 추천.")
    print("  컨텍스트별 분기 필요시 music_credit 확장 가능.")
    return 0 if all(r[1] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
