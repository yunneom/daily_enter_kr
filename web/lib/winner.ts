/**
 * Winner decision rule — replicates scripts/worldcup_tally.py `decide_winners.pick()` EXACTLY.
 *
 * Priority:
 *   ① weighted tally (votes.a / votes.b) — higher wins
 *   ② raw head count (votes.raw_a / votes.raw_b) — higher wins
 *   ③ higher seed (lower `rank`) wins
 *
 * For WEB votes weight === 1, so weighted === raw and rule ① and ② coincide.
 */

export type Pick = "a" | "b";

/**
 * decideWinner — mirrors Python pick(wa, wb, ra, rb, m):
 *   if (wa !== wb) return wa > wb ? 'a' : 'b';
 *   if (ra !== rb) return ra > rb ? 'a' : 'b';
 *   return rankA <= rankB ? 'a' : 'b';
 *
 * Unit-test-style expectations:
 *   decideWinner(5, 3, 0, 0, 1, 2) === 'a'   // weighted A wins
 *   decideWinner(3, 5, 0, 0, 1, 2) === 'b'   // weighted B wins
 *   decideWinner(4, 4, 7, 2, 9, 1) === 'a'   // tie weighted, raw A wins
 *   decideWinner(4, 4, 2, 7, 9, 1) === 'b'   // tie weighted, raw B wins
 *   decideWinner(4, 4, 3, 3, 1, 9) === 'a'   // all tie, rank A (1) <= rank B (9) → A
 *   decideWinner(4, 4, 3, 3, 9, 1) === 'b'   // all tie, rank A (9) >  rank B (1) → B
 */
export function decideWinner(
  wa: number,
  wb: number,
  ra: number,
  rb: number,
  rankA: number,
  rankB: number,
): Pick {
  if (wa !== wb) return wa > wb ? "a" : "b"; // ① weighted
  if (ra !== rb) return ra > rb ? "a" : "b"; // ② raw head count
  return rankA <= rankB ? "a" : "b"; // ③ higher seed (lower rank)
}

export interface FourChoiceCounts {
  "1": number;
  "2": number;
  "3": number;
  "4": number;
}

export interface MatchPair {
  a: number;
  b: number;
}

export interface FourChoiceMatches {
  match1: MatchPair;
  match2: MatchPair;
}

/**
 * 4지선다 → 2매치 conversion (for future IG-vote merge).
 * Given counts {"1","2","3","4"}:
 *   match1 A = (1 + 2), B = (3 + 4)
 *   match2 A = (1 + 3), B = (2 + 4)
 * Apply identically to both weighted and raw tallies.
 *
 * Unit-test-style expectations:
 *   fourChoiceToMatches({"1":1,"2":2,"3":3,"4":4})
 *     => { match1: { a: 3, b: 7 }, match2: { a: 4, b: 6 } }
 */
export function fourChoiceToMatches(counts: FourChoiceCounts): FourChoiceMatches {
  return {
    match1: { a: counts["1"] + counts["2"], b: counts["3"] + counts["4"] },
    match2: { a: counts["1"] + counts["3"], b: counts["2"] + counts["4"] },
  };
}
