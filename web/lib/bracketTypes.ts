/**
 * Isomorphic bracket types + pure helpers (no fs). Safe to import from both
 * server and client components. The fs-backed loader lives in lib/bracket.ts.
 */

export type RoundKey = "R32" | "R16" | "R8" | "R4" | "R2" | "R1";

export const ROUND_ORDER: RoundKey[] = ["R32", "R16", "R8", "R4", "R2", "R1"];

export interface Candidate {
  rank: number;
  group: string;
  member: string;
  score?: number;
}

export interface Votes {
  a: number;
  b: number;
  raw_a: number;
  raw_b: number;
}

export interface Match {
  quarter: number;
  slot: number;
  round: string;
  a: Candidate;
  b: Candidate;
  winner: Candidate | null;
  votes?: Votes;
  type?: string; // R2: "final" | "third_place"
}

export interface Round {
  matches: Match[];
  posts?: unknown[];
  winner?: Candidate | null;
}

export interface Bracket {
  tournament: string;
  source: string;
  seed_method: string;
  deterministic_seed: number;
  quarters: Candidate[][];
  rounds: Record<string, Round>;
  current_round: string;
  winner: Candidate | null;
}

const ROUND_LABELS: Record<string, string> = {
  R32: "32강",
  R16: "16강",
  R8: "8강",
  R4: "4강",
  R2: "결승·3·4위전",
  R1: "우승",
};

export function roundLabel(key: string): string {
  return ROUND_LABELS[key] ?? key;
}

export function listMatches(b: Bracket, round: string): Match[] {
  return b.rounds[round]?.matches ?? [];
}

export function getRound(b: Bracket, key: string): Round | undefined {
  return b.rounds[key];
}

export function getMatch(
  b: Bracket,
  round: string,
  quarter: number,
  slot: number,
): Match | undefined {
  return listMatches(b, round).find((m) => m.quarter === quarter && m.slot === slot);
}

/**
 * Next unvoted match recommendation.
 * votedKeys is a Set of `${quarter}-${slot}` already voted by this device.
 * Priority:
 *   1. same quarter, adjacent slot (pairs 0↔1, 2↔3)
 *   2. quarters in A→B→C→D (0→1→2→3) order, lowest slot first
 *   3. null (nothing left → go to bracket)
 * Only matches whose winner is still null are eligible.
 */
export function nextUnvotedMatch(
  b: Bracket,
  round: string,
  votedKeys: Set<string>,
  current?: { quarter: number; slot: number },
): Match | null {
  const matches = listMatches(b, round).filter((m) => m.winner === null);
  const key = (m: Match) => `${m.quarter}-${m.slot}`;
  const isOpen = (m: Match) => !votedKeys.has(key(m));

  if (current) {
    const adjacentSlot = current.slot % 2 === 0 ? current.slot + 1 : current.slot - 1;
    const adj = matches.find(
      (m) => m.quarter === current.quarter && m.slot === adjacentSlot && isOpen(m),
    );
    if (adj) return adj;
  }

  const ordered = [...matches].sort((m1, m2) =>
    m1.quarter !== m2.quarter ? m1.quarter - m2.quarter : m1.slot - m2.slot,
  );
  const next = ordered.find(isOpen);
  return next ?? null;
}
