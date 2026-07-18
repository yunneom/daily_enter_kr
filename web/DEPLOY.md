# 배포(런치) 가이드 — 걸그룹 월드컵 웹 (개인 완주 + 전체 집계)

Next.js 14(App Router) 풀스택. 사용자가 32강부터 결승·우승까지 **직접 완주**하는 이상형 월드컵,
결과를 서버(KV)에 **집계**해 실시간 랭킹으로 보여준다.

- 화면: `/`(홈) · `/play`(1:1 대결 완주) · `/bracket`(토너먼트 트리) · `/results`(실시간 우승 랭킹) · `/admin`(보호)
- API: `POST /api/run`(완주 제출·device 중복차단) · `GET /api/results`(집계) · `/api/admin/{login,reset}` · `/api/og`
- 집계 저장소: `lib/runStore.ts` — **KV(Upstash) env 있으면 KV, 없으면 로컬 파일**(`data/web_runs.json`) 자동 전환

## 0) 로컬 구동
```bash
cd web
npm install
npm run build && npm start     # http://localhost:3000
```
- 완주하면 `data/web_runs.json`(로컬) 또는 KV 에 집계. `/results` 에서 실시간 확인.

## 1) Vercel 배포 (현재 이 방식으로 운영 중)
- GitHub 레포 연결(Git Integration) → 푸시 시 자동 배포. **Root Directory = `web`**, Framework = **Next.js**.
- **투표(완주) 영속화 = Upstash Redis(KV) 필요**: Vercel → Storage → Upstash Redis → Connect → env(`KV_REST_API_URL`/`KV_REST_API_TOKEN`) 자동 주입 → Redeploy.
  - KV 없으면 서버리스 FS 휘발성 때문에 집계가 안 쌓인다(UI·대진표는 동작).

## 2) 어드민 보호 — `ADMIN_PASSWORD` 필수
- Vercel → Settings → **Environment Variables** → `ADMIN_PASSWORD` = (원하는 비번) 추가(Production/Preview) → Redeploy.
- 미설정 시 `/admin` 은 **안전하게 잠김**(로그인 페이지가 "미설정" 안내, API 401). 설정하면 `/admin/login` 에서 로그인.
- `middleware.ts` 가 `/admin`·`/api/admin/*` 를 쿠키(`wc_admin = sha256(ADMIN_PASSWORD)`)로 게이트.

## 3) 멤버 이미지
- `web/public/members/{순위}.jpg`(또는 `.png`/`.webp`) 드롭 → 자동 표시. 없으면 그룹색 카드 폴백.
- 또는 `web/data/member_images.json` 의 순위별 값에 URL 입력.
- 순위→멤버 매핑: `web/public/members/README.md` 참고 (1=장원영, 2=제니 …).

## 4) 무료 URL 정리(선택)
- 지금은 배포별 해시 URL. **Settings → General → Project Name** 을 바꾸면 `이름.vercel.app` 고정 무료 주소 사용.
- 커스텀 도메인은 Settings → Domains(도메인 구매비만 유료, 연결은 무료).

## 5) 라운드/집계 운영 메모
- 라운드를 운영자가 개설하지 않는다. 32강 대진은 `data/worldcup_bracket.json` 의 32명·R32 대진으로 **전원 고정**.
- 결과 발표: `/results` 실시간 반영이 기본. 필요 시 어드민에서 집계 확인·초기화(`/api/admin/reset`).
- 기존 IG 자동 캠페인(`worldcup_campaign.yml` 등)과는 독립. bracket.json 은 후보 명단 소스로만 사용.

## 6) GSC 색인 재발 방지 (2026-07)

**사고 원인**: `app/layout.tsx` 의 전역 `metadata.alternates.canonical="/"` 을 `/play`,
`/shop` 이 override 하지 않아 두 페이지가 홈의 중복으로 선언됨 → GSC 에 "표준 없는
중복 페이지" / "중복 페이지(Google이 사용자가 지정한 표준 페이지와 다른 페이지 선택함)"
오류로 발생. 근본 수정으로 layout.tsx 의 전역 canonical 자체를 제거했다(더 이상
새 페이지가 canonical 을 조용히 상속할 수 없음).

운영 규칙:
1. **모든 신규 페이지는 자기참조 canonical 필수** — `export const metadata` 에
   `alternates: { canonical: "/자기라우트" }` 를 반드시 선언한다. `web/scripts/check-canonical.mjs`
   가 `app/sitemap.ts` 에 등재된 모든 라우트에 대해 이를 강제하며, Vercel `buildCommand`
   (`web/vercel.json`)와 `.github/workflows/web_seo_check.yml` 양쪽에서 위반 시 실패한다.
2. **리디렉션 URL은 사이트맵 금지** — `app/vote/page.tsx` 같은 `redirect(...)` 페이지는
   `app/sitemap.ts` 에 절대 추가하지 않는다(check-canonical 이 검사).
3. **운영자 액션(수정 배포 후)**:
   - Vercel → Settings → Domains 에서 apex(`dailyenterkr.com`)가 Primary 로 지정되어
     있고 `www` 서브도메인은 apex 로 301 리다이렉트되는지 확인.
   - GSC 색인 → 페이지 리포트에서 이번에 고친 각 오류 항목을 열고 "수정 검증" 클릭.
     재크롤·재평가에는 수 일 걸릴 수 있다.
4. **GSC 의 "리디렉션 포함 페이지" 알림은 구 링크가 외부에 남아 있으면 뜨는 정보성
   항목**이다 — 그 URL 이 `sitemap.ts` 에 없으면 크롤 예산 측면에서 무해하니 별도
   조치 불필요.
