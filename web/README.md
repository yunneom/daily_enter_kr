# 걸그룹 월드컵 — Web Voting App

Mobile-first 1:1 voting web app for the existing **걸그룹 월드컵 (32강)** tournament.
Users vote one match at a time (1-tap, no login), see live %, browse the bracket,
share results, and operators control round state from an admin screen.

It is **not** a new tournament — it reads/writes the existing single source of
truth `../data/worldcup_bracket.json` and reuses the existing winner rules.

## Run locally

```bash
cd web
npm install
npm run dev        # http://localhost:3000
# production:
npm run build && npm start
```

Node 22. Stack: **Next.js 14 App Router + TypeScript + React 18**, plain CSS only
(no Tailwind, no UI libs).

## Environment variables (all optional in dev)

| Var | Default | Purpose |
|---|---|---|
| `BRACKET_PATH` | `../data/worldcup_bracket.json` | Read-only bracket source of truth |
| `WEB_VOTES_PATH` | `../data/web_votes.json` | File-backed web vote store (self-creates) |
| `WEB_ADMIN_PATH` | `../data/web_admin.json` | Round-state overrides (open/lock) |
| `ADMIN_KEY` | _(unset → allow)_ | Required as `x-admin-key` header for admin writes |

## Architecture

```
web vote (1-tap)
  → POST /api/vote → lib/voteStore.ts → data/web_votes.json   (file-backed, MVP)
  → scripts/worldcup_web_sync.py (GitHub Actions)             (aggregate + decide winner)
  → data/worldcup_bracket.json                                 (single source of truth)
  → existing worldcup_announce / worldcup_tally pipeline       (publish, next round)
```

- **App Router**, server components read the bracket via `lib/bracket.ts`
  (fs at request time, `dynamic = "force-dynamic"`). API routes use the Node runtime.
- **File-backed store for MVP.** `lib/voteStore.ts` writes a flat JSON file. For
  production swap the body for a serverless DB (Vercel KV / Postgres) — the
  `recordVote` / `tallyMatch` signatures are the stable interface.
- **Isomorphic vs server-only split:** pure types + helpers live in
  `lib/bracketTypes.ts` (safe for client). `lib/bracket.ts` adds the fs loader and
  must not be imported from client components.

### Key files

| Path | Purpose |
|---|---|
| `lib/bracketTypes.ts` | Types + pure helpers (roundLabel, getMatch, nextUnvotedMatch) |
| `lib/bracket.ts` | fs-backed `loadBracket()` (server only) |
| `lib/winner.ts` | `decideWinner` (가중→raw→rank) + `fourChoiceToMatches` |
| `lib/voteStore.ts` | `recordVote` (dedup → throws `DUPLICATE`) / `tallyMatch` |
| `lib/adminStore.ts` | Round-state file store |
| `lib/status.ts` | `matchStatus` → OPEN / LOCKED / DECIDED |
| `lib/safety.ts` | `assertSafeCopy` / `isSafeCopy` (banned words + emoji) |
| `lib/device.ts` | Client deviceId + voted-key localStorage helpers |
| `app/api/*` | bracket / match / vote / og / admin route handlers |

## Integration notes

- **Coordinates:** matches are keyed by `(quarter, slot)` — same as the Python
  pipeline. The web sync writes back to both `rounds[r].matches[]` and the
  `posts[].match1/match2` copies by `(quarter, slot)`.
- **Winner rule** (replicated exactly from `scripts/worldcup_tally.py`
  `decide_winners.pick()`): ① weighted (`votes.a/b`) → ② raw head count
  (`votes.raw_a/raw_b`) → ③ higher seed (lower `rank`). Web vote weight = 1, so
  weighted == raw for web-only matches.
- **4지선다 → 2매치:** `fourChoiceToMatches` (match1 A=1+2 B=3+4; match2 A=1+3
  B=2+4) is kept for a future IG-vote merge; not used by web 1:1 voting.
- The IG `topic_id` join key (`worldcup_{round}_{idx}`) used by the announce
  pipeline is **untouched** by this app.

## Safety policy enforcement

`lib/safety.ts` enforces the same brand guardrails as the Python `SUMMARY_PROMPT`:
no clickbait `BANNED_WORDS`, no emoji, numbers allowed, source
`한국기업평판연구소` attributable. `assertSafeCopy` runs on dynamic OG/share text;
on violation the OG card / share copy falls back to neutral safe text.

## Python sync

```bash
python3 scripts/worldcup_web_sync.py            # current_round, overwrite with web counts
python3 scripts/worldcup_web_sync.py --round R8 # specific round
python3 scripts/worldcup_web_sync.py --merge-ig # add web counts onto existing IG weighted votes
python3 scripts/worldcup_web_sync.py --dry-run  # summary only, no write
```

Pure stdlib, idempotent. Matches with 0 web votes keep `winner = null` (no seed
auto-advance — final decision belongs to the announce step). Re-implements the
small `pick()` rather than importing the tally module (avoids coupling); keep it
in sync with `scripts/worldcup_tally.py` `decide_winners`.

## MVP vs Next

**MVP (shipped here)**
- File-backed vote store; deviceId + localStorage dedup; server-side
  (round,quarter,slot,deviceId) dedup → 409.
- Result polling every 4s. Admin auth stubbed via `ADMIN_KEY` header.
- Image placeholders (dashed boxes); OG card is text-only.

**Open decisions** — tagged in code:
- **[가정]** Realtime: polling (4s) vs SSE/websocket. Polling chosen for MVP simplicity.
- **[결정필요]** Web-vote weighting: currently 1 per device. Should IG-derived
  weight (1+likes) ever apply to web votes, or stay head-count?
- **[결정필요]** Production store: Vercel KV vs Postgres vs Redis. File store does
  not work on read-only/serverless FS at scale.
- **[결정필요]** IG vote merge: run `--merge-ig` or keep web/IG tallies separate
  per round? Double-counting risk if both channels vote the same match.
- **[결정필요]** Face image usage / 저작권: member photos are not bundled (placeholders
  only) pending a licensed image source. The image_provider concept exists in the
  Python side but is currently unused.
- **[가정]** Anti-abuse: only deviceId + ip/ua hashes recorded; no rate limiting or
  bot scoring yet (`suspected` flag reserved for future filtering).
```
