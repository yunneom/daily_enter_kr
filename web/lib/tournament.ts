/**
 * Single-elimination tournament model for the single-player 이상형 월드컵.
 *
 * Everyone plays the SAME fixed 32-candidate seed bracket built from the
 * repo-root bracket JSON's `rounds.R32.matches` original a/b pairs (the web run
 * is fresh — any existing `winner` in the JSON is IGNORED here).
 *
 * Tree:  R32 (16 matches) → R16 (8) → R8 (4) → R4 (2) → Final (1) → Champion.
 * Parent pairing: seed matches 2k & 2k+1 feed the same next-round match, in the
 * existing match order. Round 1 (R32) is identical for every user, so its picks
 * aggregate cleanly; later rounds diverge per user (expected).
 *
 * This module is ISOMORPHIC where possible. The fs-backed roster loader
 * `loadRoster()` MUST only be called on the server (it pulls in lib/bracket ->
 * node fs). Client components receive the roster/seed as serialized props, then
 * use the pure helpers (nextRoundMatchups, roundKeyForSize, roundLabelBySize…).
 */

import type { Candidate } from "./bracketTypes";

export type { Candidate };

export interface SeedMatch {
  /** index in seed order 0..15 */
  index: number;
  a: Candidate;
  b: Candidate;
}

/** A generic duel used throughout the client state machine. */
export interface Duel {
  a: Candidate;
  b: Candidate;
}

/** Round keys sized by how many candidates remain. */
export type SizeRound = 32 | 16 | 8 | 4 | 2 | 1;

export const ROUND_SIZES: SizeRound[] = [32, 16, 8, 4, 2, 1];

const ROUND_LABEL_BY_SIZE: Record<number, string> = {
  32: "32강",
  16: "16강",
  8: "8강",
  4: "4강",
  2: "결승",
  1: "우승",
};

/**
 * Human label for the round that is playing when `size` candidates remain.
 * Note: 준결승 is the round producing the final two — i.e. when 4 remain the
 * matches are 4강, and the round with 2 remaining IS the final (결승).
 */
export function roundLabelBySize(size: number): string {
  return ROUND_LABEL_BY_SIZE[size] ?? `${size}강`;
}

/** RoundKey string used in aggregation picks. */
export function roundKeyForSize(size: number): string {
  return `R${size}`;
}

/**
 * Compute the next round's matchups given the winners of the current round,
 * in order. Adjacent winners (2k, 2k+1) pair up. Requires an even count > 1.
 */
export function nextRoundMatchups(winners: Candidate[]): Duel[] {
  const duels: Duel[] = [];
  for (let i = 0; i + 1 < winners.length; i += 2) {
    duels.push({ a: winners[i], b: winners[i + 1] });
  }
  return duels;
}

/** True when only the champion remains. */
export function isChampionReached(remaining: number): boolean {
  return remaining <= 1;
}

// ── candidate identity helpers ──────────────────────────────────────────────

export function candKey(c: Candidate): number {
  return c.rank; // rank is the stable unique id (1..32)
}

export function sameCand(a: Candidate | null | undefined, b: Candidate | null | undefined): boolean {
  return !!a && !!b && a.rank === b.rank;
}

/**
 * Shape of a fully-built roster. The fs-backed builder lives in lib/roster.ts
 * (SERVER ONLY) so this module stays isomorphic / client-safe.
 */
export interface Roster {
  /** ordered list of the 32 candidates (seed order, a then b per match) */
  candidates: Candidate[];
  /** the 16 fixed first-round matches */
  seeds: SeedMatch[];
  /** rank → candidate lookup */
  byRank: Record<number, Candidate>;
  tournamentName: string;
  source: string;
}
