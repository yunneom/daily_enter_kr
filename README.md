# 📰 뉴스 핫토픽 인스타 카드뉴스 자동화

매일 핫토픽 뉴스 10건을 자동 수집 → Claude로 요약 → 카드뉴스 이미지 생성 → 인스타그램 캐러셀 자동 업로드

## 📂 프로젝트 구조

```
news-instagram/
├── .github/workflows/daily.yml  # 매일 자동 실행 (GitHub Actions)
├── src/
│   ├── fetch_news.py            # 뉴스 수집 (구글 뉴스 RSS)
│   ├── summarize.py             # Claude API로 요약
│   ├── make_card.py             # PIL로 카드 이미지 생성
│   └── post_instagram.py        # 인스타 캐러셀 업로드
├── main.py                      # 전체 파이프라인
├── requirements.txt
└── README.md
```

## 🚀 빠른 시작 (로컬 테스트)

### 1. 환경 설정
```bash
pip install -r requirements.txt

# 한글 폰트 설치 (Ubuntu/Debian)
sudo apt-get install fonts-noto-cjk
# macOS는 시스템 폰트 자동 사용
# Windows는 맑은 고딕 자동 사용
```

### 2. 환경변수 설정
```bash
# .env 파일 또는 export로 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 인스타 업로드 안 하고 이미지만 만들려면 아래는 건너뛰기
export INSTAGRAM_USER_ID="17841..."
export INSTAGRAM_ACCESS_TOKEN="EAAB..."
export IMGUR_CLIENT_ID="abc123..."
```

### 3. 실행
```bash
python main.py
```

환경변수가 없으면 이미지만 생성하고 종료 → `output/YYYYMMDD/` 폴더에서 확인

## 🔑 API 키 발급 가이드

### A. Anthropic API Key (필수, 유료 - 월 $1-3)
1. https://console.anthropic.com 가입
2. Billing에 카드 등록 ($5 충전이면 1년치 사용 가능)
3. API Keys 메뉴에서 키 발급

### B. Instagram Graph API (선택 - 자동 업로드 시)

**필요한 모든 단계:**

1. **인스타 비즈니스 계정 전환**
   - 인스타 앱 > 설정 > 계정 > 프로페셔널 계정으로 전환
   
2. **Facebook 페이지 생성 및 연결**
   - https://facebook.com/pages/create 에서 페이지 생성
   - 인스타 앱에서 페이지 연결
   
3. **Meta 개발자 앱 생성**
   - https://developers.facebook.com/apps 에서 새 앱 생성
   - 유형: "비즈니스" 선택
   - "Instagram Graph API" 제품 추가
   
4. **토큰 발급**
   - Graph API Explorer에서 단기 토큰 발급
   - 다음 권한 체크: `instagram_basic`, `instagram_content_publish`, `pages_show_list`
   - 장기 토큰으로 교환 (60일 유효):
     ```
     curl -X GET "https://graph.facebook.com/v22.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={app-id}&
     client_secret={app-secret}&
     fb_exchange_token={short-lived-token}"
     ```
   
5. **Instagram Business Account ID 찾기**
   ```bash
   curl "https://graph.facebook.com/v22.0/me/accounts?access_token={token}"
   # 결과에서 Facebook 페이지 ID 확인
   
   curl "https://graph.facebook.com/v22.0/{page-id}?fields=instagram_business_account&access_token={token}"
   # 결과에서 instagram_business_account.id 확인
   ```

### C. Imgur Client ID (이미지 호스팅, 무료)
1. https://api.imgur.com/oauth2/addclient 접속
2. Anonymous usage 선택
3. Client ID만 사용 (Secret은 불필요)

## ⚙️ GitHub Actions로 자동화 (베스트)

### 1. GitHub repo 생성 후 코드 푸시

### 2. Secrets 설정
Repo > Settings > Secrets and variables > Actions > New repository secret
다음 4개를 추가:
- `ANTHROPIC_API_KEY`
- `INSTAGRAM_USER_ID`
- `INSTAGRAM_ACCESS_TOKEN`
- `IMGUR_CLIENT_ID`

### 3. 워크플로우 활성화
Actions 탭에서 워크플로우 활성화. 매일 한국시간 오전 8시에 자동 실행.

수동 테스트는 Actions > Daily Instagram News Posting > Run workflow 클릭.

## 💰 예상 비용 (월간)

| 항목 | 비용 |
|---|---|
| Anthropic API (Haiku, 일 10건) | $1-3 |
| GitHub Actions (월 2000분 무료) | $0 |
| Imgur (무료 티어) | $0 |
| Instagram API | $0 |
| **합계** | **월 $1-3** |

## ⚠️ 운영 시 주의사항

### 토큰 만료
- 인스타 장기 토큰은 60일마다 갱신 필요
- 50일째쯤 자동 갱신하는 별도 워크플로우 추가 권장

### 저작권 / 약관
- 뉴스 원문 복사 금지, "출처 명시 + 요약만" 원칙 준수
- 인스타 캡션에 자동 큐레이션 명시 권장 (코드에 이미 포함됨)
- 자극적 제목 자동 생성 방지 (프롬프트에 명시됨)

### 인스타 정책
- 자동 게시는 허용되나 과도하면 계정 제한 위험
- 일 1회 게시는 안전 범위
- 같은 캡션/이미지 반복 게시 금지

### 토큰 만료 시 갱신 코드 (참고)
```python
def refresh_long_lived_token(current_token: str, app_id: str, app_secret: str):
    url = "https://graph.facebook.com/v22.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": current_token,
    }
    resp = requests.get(url, params=params)
    return resp.json()["access_token"]
```

## 🎨 커스터마이징

### 카드 디자인 변경
`src/make_card.py`의 `COLOR_THEMES`에서 색상 변경

### 뉴스 카테고리 변경
`src/fetch_news.py`에서 RSS URL 변경:
- IT: `https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR%3Ako`
- 경제: `https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR%3Ako`

### 게시 시간 변경
`.github/workflows/daily.yml`의 cron 식 변경
- 한국시간 = UTC + 9시간
- 오전 8시 KST = `0 23 * * *` (UTC)
- 오후 6시 KST = `0 9 * * *` (UTC)
