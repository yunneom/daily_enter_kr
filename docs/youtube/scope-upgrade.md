# YouTube OAuth scope 업그레이드 — 자동 댓글 활성화 (1회)

## 왜

현재 `YOUTUBE_REFRESH_TOKEN` 은 **`youtube.upload`** scope (영상 업로드만).
자동 댓글은 **`youtube.force-ssl`** scope 가 필요. 현재 토큰으로 댓글 시도하면 **403**.

> 코드는 이미 자동 댓글 기능 포함 — 토큰만 업그레이드하면 즉시 작동. 안 해도 영상 업로드는 정상.

## 절차 (5분)

### 1. OAuth Playground 재인증

1. https://developers.google.com/oauthplayground 접속 (시크릿 창 권장)
2. **⚙️(톱니)** → **Use your own OAuth credentials** 체크 → 기존 **웹 클라이언트 ID/Secret** 그대로 (이전에 받은 것)
3. 좌측 **"Input your own scopes"** 에 정확히 (한 줄에 띄어쓰기로 구분):
   ```
   https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl
   ```
   - 두 scope 다 들어가야 함 — upload 도 유지하면서 댓글 권한 추가
4. **Authorize APIs** → 채널 계정 선택 → 동의
   - "확인되지 않은 앱" → 고급 → 이동
5. **Exchange authorization code for tokens** → **새 Refresh token** 복사

### 2. GitHub Secrets 업데이트

https://github.com/yunneom/daily_enter_kr/settings/secrets/actions

`YOUTUBE_REFRESH_TOKEN` → **Update** → 방금 받은 새 토큰으로 교체

(Client ID/Secret 은 그대로 — 같은 클라이언트)

### 3. 검증 — 다음 cron 게시 로그

게시 후 Actions 로그에서:

```
✅ YouTube Shorts 게시! https://youtube.com/shorts/...
💬 YouTube 댓글: UgxXX...     ← 토픽별 미션 (1번째)
💬 YouTube 댓글: UgxYY...     ← 어필리에이트 + 디스클로저 (2번째)
```

만약 여전히 `⚠️ YouTube 댓글 403` 이 나오면:
- refresh_token 이 옛날 그대로 들어간 것 → 다시 1단계부터
- 또는 scope 입력 시 띄어쓰기 잘못 → 정확히 위 형식대로

## 기존 refresh_token 은?

업로드만 되니 그대로 둬도 됩니다 — 새 token 으로 덮어쓰면 끝.
구 token 은 자동 폐기되진 않지만, 사용은 안 됨.
