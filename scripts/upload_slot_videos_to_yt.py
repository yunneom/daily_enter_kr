"""
슬롯머신 영상 2건 YT 자동 업로드 — 시그니처 사운드 시드 + 콘텐츠 동시 노출.

[교체 배경]
이전 build_signature_videos.py + upload_signature_to_yt.py = 정적 시그니처 영상.
"아무것도 없이 올리니까 애매" → 슬롯머신 영상에 시그니처 음원 깔아 2건 게시로
콘텐츠 가치 + 음원 시드 동시.

[전제]
- YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN 환경변수
- output_enter/publish/slot_{girl,boy}group_5x3.mp4 사전 빌드
  (slot_girlgroup → A BGM, slot_boygroup → C BGM)

[흐름]
1. 두 mp4 를 @daily_enter_kr YT Shorts 로 업로드 → 음원 페이지 자동 생성
2. 사용자가 폰 IG 앱으로 같은 mp4 1번씩 수동 업로드 → IG 원본 오디오 라벨 등록
3. 이후 자동 게시(매트릭스/월드컵)가 같은 mp3 합성 → IG fingerprint 매칭 가능
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import post_youtube  # noqa: E402


META = {
    "slot_girlgroup_5x3": {
        "bgm_tone": "A (밝은 K-pop)",
        "title": "🎰 슬롯머신 걸그룹 조합 — 일시정지로 픽! #Shorts",
        "description": "\n".join([
            "🎰 슬롯머신 걸그룹 5×3 = 125 조합",
            "일시정지로 멈춰서 본인 픽 — 기회 3번!",
            "",
            "장원영·카리나·민지·안유진·닝닝·카즈하·하니·지젤·사쿠라·해린·윈터·리즈·허윤진·다니엘",
            "",
            "🎵 BGM: Daily Enter Theme A (오리지널 — @daily_enter_kr)",
            "📲 매일 새로운 픽: instagram.com/daily_enter_kr",
            "",
            "#Shorts #쇼츠 #슬롯머신 #케이팝 #kpop #밸런스게임 #일시정지챌린지",
        ]),
        "tags": ["#Shorts", "#쇼츠", "#슬롯머신", "#케이팝", "#kpop",
                 "#밸런스게임", "#일시정지챌린지", "#걸그룹조합"],
        "category": "24",  # Entertainment
    },
    "slot_boygroup_5x3": {
        "bgm_tone": "C (다크 게임)",
        "title": "🎰 슬롯머신 보이그룹 조합 — 일시정지로 픽! #Shorts",
        "description": "\n".join([
            "🎰 슬롯머신 보이그룹 5×3 = 125 조합",
            "일시정지로 멈춰서 본인 픽 — 기회 3번!",
            "",
            "필릭스·정원·태현·승한·성한빈·현진·니키·휴닝카이·앤톤·산·성훈·연준·원빈·윤호·장하오",
            "",
            "🎵 BGM: Daily Enter Theme C (오리지널 — @daily_enter_kr)",
            "📲 매일 새로운 픽: instagram.com/daily_enter_kr",
            "",
            "#Shorts #쇼츠 #슬롯머신 #케이팝 #kpop #밸런스게임 #일시정지챌린지",
        ]),
        "tags": ["#Shorts", "#쇼츠", "#슬롯머신", "#케이팝", "#kpop",
                 "#밸런스게임", "#일시정지챌린지", "#보이그룹조합"],
        "category": "24",
    },
}


def main():
    if not post_youtube.is_configured():
        print("❌ YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN 미설정")
        return 1
    out_dir = ROOT / "output_enter" / "publish"
    results = []
    for tid, meta in META.items():
        mp4 = out_dir / f"{tid}.mp4"
        if not mp4.exists():
            print(f"❌ {mp4} 없음 — 슬롯 mp4 먼저 빌드")
            return 1
        print(f"\n📤 업로드: [{meta['bgm_tone']}] {meta['title'][:50]}...")
        try:
            yt_id = post_youtube.upload_short(
                mp4, meta["title"], meta["description"],
                tags=meta["tags"], category_id=meta["category"],
            )
            url = f"https://youtu.be/{yt_id}" if yt_id else None
            results.append((tid, yt_id, url, meta["bgm_tone"]))
            print(f"  ✓ {url}")
        except Exception as e:
            print(f"  ❌ {tid} 실패: {e}")
            results.append((tid, None, None, meta["bgm_tone"]))

    print("\n" + "=" * 60)
    print("✅ 슬롯머신 YT 업로드 결과 (시그니처 사운드 시드):")
    for tid, yt_id, url, tone in results:
        if url:
            print(f"  [{tone}] {tid}")
            print(f"    {url}")
    print()
    print("📌 다음 단계 — 사용자 폰 IG 앱에서:")
    print("  1) 위 두 mp4 를 IG @daily_enter_kr 에 Reels 1번씩 수동 게시")
    print("  2) IG 가 '@daily_enter_kr · 원본 오디오' 라벨 자동 등록")
    print("  3) 이후 자동 게시 (월드컵/매트릭스) 가 IG fingerprint 매칭 가능")
    return 0 if all(r[1] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
