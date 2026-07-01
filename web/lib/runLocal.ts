/**
 * Personal run state persisted to localStorage. Powers /play resume and lets
 * /bracket render the user's own filled tree with their picks highlighted.
 *
 * A "column" is one round's list of duels. When a duel is decided we store the
 * winner rank. The full run is a list of rounds; the last round's single winner
 * is the champion.
 *
 * Browser-only. Shape is intentionally simple JSON so it round-trips cleanly.
 */

import type { Candidate } from "./bracketTypes";

const RUN_KEY = "wc_run_v1";

export interface StoredDuel {
  a: Candidate;
  b: Candidate;
  winnerRank: number | null;
}

export interface StoredRound {
  /** RoundKey, e.g. "R32" */
  key: string;
  /** number of candidates entering this round (32,16,8,4,2) */
  size: number;
  duels: StoredDuel[];
}

export interface StoredRun {
  version: 1;
  rounds: StoredRound[];
  championRank: number | null;
  finished: boolean;
  /** whether this finished run was already accepted by the server */
  submitted: boolean;
  updatedAt: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function loadRun(): StoredRun | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(RUN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredRun;
    if (parsed && parsed.version === 1 && Array.isArray(parsed.rounds)) return parsed;
  } catch {
    /* ignore */
  }
  return null;
}

export function saveRun(run: StoredRun): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(RUN_KEY, JSON.stringify({ ...run, updatedAt: new Date().toISOString() }));
  } catch {
    /* ignore */
  }
}

export function clearRun(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(RUN_KEY);
  } catch {
    /* ignore */
  }
}

/** Build the aggregation picks payload from a finished run. */
export function runToPicks(run: StoredRun) {
  const picks: { round: string; aRank: number; bRank: number; winnerRank: number }[] = [];
  for (const round of run.rounds) {
    for (const d of round.duels) {
      if (d.winnerRank != null) {
        picks.push({ round: round.key, aRank: d.a.rank, bRank: d.b.rank, winnerRank: d.winnerRank });
      }
    }
  }
  return picks;
}
