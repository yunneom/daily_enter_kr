/**
 * Run store — cross-user aggregation for the single-player 이상형 월드컵.
 * Async, dual backend (mirrors lib/voteStore.ts):
 *
 *   • Vercel KV / Upstash Redis — when KV_REST_API_URL(+token) or
 *     UPSTASH_REDIS_REST_URL(+token) are present.
 *   • JSON file (repo-root data/web_runs.json) — local dev / persistent-disk
 *     self-host. Resolve: env WEB_RUNS_PATH → ../data.
 *
 * A "run" = one user finishing the whole bracket. Deduped per device: a device
 * counts at most once. The file backend stores raw runs + a done-list and
 * computes counters on read; the KV backend keeps incrementing counters.
 *
 * KV key model:
 *   wc:run:done            → SET of deviceId (SADD result 0 == duplicate)
 *   wc:runs_total          → INCR
 *   wc:champion:{rank}     → INCR per champion
 *   wc:appear:{rank}       → INCR per appearance in a played match
 *   wc:pick:{rank}         → INCR per time picked as winner
 *   wc:device_champ        → HASH deviceId → championRank
 */

import fs from "fs";
import path from "path";
import { loadRoster } from "./roster";
import type { Candidate } from "./bracketTypes";

export interface RunPick {
  round: string;
  aRank: number;
  bRank: number;
  winnerRank: number;
}

export interface SubmitRunInput {
  deviceId: string;
  championRank: number;
  picks: RunPick[];
}

export interface SubmitRunResult {
  counted: boolean;
}

export interface ChampionRow {
  rank: number;
  group: string;
  member: string;
  count: number;
  pct: number;
}

export interface AdvancementRow {
  rank: number;
  group: string;
  member: string;
  picks: number;
  appears: number;
  pickRate: number;
}

export interface Results {
  runsTotal: number;
  champions: ChampionRow[];
  advancement: AdvancementRow[];
}

// ── backend selection ──────────────────────────────────────────────────────

interface KvEnv {
  url: string;
  token: string;
}

function kvEnv(): KvEnv | null {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) return { url, token };
  return null;
}

export function usingKv(): boolean {
  return kvEnv() !== null;
}

const K = {
  done: "wc:run:done",
  runsTotal: "wc:runs_total",
  champion: (rank: number) => `wc:champion:${rank}`,
  appear: (rank: number) => `wc:appear:${rank}`,
  pick: (rank: number) => `wc:pick:${rank}`,
  deviceChamp: "wc:device_champ",
};

let redisClient: import("@upstash/redis").Redis | null = null;
async function getRedis(env: KvEnv) {
  if (redisClient) return redisClient;
  const { Redis } = await import("@upstash/redis");
  redisClient = new Redis({ url: env.url, token: env.token });
  return redisClient;
}

// ── validation ──────────────────────────────────────────────────────────────

function isValidInput(input: SubmitRunInput, byRank: Record<number, Candidate>): boolean {
  if (!input || typeof input.deviceId !== "string" || !input.deviceId) return false;
  if (typeof input.championRank !== "number" || !byRank[input.championRank]) return false;
  if (!Array.isArray(input.picks) || input.picks.length === 0) return false;
  for (const p of input.picks) {
    if (typeof p.round !== "string" || !p.round) return false;
    if (
      typeof p.aRank !== "number" ||
      typeof p.bRank !== "number" ||
      typeof p.winnerRank !== "number"
    )
      return false;
    if (p.winnerRank !== p.aRank && p.winnerRank !== p.bRank) return false;
    if (!byRank[p.aRank] || !byRank[p.bRank]) return false;
  }
  return true;
}

// ── KV backend ───────────────────────────────────────────────────────────────

async function kvSubmit(env: KvEnv, input: SubmitRunInput): Promise<SubmitRunResult> {
  const redis = await getRedis(env);
  const added = await redis.sadd(K.done, input.deviceId);
  if (added === 0) return { counted: false };

  const p = redis.multi();
  p.incr(K.runsTotal);
  p.incr(K.champion(input.championRank));
  p.hset(K.deviceChamp, { [input.deviceId]: input.championRank });
  for (const pick of input.picks) {
    p.incr(K.appear(pick.aRank));
    p.incr(K.appear(pick.bRank));
    p.incr(K.pick(pick.winnerRank));
  }
  await p.exec();
  return { counted: true };
}

async function kvResults(env: KvEnv, roster: ReturnType<typeof loadRoster>): Promise<Results> {
  const redis = await getRedis(env);
  const ranks = roster.candidates.map((c) => c.rank);

  const runsTotal = Number((await redis.get<number>(K.runsTotal)) ?? 0);

  const champKeys = ranks.map((r) => K.champion(r));
  const appearKeys = ranks.map((r) => K.appear(r));
  const pickKeys = ranks.map((r) => K.pick(r));

  const [champVals, appearVals, pickVals] = await Promise.all([
    champKeys.length ? redis.mget<(number | null)[]>(...champKeys) : Promise.resolve([]),
    appearKeys.length ? redis.mget<(number | null)[]>(...appearKeys) : Promise.resolve([]),
    pickKeys.length ? redis.mget<(number | null)[]>(...pickKeys) : Promise.resolve([]),
  ]);

  const champCount: Record<number, number> = {};
  const appearCount: Record<number, number> = {};
  const pickCount: Record<number, number> = {};
  ranks.forEach((r, i) => {
    champCount[r] = Number(champVals[i] ?? 0);
    appearCount[r] = Number(appearVals[i] ?? 0);
    pickCount[r] = Number(pickVals[i] ?? 0);
  });

  return buildResults(roster, runsTotal, champCount, appearCount, pickCount);
}

