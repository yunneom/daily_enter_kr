# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 프로젝트 컨텍스트입니다.

## 프로젝트 개요

K-연예 뉴스 핫토픽 10건을 매일 자동 수집 → Claude로 안전 분류·SEO 카피 생성 → PIL로 미니멀 카드뉴스 생성 (흰 배경 + 검정 제목) → Cloudinary 호스팅 → Instagram 캐러셀로 자동 게시.

운영 계정: `@daily_enter_kr`
스케줄: 매일 한국시간 오전 8시 (UTC 23:00) + 0–90분 random jitter (봇 패턴 회피)

## 모듈 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 파이프라인 오케스트레이션 + 중복 체크 + jitter + 토큰 health check |
| `src/fetch_news.py` | Google News RSS (`entertainment` topic 기본). 20건 수집 |
| `src/summarize.py` | Claude Haiku 4.5. **안전 분류 (post/respectful/skip) + 제목-only SEO 카피** |
| `src/make_card.py` | PIL 1080x1080. 미니멀 — 흰 배경 + 검정 제목 한 줄(자동 축소·트렁케이트) + 출처/아웃트로 카드 |
| `src/post_instagram.py` | Instagram Graph (`graph.instagram.com`) v22.0. IGAA 토큰 + Cloudinary 우선 + health_check |
| `src/state.py` | 중복 게시 방지 (14일 윈도우) + 실행 이력 + 토큰 만료 추적. `state.json` 읽고 씀 |
| `exchange_token.py` | IGAA 단기→장기 토큰 교환, refresh 폴백 자동, `.env` + state 자동 업데이트 |
| `fetch_insights.py` | 최근 게시물 like/comment 스냅샷 → `insights.json` (A/B 분석 기반) |
| `state.json` | 운영 state — 매 실행마다 워크플로우가 git에 commit 함 |
| `insights.json` | 게시물 인사이트 시계열 — 매 실행 끝에 워크플로우가 commit |
| `.github/workflows/daily.yml` | 매일 실행 + state/insights commit-back + Discord 알림(선택) |
| `.github/workflows/refresh_token.yml` | 수동 트리거 — IGAA 장기 토큰 refresh (60일 만료 임박 시) |

생성된 이미지는 `output/YYYYMMDD/` 폴더에 저장 (gitignore).

## 환경변수 (`.env` 또는 GitHub Secrets)

| 변수 | 필수 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✓ | Claude API. 없으면 안전 분류 불가 → 게시 차단 |
| `INSTAGRAM_USER_ID` | 업로드 시 | 17841...로 시작하는 16-17자리 |
| `INSTAGRAM_ACCESS_TOKEN` | 업로드 시 | IGAA... 60일 장기 토큰 |
| `INSTAGRAM_APP_SECRET` | 토큰 갱신 시 | `exchange_token.py`가 사용 |
| `CLOUDINARY_CLOUD_NAME` | 업로드 시 | dwiq...같은 호스트 식별자 |
| `CLOUDINARY_UPLOAD_PRESET` | 업로드 시 | Unsigned upload preset 이름 |
| `DISCORD_WEBHOOK_URL` | 선택 | 워크플로우 실패 시 Discord 알림 (없으면 GH 이메일 폴백) |
| `CHANNEL` | 선택 | 채널 ID (예: `daily_enter_kr`). 미설정 시 기본값 사용 |

API 키 누락 시 안전 분류 없이 게시하는 것을 차단 (안전 우선). 카드 이미지는 생성하지만 인스타 업로드는 스킵됨.

## 안전 정책 (요약 프롬프트)

`src/summarize.py`의 `SUMMARY_PROMPT`가 다음을 보장:

**자동 skip 사유** — 게시하지 않음:
- 자살/극단적 선택/유서/투신 (인용·암시 포함)
- 폭력/성범죄/학대 피해자 신원 추측 가능
- 만 18세 미만 외모/사생활/연애
- 동의 없는 연인 추측, 신체/성형 비교, 의학적 진단명 가십화
- 정치 정쟁
- 사실 확인 안 된 자극적 단독

**respectful 톤 전환** — 부고/투병/공식 사회적 메시지 등.

**클릭베이트 어휘 금지** — "충격", "발칵", "경악", "오열", "폭로", "이럴 수가", "결국", "도대체".

**저작권 변형 강제** — 본문은 원기사 문장 그대로 X, 110자 이내, 출처 자동 표기.

