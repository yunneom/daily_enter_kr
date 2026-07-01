/**
 * SERVER-ONLY roster builder. Uses the fs-backed bracket loader, so DO NOT
 * import this from a client component — import the pure helpers/types from
 * lib/tournament instead and receive the built roster as serialized props.
 */

import { loadBracket } from "./bracket";
import type { Candidate } from "./bracketTypes";
import type { Roster, SeedMatch } from "./tournament";

function stripScore(c: Candidate): Candidate {
  return { rank: c.rank, group: c.group, member: c.member };
}

/**
 * Build the fixed roster from the R32 seed matches. Ignores any stored winners
 * (the web run is fresh). Order = seed match order, a then b per match.
 */
export function loadRoster(): Roster {
  const b = loadBracket();
  const r32 = b.rounds?.R32?.matches ?? [];
  const seeds: SeedMatch[] = [];
  const candidates: Candidate[] = [];
  const byRank: Record<number, Candidate> = {};

  r32.forEach((m, index) => {
    const a = stripScore(m.a);
    const bb = stripScore(m.b);
    seeds.push({ index, a, b: bb });
    candidates.push(a, bb);
    byRank[a.rank] = a;
    byRank[bb.rank] = bb;
  });

  return {
    candidates,
    seeds,
    byRank,
    tournamentName: b.tournament ?? "이상형 월드컵",
    source: b.source ?? "",
  };
}
