# 이상형 월드컵 — Web App

Single-player **이상형 월드컵** (ideal-type worldcup). Each user plays the whole
fixed 32-candidate bracket themselves (1-tap LEFT vs RIGHT duels) down to a
champion; finished runs are aggregated across all users (deduped per device) to
show live champion rankings and advancement rates. Includes a visual tournament
tree, a member-image system, and a password-protected admin.

The candidate roster is the fixed source of truth `../data/worldcup_bracket.json`
(`rounds.R32.matches` original a/b pairs). Any stored `winner` in that JSON is
IGNORED — the web run is fresh for every player.

## Run locally

```bash
cd web
npm install
npm run dev        # http://localhost:3000
# production:
npm run build && npm start
```

Node 22. Stack: **Next.js 14 App Router + TypeScript + React 18**, plain CSS only.

## Pages

| Route | What |
|---|---|
| `/` | Worldcup hero + "월드컵 시작하기" + 참가 32팀 미리보기 + live 참여수 |
| `/play` | The duel state machine (LEFT vs RIGHT, VS badge, pick animation, champion screen) |
| `/bracket` | Visual tournament tree with connecting lines; toggle 내 결과 / 전체 집계 |
| `/results` | Live aggregate leaderboard (%, count) + 진출률, polls every 5s, 발표 모드 |
| `/admin` | PROTECTED — summary + 집계 초기화 (danger) |
| `/admin/login` | Password form |
| `/vote` | redirects → `/play` (legacy URL) |

Bottom nav: 홈 · 대진표 · 결과 · 어드민. Play is entered from the home CTA.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `BRACKET_PATH` | `../data/worldcup_bracket.json` | Candidate roster source of truth |
| `WEB_RUNS_PATH` | `../data/web_runs.json` | File-backed run store (self-creates) |
| `KV_REST_API_URL` / `KV_REST_API_TOKEN` | _(unset → file backend)_ | Vercel KV / Upstash Redis |
| `UPSTASH_REDIS_REST_URL` / `_TOKEN` | _(alt to KV_*)_ | Same, alternate names |
| `ADMIN_PASSWORD` | _(unset → admin LOCKED)_ | Admin login password. **Unset = no admin access.** |

## Architecture

- **Personal run:** `/play` is a client state machine. It builds the fixed R32
  seed matches, shows one duel, and on each pick advances winners into the next
  round (adjacent winners pair up). The full run is persisted to localStorage
  (`lib/runLocal.ts`) so `/bracket` can render the user's own filled tree and
  `/play` can resume. On champion, it POSTs the run once to `/api/run`.
- **Aggregation:** `lib/runStore.ts` mirrors the old vote store's dual backend
  (Upstash Redis when KV/UPSTASH env present, else `data/web_runs.json`). One
  run per device (`wc:run:done` SADD dedup). Counters: `wc:runs_total`,
  `wc:champion:{rank}`, `wc:appear:{rank}`, `wc:pick:{rank}`, hash
  `wc:device_champ`. `getResults()` maps ranks → roster and returns champions +
  advancement (pickRate = picks / appearances).
- **Bracket tree:** `/bracket` computes columns from the seed matches. Winner of
  each duel = (1) the user's localStorage pick (내 결과) or (2) the aggregate
  consensus — higher aggregate pickRate between the two (전체 집계). CSS/flex
  columns + connector stubs, horizontally scrollable, round tabs.
- **Admin auth:** `middleware.ts` (edge) gates `/admin` + `/api/admin` except
  `*/login`. Valid cookie `wc_admin` === `sha256(ADMIN_PASSWORD)` (Web Crypto).
  If `ADMIN_PASSWORD` is unset, admin is LOCKED (never open by default). Admin
  API handlers re-check the cookie server-side (defense in depth).
- **Isomorphic vs server-only:** pure types/helpers in `lib/tournament.ts` &
  `lib/bracketTypes.ts` (client-safe). The fs-backed roster builder is
  `lib/roster.ts` (server only) — never import it from a client component.

### Key files

| Path | Purpose |
|---|---|
| `lib/tournament.ts` | Pure tournament model (seed types, nextRoundMatchups, round labels) |
| `lib/roster.ts` | SERVER-ONLY roster builder (fs via lib/bracket) |
| `lib/runStore.ts` | Aggregation store (KV/file), `submitRun` / `getResults` / `resetAll` |
| `lib/runLocal.ts` | localStorage personal-run persistence + `runToPicks` |
| `lib/colors.ts` | Group color palette + gradients |
| `lib/memberImages.ts` | Reads `data/member_images.json` (rank → URL) |
| `lib/adminAuth.ts` | sha256 (Web Crypto), expected-token, cookie check |
| `lib/safety.ts` | `assertSafeCopy` (banned words + emoji) — used by `/api/og` |
| `components/MemberImage.tsx` | Photo with URL → /members file → gradient fallback chain |
| `middleware.ts` | Admin gate (edge) |

## Member images

Real photos are added by the owner later. Two ways to add an image for a member
(identified by their **rank**, 1..32):

1. **Drop a file** in `web/public/members/` named by rank:
   `web/public/members/1.jpg` (also `.png` / `.webp` are tried, in that order).
2. **Paste a URL** into `web/data/member_images.json`, e.g.
   `{ "1": "https://.../wonyoung.jpg", ... }`. An empty string means "no URL".

Resolution order per member: `member_images.json` URL → `/members/{rank}.jpg`
→ `.png` → `.webp` → group-colored gradient block with the member's name. No
config needed — `MemberImage` uses a plain `<img>` with an `onError` fallback
chain.

## Safety policy

`lib/safety.ts` enforces the same guardrails as the Python `SUMMARY_PROMPT`: no
clickbait `BANNED_WORDS`, no emoji in copy. `/api/og` runs `assertSafeCopy` on
dynamic text and falls back to neutral copy on violation.

## Open items

- **[가정]** Realtime: `/results` polls every 5s (simplicity over SSE/websocket).
- **[결정필요]** Production store: Upstash Redis via KV env vars recommended;
  the file backend does not persist on serverless/read-only FS.
- **[가정]** The aggregate "consensus" bracket resolves each later-round duel by
  comparing global pickRate of the two entrants — this is an approximation, not
  a replay of any single user's path (later rounds legitimately diverge per user).
- Member photos are not bundled (gradient fallbacks) pending a licensed source.
