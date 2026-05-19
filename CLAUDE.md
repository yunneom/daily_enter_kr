# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 프로젝트 컨텍스트입니다.

## 프로젝트 개요

매일 한국 뉴스 핫토픽 10건을 자동 수집 → Claude로 요약 → PIL로 카드뉴스 이미지 생성 → 인스타그램 캐러셀로 자동 업로드하는 파이프라인.

GitHub Actions가 매일 한국시간 오전 8시(UTC 23:00)에 실행. 로컬에서는 `python main.py`로 동일하게 실행 가능.

## 모듈 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 파이프라인 오케스트레이션 |
| `src/fetch_news.py` | 구글 뉴스 한국판 RSS 수집 (기본). 네이버 검색 API / 언론사 RSS 옵션도 구현되어 있음 |
| `src/summarize.py` | Claude Haiku 4.5(`claude-haiku-4-5-20251001`)로 JSON 요약 |
| `src/make_card.py` | PIL 1080x1080 카드뉴스, 그라데이션 배경 + 3가지 색상 테마(default/warm/cool) |
| `src/post_instagram.py` | Instagram Graph API v22.0 캐러셀 게시 + Imgur 이미지 호스팅 |
| `.github/workflows/daily.yml` | GitHub Actions 일일 실행 |

생성된 이미지는 `output/YYYYMMDD/` 폴더에 저장됩니다.

## 환경변수

- `ANTHROPIC_API_KEY` — 필수. 요약 단계에 사용
- `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`, `IMGUR_CLIENT_ID` — 선택. 세 개 모두 있으면 업로드까지, 하나라도 없으면 이미지 생성까지만

업로드 환경변수가 없으면 main.py는 이미지 생성 후 정상 종료합니다. 이게 의도된 동작이니 "환경변수 누락"을 오류로 처리하지 마세요.

## 로컬 실행 (Windows / PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python main.py
```

한글 폰트는 `make_card.py`가 시스템에서 자동 탐색합니다. Windows는 `C:/Windows/Fonts/malgunbd.ttf`, macOS는 AppleSDGothicNeo, Linux는 Nanum/Noto CJK. GitHub Actions 워크플로우에서는 `fonts-noto-cjk`를 apt로 설치하니 그대로 두면 됩니다.

## 자주 나오는 작업 패턴

### 카드 디자인 수정
- 색상: `src/make_card.py`의 `COLOR_THEMES` 딕셔너리
- 레이아웃 좌표: `make_card()` 내부의 `draw.text()` 호출 y_pos 값
- 폰트 크기: `font_rank`(120), `font_title`(72), `font_body`(42), `font_source`(28)
- 테마 순환: `main.py`의 `THEMES` 리스트

수정 후 `python src/make_card.py`로 단독 실행하면 샘플 카드가 생성되어 빠르게 확인 가능.

### 뉴스 소스 변경
- 카테고리별 RSS는 `README.md` 하단에 URL이 정리되어 있음
- `fetch_news.py`의 `fetch_google_news_korea()` 안의 `url` 변수 변경

### 게시 시간 변경
`.github/workflows/daily.yml`의 cron. UTC 기준이므로 한국시간 - 9시간으로 환산.

## 주의사항 (작업 시 지킬 것)

- **요약 프롬프트 톤 유지**: `SUMMARY_PROMPT`에 "자극적이지 않게", "객관적 사실 위주", "추측 배제" 조건이 들어 있음. 클릭베이트 유도 문구를 추가하지 말 것
- **인스타 API 제약**: 캐러셀 최대 10장, 첫 이미지 비율에 맞춰 모두 크롭됨 → 1080x1080 정사각형 고정. 24시간 100건 게시 제한
- **Imgur 익명 업로드**: 2023년 이후 정책 변경 이력이 있음. 업로드가 403/429로 자주 실패하면 Cloudinary나 GitHub Pages 호스팅으로 교체 고려
- **장기 토큰 60일 만료**: README 하단의 `refresh_long_lived_token()` 스니펫 참고. 50일째쯤 갱신하는 별도 워크플로우 추가가 안전
- **저작권**: 뉴스 원문 복사 금지, 요약 + 출처 표기 원칙. 캡션에 "자동 큐레이션" 명시 (이미 `build_caption()`에 포함됨)
- **모델 ID**: Anthropic 모델은 `claude-haiku-4-5-20251001` 사용 중. 변경 시 비용/품질 트레이드오프 확인

## 테스트 명령

각 모듈에 `if __name__ == "__main__"` 단독 실행 블록이 있습니다:
- `python src/fetch_news.py` — 뉴스 10건 출력 (API 키 불필요)
- `python src/summarize.py` — 3건 요약 (ANTHROPIC_API_KEY 필요)
- `python src/make_card.py` — 샘플 카드 4장 생성 (API 키 불필요, 폰트만 있으면 됨)

전체 파이프라인은 `python main.py`.
