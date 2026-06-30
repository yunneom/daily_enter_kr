/**
 * Match status derivation. Combines the bracket (winner / current_round) with
 * the admin override state.
 *
 *   DECIDED — match.winner != null (winner already announced)
 *   OPEN    — round === current_round, winner == null, and not admin-LOCKED
 *   LOCKED  — otherwise (future round, or admin locked the round)
 */

import type { Bracket, Match } from "@/lib/bracketTypes";
import { getRoundState } from "@/lib/adminStore";

export type MatchStatus = "OPEN" | "LOCKED" | "DECIDED";

export function matchStatus(b: Bracket, round: string, match: Match): MatchStatus {
  if (match.winner !== null) return "DECIDED";
  const admin = getRoundState(round);
  if (admin?.state === "LOCKED") return "LOCKED";
  if (round === b.current_round) return "OPEN";
  return "LOCKED";
}
