/**
 * JSON-file-backed vote store at repo-root data/web_votes.json.
 *
 * NOTE (MVP): a flat JSON file is fine for local dev / low volume. For
 * production swap this module's body for a serverless DB (Vercel KV / Postgres)
 * — the function signatures (recordVote, tallyMatch) are the stable interface.
 *
 * Resolve order: env WEB_VOTES_PATH override → ../data/web_votes.json.
 * Uses synchronous fs with try/catch; self-creates the file if missing.
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
    // missing/corrupt → start fresh and self-create
    const fresh: Store = { votes: [] };
    try {
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, JSON.stringify(fresh, null, 2), "utf-8");
    } catch {
      /* read-only FS (e.g. some serverless) — keep in-memory only */
    }
    return fresh;
  }
}

function writeStore(store: Store): void {
  const p = votesPath();
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(store, null, 2), "utf-8");
}

/**
 * Append a vote. Throws Error('DUPLICATE') if the same
 * (round, quarter, slot, deviceId) already exists.
 */
export function recordVote(input: RecordVoteInput): Vote {
  const store = readStore();
  const dup = store.votes.some(
    (v) =>
      v.round === input.round &&
      v.quarter === input.quarter &&
      v.slot === input.slot &&
      v.deviceId === input.deviceId,
  );
  if (dup) {
    throw new Error("DUPLICATE");
  }
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

/** Aggregate web votes for a single match (web weight === 1 → raw == weighted). */
export function tallyMatch(round: string, quarter: number, slot: number): MatchTally {
  const store = readStore();
  let rawA = 0;
  let rawB = 0;
  for (const v of store.votes) {
    if (v.round !== round || v.quarter !== quarter || v.slot !== slot) continue;
    if (v.suspected) continue; // exclude suspected from displayed tally
    if (v.pick === "a") rawA += 1;
    else rawB += 1;
  }
  const total = rawA + rawB;
  const pctA = total === 0 ? 0 : Math.round((rawA / total) * 100);
  const pctB = total === 0 ? 0 : 100 - pctA;
  return { rawA, rawB, total, pctA, pctB };
}
