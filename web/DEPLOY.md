# 배포(런치) 가이드 — 걸그룹 월드컵 웹 투표

이 앱은 Next.js 14(App Router) 풀스택이다. 프런트(투표/대진표/공유/어드민) + API 라우트
(`/api/bracket`, `/api/match`, `/api/vote`, `/api/og`, `/api/admin/round`) + 투표 저장소
(`lib/voteStore.ts`) + 파이썬 동기화(`scripts/worldcup_web_sync.py`)로 구성된다.

## 0) 로컬에서 바로 구동 (지금 동작 검증됨)
```bash
cd web
npm install
npm run build && npm start      # http://localhost:3000  (풀 기능: 투표 영속 저장됨)
# 또는 개발 모드
npm run dev
```
- 투표는 레포 루트 `data/web_votes.json` 에 누적된다(파일 저장소, 영속).
- 대진표는 `data/worldcup_bracket.json` 을 그대로 읽는다.
- 웹표를 bracket 으로 수렴: `python3 scripts/worldcup_web_sync.py --round R8`(미리보기 `--dry-run`).

> **자체 호스팅(영속 디스크 있는 곳: VPS·Render·Railway·Fly 등)** 에서는 위 그대로 풀스택으로 동작한다.
> `npm run build && npm start` 를 프로세스 매니저(pm2/systemd)로 띄우면 끝.

## 1) Vercel 배포
1. GitHub 레포를 Vercel 에 임포트.
2. **Root Directory = `web`** 로 지정 (중요).
3. 빌드는 `web/vercel.json` 의 `buildCommand`(`copy-bracket.mjs` → `next build`)가 처리한다.
   - 레포 루트는 web/ 밖이라 배포 번들에 안 들어가므로, 빌드 시 `data/worldcup_bracket.json`
     스냅샷을 `web/data/` 로 복사한다. bracket.json 이 갱신될 때마다 푸시→자동 재배포되어 최신 유지.
4. 환경변수(선택): `ADMIN_KEY`(어드민 API 헤더 키). `BRACKET_PATH`(커스텀 경로).

### ⚠️ Vercel 의 투표 영속성 — [결정필요]
Vercel 서버리스 함수의 파일시스템은 **쓰기 불가/휘발성**이라 `data/web_votes.json` 파일 저장소로는
투표가 영속되지 않는다. 운영 배포에서 실제 투표를 받으려면 `lib/voteStore.ts` 본문을
서버리스 DB 로 교체해야 한다(시그니처 `recordVote`/`tallyMatch` 는 그대로 유지 = 교체 지점 1곳).
- 추천: **Vercel KV(Upstash Redis)** 또는 **Vercel Postgres / Neon**.
- 자격증명(KV/DB URL)을 주시면 어댑터 구현 + 연결까지 진행 가능.

즉 Vercel 에서 **UI·대진표·OG 는 즉시 동작**하고, **투표 영속은 DB 어댑터 추가 후** 완성된다.

## 2) IG ↔ 웹 동기화 자동화
- `.github/workflows/worldcup_web_sync.yml` (수동 dispatch): `web_votes.json` → `bracket.json`
  votes/winner 수렴 후 commit-back. 승자 규칙(가중→raw→rank)·`(quarter,slot)` 좌표를 기존
  `worldcup_tally.py` 와 동일하게 적용 → 기존 `worldcup_campaign.yml` 의 announce 단계와 연결.
- 운영 DB 도입 시: 이 워크플로 앞에 "DB→web_votes.json 덤프" 스텝을 추가하거나 sync 가 DB 를 직접 읽도록 변경.

## 3) 런치 체크리스트
- [ ] 자체호스팅이면 `npm start` 프로세스 상시화 → **풀 기능 라이브 완료**
- [ ] Vercel 이면 Root=web 임포트 → UI/대진표 라이브, 투표용 DB 어댑터 연결
- [ ] (선택) 커스텀 도메인 + IG 게시물 딥링크 UTM/topic_id 연결
- [ ] `ADMIN_KEY` 설정 후 어드민 접근 제한 (현재 MVP 는 헤더 키 stub)
