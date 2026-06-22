# 분석 아키텍처 — IG / YouTube / abc 송 퍼널

@daily_enter_kr 의 크로스플랫폼 성과 + 음원(abc 송) 퍼널을 추적하는 데이터 파이프라인.

## 데이터 흐름

```
publish_matrix.py (게시)
   │  게시마다 topic_id · ig_media_id · youtube_id · bgm 반환
   ▼
post_ledger.json  ◀── 조인 키 (src/post_ledger.py)
   │   topic_id ─┬─ ig_media_id   → insights.json
   │             └─ youtube_id    → insights_youtube.json
   ▼
fetch_insights.py (게시 후, 4회/일)
   │   게시별: plays/reach/saved/shares/likes/comments
   │   계정 단위: profile_views / website_clicks / reach / follower_count  ← abc송 퍼널 프록시
   ▼
insights.json (v3)
   │
cross_platform_report.py (게시 후)
   │   ledger + insights.json(IG) + insights_youtube.json(YT) 조인
   ▼
docs/digests/cross_platform.html  +  Discord 요약
```

## 파일 계약

### `post_ledger.json` (src/post_ledger.py 가 씀)
```json
{
  "version": 1,
  "entries": [
    {
      "posted_at": "2026-06-22T09:03:00+09:00",
      "topic_id": "brand_rep_girlgroup",
      "title": "걸그룹 개인 브랜드평판 TOP30",
      "style": "brand_chart",
      "seed": 1234,
      "ig_media_id": "1801...",
      "youtube_id": "abcD",      // 없으면 null
      "threads_id": null,
      "bgm": "abc_song.mp3"      // 어떤 음원이 깔렸는지 (BGM A/B)
    }
  ]
}
```
보존 120일. IG↔YT↔topic↔음원 의 단일 조인 소스.

### `insights.json` (v3, fetch_insights.py 가 씀)
스냅샷마다 `account` 블록 추가됨 (v3):
```json
{
  "snapshot_at": "...",
  "account": {
    "profile_views": 142,    // 오디오/게시물 → 프로필 방문 (abc송 퍼널 1단계)
    "website_clicks": 18,    // bio 링크(=YT) 클릭 (abc송 퍼널 최종)
    "reach": 2300,
    "accounts_engaged": 210,
    "follower_count": 512
  },
  "posts": [ { "media_id": "...", "reach": ..., "shares": ..., ... } ]
}
```

> **정직한 한계**: IG Graph API 는 **오디오 페이지별 클릭 수를 노출하지 않음**.
> abc 송의 트래픽 기여는 `profile_views` + `website_clicks` 의 **도입 전/후 추세 비교**로
> 근사한다. 음원 전용 전환일을 기준으로 이 두 지표가 오르면 음원 효과 신호.

### `insights_youtube.json` (⏳ #1 이 2주 뒤 생성 — 계약 미리 고정)
cross_platform_report.py 가 이 포맷을 기대함. #1(YT Shorts 인사이트 수집)은 아래대로 쓰면
크로스플랫폼 리포트가 **코드 변경 없이 자동 점등**:
```json
{
  "version": 1,
  "snapshots": [
    {
      "snapshot_at": "2026-07-06T09:05:00+09:00",
      "videos": [
        {
          "video_id": "abcD",                  // ← ledger.youtube_id 와 조인
          "views": 3200,
          "likes": 140,
          "comments": 22,
          "average_view_percentage": 68.5,     // retention % (YT Analytics)
          "avg_view_duration_sec": 12.3
        }
      ]
    }
  ]
}
```
필수 키: `video_id`, `views`, `average_view_percentage`. 나머지는 선택.
YouTube Analytics API (`youtubeAnalytics.reports.query`, 또는 Data API `videos.list?part=statistics`)
에서 수집. 인증은 이미 있는 `YOUTUBE_REFRESH_TOKEN` 재사용 (단 `yt-analytics.readonly` scope 필요할 수 있음).

## 리포트 3개 섹션

1. **abc 송 퍼널** — profile_views·website_clicks 일별 추세 (음원→프로필→bio→YT)
2. **토픽별 IG↔YT** — 같은 mp4 가 두 플랫폼에서 어떻게 다른지 (어느 쪽이 이 콘텐츠에 강한가)
3. **BGM A/B** — 음원별 평균 IG reach/shares/saved (abc 송 vs 기존 ambient)

## 실행

```bash
python fetch_insights.py          # IG 게시별 + 계정 퍼널 스냅샷 (IG 토큰 필요)
python cross_platform_report.py   # 조인 + HTML + Discord (토큰 불필요 — 파일만 읽음)
python src/post_ledger.py         # 원장 현황 요약 (점검용)
```

워크플로우(`publish_matrix.yml`)가 게시 4회/일마다 자동 실행 + 커밋.

## 2주 뒤 #1 도착 시 할 일

1. `insights_youtube.json` 을 위 계약대로 생성하는 수집기 작성 (`fetch_youtube_insights.py`)
2. `publish_matrix.yml` 에 수집 스텝 + 커밋 대상에 `insights_youtube.json` 추가
3. 끝 — cross_platform_report.py 가 자동으로 YT 컬럼 점등 (대기→실데이터)
