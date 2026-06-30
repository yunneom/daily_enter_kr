/**
 * Vote store — async, dual backend, auto-selected at runtime.
 *
 *   • Vercel KV / Upstash Redis  — used when KV_REST_API_URL (+ token) or
 *     UPSTASH_REDIS_REST_URL (+ token) env vars are present (serverless/prod).
 *   • JSON file (repo-root data/web_votes.json) — fallback for local dev /
 *     self-host with a persistent disk. Resolve: env WEB_VOTES_PATH → ../data.
 *
 * Public interface (stable): recordVote() / tallyMatch(). Both async.
 * recordVote throws Error('DUPLICATE') when the same
 * (round, quarter, slot, deviceId) already voted.
 *
 * KV key model:
 *   wc:voted:{round}:{q}:{s}      → SET of deviceId  (dedup via SADD result)
 *   wc:tally:{round}:{q}:{s}:a|b  → INCR counter
 */

import fs from "fs";
import path from "path";
import crypto from "crypto";

export interface Vote {
  id: string;
  round: string;
  quarter: number;
  slot: number;
  pick: "a" | "b";
  deviceId: string;
  ipHash?: string;
  uaHash?: string;
  createdAt: string;
  suspected: boolean;
}

interface Store {
  votes: Vote[];
}

export interface RecordVoteInput {
  round: string;
  quarter: number;
  slot: number;
  pick: "a" | "b";
  deviceId: string;
  ipHash?: string;
  uaHash?: string;
  suspected?: boolean;
}

export interface MatchTally {
  rawA: number;
  rawB: number;
  total: number;
  pctA: number;
  pctB: number;
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

/** True when a serverless KV/Redis backend is configured. */
export function usingKv(): boolean {
  return kvEnv() !== null;
}

function votedKey(round: string, q: number, s: number): string {
  return `wc:voted:${round}:${q}:${s}`;
}
function tallyKey(round: string, q: number, s: number, pick: "a" | "b"): string {
  return `wc:tally:${round}:${q}:${s}:${pick}`;
}

function pct(rawA: number, rawB: number): MatchTally {
  const total = rawA + rawB;
  const pctA = total === 0 ? 0 : Math.round((rawA / total) * 100);
  const pctB = total === 0 ? 0 : 100 - pctA;
  return { rawA, rawB, total, pctA, pctB };
}

// ── KV (Upstash Redis REST) backend ─────────────────────────────────────────

// Cache the client across invocations on a warm lambda.
let redisClient: import("@upstash/redis").Redis | null = null;
async function getRedis(env: KvEnv) {
  if (redisClient) return redisClient;
  const { Redis } = await import("@upstash/redis");
  redisClient = new Redis({ url: env.url, token: env.token });
  return redisClient;
}

async function kvRecord(env: KvEnv, input: RecordVoteInput): Promise<Vote> {
  const redis = await getRedis(env);
  // SADD returns the number of NEW members added: 0 means duplicate device.
  const added = await redis.sadd(
    votedKey(input.round, input.quarter, input.slot),
    input.deviceId,
  );
  if (added === 0) throw new Error("DUPLICATE");
  await redis.incr(tallyKey(input.round, input.quarter, input.slot, input.pick));
  return {
    id: crypto.randomUUID(),
    round: input.round,
    quarter: input.quarter,
    slot: input.slot,
    pick: input.pick,
    deviceId: input.deviceId,
    ipHash: input.ipHash,
    uaHash: input.uaHash,
    createdAt: new Date().toISOString(),
    suspected: input.suspected ?? false,
  };
}

async function kvTally(env: KvEnv, round: string, q: number, s: number): Promise<MatchTally> {
  const redis = await getRedis(env);
  const [a, b] = await Promise.all([
    redis.get<number>(tallyKey(round, q, s, "a")),
    redis.get<number>(tallyKey(round, q, s, "b")),
  ]);
  return pct(Number(a ?? 0), Number(b ?? 0));
}

// ── File backend (local dev / persistent-disk self-host) ─────────────────────

function votesPath(): string {
  const override = process.env.WEB_VOTES_PATH;
  if (override) return override;
  return path.resolve(process.cwd(), "..", "data", "web_votes.json");
}

function readStore(): Store {
  const p = votesPath();
  try {
    const raw = fs.readFileSync(p, "utf-8");
    const parsed = JSON.parse(raw) as Partial<Store>;
    return { votes: Array.isArray(parsed.votes) ? parsed.votes : [] };
  } catch {
    const fresh: Store = { votes: [] };
    try {
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, JSON.stringify(fresh, null, 2), "utf-8");
    } catch {
      /* read-only FS — keep in-memory only */
    }
    return fresh;
  }
}

function writeStore(store: Store): void {
  const p = votesPath();
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(store, null, 2), "utf-8");
}

function fileRecord(input: RecordVoteInput): Vote {
  const store = readStore();
  const dup = store.votes.some(
    (v) =>
      v.round === input.round &&
      v.quarter === input.quarter &&
      v.slot === input.slot &&
      v.deviceId === input.deviceId,
  );
  if (dup) throw new Error("DUPLICATE");
  const vote: Vote = {
    id: crypto.randomUUID(),
    round: input.round,
    quarter: input.quarter,
    slot: input.slot,
    pick: input.pick,
    deviceId: input.deviceId,
    ipHash: input.ipHash,
    uaHash: input.uaHash,
    createdAt: new Date().toISOString(),
    suspected: input.suspected ?? false,
  };
  store.votes.push(vote);
  writeStore(store);
  return vote;
}

function fileTally(round: string, quarter: number, slot: number): MatchTally {
  const store = readStore();
  let rawA = 0;
  let rawB = 0;
  for (const v of store.votes) {
    if (v.round !== round || v.quarter !== quarter || v.slot !== slot) continue;
    if (v.suspected) continue;
    if (v.pick === "a") rawA += 1;
    else rawB += 1;
  }
  return pct(rawA, rawB);
}

// ── public API (dispatches to the active backend) ────────────────────────────

/** Append a vote. Throws Error('DUPLICATE') on a repeat device for the match. */
export async function recordVote(input: RecordVoteInput): Promise<Vote> {
  const env = kvEnv();
  if (env) return kvRecord(env, input);
  return fileRecord(input);
}

/** Aggregate web votes for one match (web weight === 1 → raw == weighted). */
export async function tallyMatch(round: string, quarter: number, slot: number): Promise<MatchTally> {
  const env = kvEnv();
  if (env) return kvTally(env, round, quarter, slot);
  return fileTally(round, quarter, slot);
}
