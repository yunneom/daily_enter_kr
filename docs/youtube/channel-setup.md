# YouTube 채널 셋업 가이드 (1회)

본 문서는 1회만 설정하면 끝나는 채널 메타데이터·아트·설명 모음입니다.

## 1. 채널 아트 + 프로필 사진 (10분)

YouTube Studio → 좌측 **맞춤설정** → **브랜딩** 탭:

| 항목 | 파일 | 설명 |
|---|---|---|
| 사진 (Profile) | `docs/youtube/profile_800.png` | 800×800 그라데이션 + 📰 |
| 배너 (Banner) | `docs/youtube/banner_2560x1440.png` | 2560×1440 + 핵심 카피 |
| 동영상 워터마크 | (선택, 프로필 재사용 가능) | 80×80~150×150 |

> 이미지 재생성: `python3 scripts/generate_channel_assets.py`

## 2. 채널 설명 (5분)

YouTube Studio → 좌측 **맞춤설정** → **기본정보** 탭 → **설명**:

```
📰 매일 새로운 K-연예 밸런스 시리즈

오늘의 K-POP, 4·5세대 아이돌, 직장인 공감, 축구·여행 매트릭스까지.
"만원으로 OO 하기" 한 장 매트릭스 + 일시정지 챌린지 스피너 +
틀린 곰돌이 찾기 퍼즐을 매일 새로운 시리즈로 만나보세요.

📅 게시 일정 (KST 기준)
  · 매일 09 / 13 / 18시 매트릭스
  · 매일 21시 스피너 챌린지

🛒 오늘의 추천템 · 전체 시리즈 모음
  https://yunneom.github.io/daily_enter_kr/

📷 인스타그램 (같은 콘텐츠 + 비하인드)
  https://www.instagram.com/daily_enter_kr/

💬 협찬·콜라보·문의
  DM 또는 @daily_enter_kr

⚖️ 본 채널의 어필리에이트 콘텐츠에는
   쿠팡 파트너스 활동에 따른 수수료가 포함될 수 있습니다.

#밸런스게임 #K연예 #아이돌 #밈 #카드뉴스
```

> 위 그대로 복붙. **마지막 해시태그 줄**이 YouTube 채널 검색 SEO 의 핵심 신호입니다.

## 3. 기본정보 — 키워드 (검색 SEO)

YouTube Studio → **설정**(좌측 톱니) → **채널** → **기본 정보** → **키워드**:

```
밸런스게임, 매트릭스, K-POP, 케이팝, 아이돌, 4세대 걸그룹, 5세대 걸그룹,
직장인, 초능력, 카드뉴스, 쇼츠, shorts, 밈, 매일, 데일리연예, daily enter
```

쉼표로 구분, 띄어쓰기 OK. 채널 단위 검색 매칭 강화.

## 4. 링크 (브랜딩 탭 하단)

YouTube Studio → 맞춤설정 → **기본정보** 아래 **링크 추가**:

| 링크 제목 | URL |
|---|---|
| 인스타그램 | `https://www.instagram.com/daily_enter_kr/` |
| 오늘의 추천템 | `https://yunneom.github.io/daily_enter_kr/` |

## 5. 권한 설정 — 자동 댓글 활성화 (선택, 5분)

자동 댓글까지 켜려면 OAuth scope 재발급 1회 필요.
자세한 절차는 → `docs/youtube/scope-upgrade.md`