이 정책은 평판/저작권/IG ToS 모두에 직결됨. 카피 톤을 강하게 만들고 싶더라도 이 가드레일은 유지할 것.

## 운영 안전장치

| 메커니즘 | 위치 | 동작 |
|---|---|---|
| 중복 게시 차단 | `state.py.filter_duplicates` | 14일 안 동일 제목 해시 skip |
| 최소 카드 수 | `main.MIN_CARDS=3` | 3개 미만이면 게시 스킵 (1-2장 카루셀 방지) |
| 업로드 재시도 | `main.upload_with_retry` | Cloudinary 업로드 최대 3회 + 지수 백오프 |
| 토큰 health check | `post_instagram.health_check` | 게시 직전 토큰 유효성 확인, 무효 시 가이드 메시지와 함께 종료 |
| Cron jitter | `main.apply_cron_jitter` | CI에서만 0-90분 랜덤 지연 (봇 패턴 회피). 워크플로우 `timeout-minutes`는 jitter 최대값 + 파이프라인 여유로 책정 |
| state commit-back | `daily.yml` 워크플로우 | 매 실행 후 `state.json` 자동 commit (감사 추적) |

## 로컬 실행 (Windows / PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # 값 채우기
$env:PYTHONIOENCODING="utf-8"
python main.py
```

한글 폰트는 시스템에서 자동 탐색 (Windows: malgunbd.ttf, macOS: AppleSDGothicNeo, Linux: NanumGothicBold/NotoSansCJK).

## 토큰 갱신 (50일째쯤)

```powershell
python exchange_token.py --refresh
# 출력된 새 토큰으로 GitHub Secrets의 INSTAGRAM_ACCESS_TOKEN 업데이트
```

## 자주 나오는 작업 패턴

### 카드 디자인 수정
- 색상/배경: `src/make_card.py` 상단의 `BG_COLOR` / `TEXT_COLOR` / `SUBTLE_COLOR`
- 본문 카드 폰트 사이즈 범위 (1줄 강제): `_fit_title_single_line()`의 `size_max`(기본 110) / `size_min`(36). 안 들어가면 '…' 트렁케이트
- 표지(아웃트로) 폰트 사이즈: `make_cover_card()` 내부의 `f_big` / `f_mid` / `f_date`
- 출처 카드 폰트 사이즈: `make_sources_card()` 내부의 `f_label` / `f_item`
- 좌우 여백: `SIDE_MARGIN`
- 캐러셀 순서: 본문 N장 → 출처(`90_sources.jpg`) → 표지(`99_outro.jpg`). 변경은 `main.py`의 image_paths 순서 조정

### 토픽 변경
- `fetch_news.py`의 `TOPIC_URLS`에 다른 토픽 추가 또는
- `main.py`의 `fetch_google_news_korea(topic=...)` 호출 인자 변경

### 게시 시간 변경
`.github/workflows/daily.yml`의 cron — UTC 기준이므로 KST - 9시간.

## 주의사항 (작업 시 지킬 것)

- **안전 프롬프트 수정 시**: skip 목록 약화 금지. 추가만 허용
- **클릭베이트 어휘 추가 금지**: IG 정책 위반 위험. 인용/따옴표 강조도 자제
- **제목 길이**: 카드엔 본문이 없고 제목만 한 줄로 노출. summarize 프롬프트의 14-22자 가이드 준수 — 너무 길면 폰트 자동 축소 후에도 안 들어가면 끝이 '…'로 잘림
- **모델 ID**: `claude-haiku-4-5-20251001` 사용. 변경 시 비용/품질 영향 평가
- **인스타 API 제약**: 캐러셀 최대 10장, 1:1 비율 고정, 24시간 100건 한도
- **토큰 60일 만료**: 만료 전 갱신. 자동 갱신은 GitHub Actions에서 PAT 필요 (현재 미적용)

## 테스트 명령

```powershell
python src/fetch_news.py     # 뉴스 수집 (API 키 불필요)
python src/summarize.py      # 안전 분류 + 요약 5건 (ANTHROPIC_API_KEY 필요)
python src/make_card.py      # 본문 5장 + 출처 + 아웃트로 샘플 (한글 폰트만 있으면 됨)
python fetch_insights.py     # 최근 게시 인사이트 (IG 토큰 필요)
python main.py               # 전체 파이프라인 (CHANNEL 환경변수로 채널 선택)