async function kvReset(env: KvEnv, roster: ReturnType<typeof loadRoster>): Promise<void> {
  const redis = await getRedis(env);
  const ranks = roster.candidates.map((c) => c.rank);
  const keys = [
    K.done,
    K.runsTotal,
    K.deviceChamp,
    ...ranks.map((r) => K.champion(r)),
    ...ranks.map((r) => K.appear(r)),
    ...ranks.map((r) => K.pick(r)),
  ];
  await redis.del(...keys);
}

// ── file backend ─────────────────────────────────────────────────────────────

interface FileRun {
  deviceId: string;
  championRank: number;
  picks: RunPick[];
}

interface FileStore {
  runs: FileRun[];
  done: string[];
}

function runsPath(): string {
  const override = process.env.WEB_RUNS_PATH;
  if (override) return override;
  return path.resolve(process.cwd(), "..", "data", "web_runs.json");
}

function readStore(): FileStore {
  const p = runsPath();
  try {
    const raw = fs.readFileSync(p, "utf-8");
    const parsed = JSON.parse(raw) as Partial<FileStore>;
    return {
      runs: Array.isArray(parsed.runs) ? parsed.runs : [],
      done: Array.isArray(parsed.done) ? parsed.done : [],
    };
  } catch {
    return { runs: [], done: [] };
  }
}

function writeStore(store: FileStore): void {
  const p = runsPath();
  try {
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, JSON.stringify(store, null, 2), "utf-8");
  } catch {
    /* read-only FS — best effort */
  }
}

function fileSubmit(input: SubmitRunInput): SubmitRunResult {
  const store = readStore();
  if (store.done.includes(input.deviceId)) return { counted: false };
  store.done.push(input.deviceId);
  store.runs.push({
    deviceId: input.deviceId,
    championRank: input.championRank,
    picks: input.picks,
  });
  writeStore(store);
  return { counted: true };
}

function fileResults(roster: ReturnType<typeof loadRoster>): Results {
  const store = readStore();
  const champCount: Record<number, number> = {};
  const appearCount: Record<number, number> = {};
  const pickCount: Record<number, number> = {};

  for (const run of store.runs) {
    champCount[run.championRank] = (champCount[run.championRank] ?? 0) + 1;
    for (const pick of run.picks) {
      appearCount[pick.aRank] = (appearCount[pick.aRank] ?? 0) + 1;
      appearCount[pick.bRank] = (appearCount[pick.bRank] ?? 0) + 1;
      pickCount[pick.winnerRank] = (pickCount[pick.winnerRank] ?? 0) + 1;
    }
  }

  return buildResults(roster, store.runs.length, champCount, appearCount, pickCount);
}

function fileReset(): void {
  writeStore({ runs: [], done: [] });
}

// ── shared result assembly ───────────────────────────────────────────────────

function buildResults(
  roster: ReturnType<typeof loadRoster>,
  runsTotal: number,
  champCount: Record<number, number>,
  appearCount: Record<number, number>,
  pickCount: Record<number, number>,
): Results {
  const champions: ChampionRow[] = roster.candidates
    .map((c) => {
      const count = champCount[c.rank] ?? 0;
      const pct = runsTotal > 0 ? Math.round((count / runsTotal) * 1000) / 10 : 0;
      return { rank: c.rank, group: c.group, member: c.member, count, pct };
    })
    .sort((x, y) => y.count - x.count || x.rank - y.rank);

  const advancement: AdvancementRow[] = roster.candidates
    .map((c) => {
      const picks = pickCount[c.rank] ?? 0;
      const appears = appearCount[c.rank] ?? 0;
      const pickRate = appears > 0 ? Math.round((picks / appears) * 1000) / 10 : 0;
      return { rank: c.rank, group: c.group, member: c.member, picks, appears, pickRate };
    })
    .sort((x, y) => y.pickRate - x.pickRate || y.picks - x.picks || x.rank - y.rank);

  return { runsTotal, champions, advancement };
}

// ── public API ────────────────────────────────────────────────────────────────

export async function submitRun(input: SubmitRunInput): Promise<SubmitRunResult> {
  const roster = loadRoster();
  if (!isValidInput(input, roster.byRank)) {
    throw new Error("INVALID_RUN");
  }
  const env = kvEnv();
  if (env) return kvSubmit(env, input);
  return fileSubmit(input);
}

export async function getResults(): Promise<Results> {
  const roster = loadRoster();
  const env = kvEnv();
  if (env) return kvResults(env, roster);
  return fileResults(roster);
}

export async function resetAll(): Promise<void> {
  const roster = loadRoster();
  const env = kvEnv();
  if (env) return kvReset(env, roster);
  return fileReset();
}