# 다른 채널 테스트:
$env:CHANNEL="daily_sports_kr"; python main.py
$env:CHANNEL="daily_economy_kr"; python main.py
```

## 시크릿 관리

`python sync_secrets.py` 한 번으로 `.env`의 모든 값을 GitHub Secrets에 동기화. gh CLI 필요.

```powershell
python sync_secrets.py                  # .env에 있는 모든 알려진 시크릿 동기화
python sync_secrets.py UNSPLASH_ACCESS_KEY  # 특정 키만
python sync_secrets.py --dry-run        # 무엇이 바뀔지만 미리보기
```

값은 화면에 마스킹 표시. stdin으로 gh에 전달해 커맨드라인 노출 없음.

## 배경 이미지 시스템 (현재 미사용)

카드 디자인이 미니멀(흰 배경)로 전환되며 외부 이미지가 더 이상 합성되지 않음. 다만 `src/image_provider.py` 와 summarize 프롬프트의 `visual_concept` 필드는 보존(나중에 다른 디자인 변형이 필요해질 때 즉시 활용 가능).

- 현재 `main.py` 는 `image_provider` 를 import 하지 않음 → 호출 0건 → Unsplash 쿼터 소모 없음
- `UNSPLASH_ACCESS_KEY` 시크릿도 사실상 불필요해졌으나 제거하지 않아도 무해

## 다중 채널 운영

현재 구성된 채널: `daily_enter_kr` (운영 중), `daily_sports_kr`, `daily_economy_kr` (코드/워크플로우 준비, 계정 미세팅).

### 새 채널 활성화 — Meta 측 (수동, 약 30-60분)

1. **새 IG 비즈니스 계정 생성**: 인스타 앱에서 `daily_sports_kr` 등 새 계정 추가 → 비즈니스 전환
2. **새 FB 페이지 생성 + IG 연결**: facebook.com/pages/create → 만든 페이지의 Settings → Linked accounts → Instagram 연결
3. **기존 Meta 앱에 새 IG 계정 추가**: developers.facebook.com → news-instagram-bot 앱 → 앱 역할 → Instagram 테스터 → 새 IG 계정 사용자명 입력 → 초대
4. **새 IG 계정으로 초대 수락**: https://www.instagram.com/accounts/manage_access/ 직접 접속 → Tester Invites 탭 → 수락
5. **새 IG 계정의 단기 토큰 발급**: Meta 앱 → Instagram → API setup → Generate access tokens → 새 IG 계정 선택
6. **단기 토큰 → 장기**: `.env` INSTAGRAM_ACCESS_TOKEN 임시 교체 후 `python exchange_token.py` (또는 `--refresh`)

### 새 채널 활성화 — GitHub 시크릿

기존 시크릿 외에 채널별로 추가:

| Sports | Economy |
|---|---|
| `INSTAGRAM_USER_ID_SPORTS` | `INSTAGRAM_USER_ID_ECONOMY` |
| `INSTAGRAM_ACCESS_TOKEN_SPORTS` | `INSTAGRAM_ACCESS_TOKEN_ECONOMY` |
| `INSTAGRAM_APP_SECRET_SPORTS` (선택; 미설정 시 기본 _ 재사용) | `INSTAGRAM_APP_SECRET_ECONOMY` (동) |

CLI 한 줄로:
```
gh secret set INSTAGRAM_USER_ID_SPORTS --repo yunneom/daily_enter_kr --body "17841..."
gh secret set INSTAGRAM_ACCESS_TOKEN_SPORTS --repo yunneom/daily_enter_kr --body "IGAA..."
```

### 새 채널 활성화 — 워크플로우

이미 `.github/workflows/daily_sports.yml`, `daily_economy.yml` 생성됨. 시크릿만 세팅되면 자동 활성화. cron 시각:

| 채널 | cron (UTC) | KST |
|---|---|---|
| daily_enter_kr | `0 23 * * *` | 08:00 |
| daily_sports_kr | `0 0 * * *` | 09:00 |
| daily_economy_kr | `0 1 * * *` | 10:00 |

각 jitter 0-90분 적용 → 실제 게시 윈도우는 08:00-09:30, 09:00-10:30, 10:00-11:30. 현재 sports/economy는 schedule 비활성. 활성화 시 채널간 1시간 간격으론 윈도우 겹침 → cron 시각을 더 벌리거나 채널별 jitter 상한을 줄여야 함.

### 새 채널 추가 (sports/economy 외)

`main.py`의 `CHANNELS` dict에 항목 + 새 워크플로우 파일 복제. ~10분 코드 작업.
