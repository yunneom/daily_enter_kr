"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Candidate } from "@/lib/bracketTypes";
import type { SeedMatch, Duel } from "@/lib/tournament";
import {
  nextRoundMatchups,
  roundKeyForSize,
  roundLabelBySize,
} from "@/lib/tournament";
import MemberImage from "@/components/MemberImage";
import { memberImageUrl } from "@/lib/memberImages";
import { getDeviceId } from "@/lib/device";
import {
  loadRun,
  saveRun,
  clearRun,
  runToPicks,
  type StoredRound,
  type StoredRun,
} from "@/lib/runLocal";

interface Props {
  seeds: SeedMatch[];
  tournamentName: string;
}

type Phase = "intro" | "playing" | "champion";

// side picked, used to drive the exit animation before advancing
type Anim = null | { winner: "a" | "b" };

function buildRoundsFromSeeds(seeds: SeedMatch[]): StoredRound[] {
  const duels = seeds
    .slice()
    .sort((x, y) => x.index - y.index)
    .map((s) => ({ a: s.a, b: s.b, winnerRank: null as number | null }));
  return [{ key: roundKeyForSize(32), size: 32, duels }];
}

/** Locate the first undecided duel across rounds → {round, duel} indices. */
function findCursor(rounds: StoredRound[]): { r: number; d: number } | null {
  for (let r = 0; r < rounds.length; r++) {
    for (let d = 0; d < rounds[r].duels.length; d++) {
      if (rounds[r].duels[d].winnerRank == null) return { r, d };
    }
  }
  return null;
}

export default function PlayClient({ seeds }: Props) {
  const [rounds, setRounds] = useState<StoredRound[]>([]);
  const [phase, setPhase] = useState<Phase>("intro");
  const [anim, setAnim] = useState<Anim>(null);
  const [champion, setChampion] = useState<Candidate | null>(null);
  const [counted, setCounted] = useState<null | boolean>(null);
  const [submitting, setSubmitting] = useState(false);

  // Preload ALL 32 candidate photos up front so every duel transition is instant
  // (Commons/gstatic are external + redirect-heavy; warming the browser cache once
  //  removes the per-transition load lag).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const urls = new Set<string>();
    for (const s of seeds) {
      for (const c of [s.a, s.b]) {
        urls.add(memberImageUrl(c.rank) || `/members/${c.rank}.jpg`);
      }
    }
    urls.forEach((u) => {
      const img = new window.Image();
      img.decoding = "async";
      img.src = u;
    });
  }, [seeds]);

  // Resume an in-progress run if present.
  useEffect(() => {
    const saved = loadRun();
    if (saved && saved.rounds.length > 0) {
      setRounds(saved.rounds);
      if (saved.finished && saved.championRank != null) {
        const champ = findCandByRank(saved.rounds, saved.championRank);
        setChampion(champ);
        setPhase("champion");
        setCounted(saved.submitted ? true : null);
      } else {
        setPhase("playing");
      }
    }
  }, []);

  const cursor = useMemo(() => findCursor(rounds), [rounds]);
  const currentRound = cursor ? rounds[cursor.r] : null;
  const currentDuel: Duel | null =
    cursor && currentRound ? currentRound.duels[cursor.d] : null;

  const totalInRound = currentRound?.duels.length ?? 0;
  const decidedInRound = currentRound
    ? currentRound.duels.filter((d) => d.winnerRank != null).length
    : 0;

  const persist = useCallback(
    (nextRounds: StoredRound[], finished: boolean, championRank: number | null, submitted: boolean) => {
      const run: StoredRun = {
        version: 1,
        rounds: nextRounds,
        championRank,
        finished,
        submitted,
        updatedAt: new Date().toISOString(),
      };
      saveRun(run);
    },
    [],
  );

  const start = useCallback(() => {
    const fresh = buildRoundsFromSeeds(seeds);
    setRounds(fresh);
    setChampion(null);
    setCounted(null);
    setPhase("playing");
    persist(fresh, false, null, false);
  }, [seeds, persist]);

  const restart = useCallback(() => {
    clearRun();
    start();
  }, [start]);

  const submit = useCallback(
    async (finalRounds: StoredRound[], championRank: number) => {
      setSubmitting(true);
      try {
        const deviceId = getDeviceId();
        const picks = runToPicks({
          version: 1,
          rounds: finalRounds,
          championRank,
          finished: true,
          submitted: false,
          updatedAt: "",
        });
        const res = await fetch("/api/run", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ deviceId, championRank, picks }),
        });
        const data = (await res.json()) as { counted?: boolean; error?: string };
        const ok = res.ok && data.counted === true;
        setCounted(res.ok ? Boolean(data.counted) : false);
        persist(finalRounds, true, championRank, ok);
      } catch {
        setCounted(false);
        persist(finalRounds, true, championRank, false);
      } finally {
        setSubmitting(false);
      }
    },
    [persist],
  );

  const pick = useCallback(
    (side: "a" | "b") => {
      if (!cursor || !currentRound || !currentDuel || anim) return;
      const c = cursor;
      setAnim({ winner: side });

      // After the exit animation: compute the next state once (deterministically
      // from current `rounds`), set it, then run side effects exactly once.
      window.setTimeout(() => {
        const next = rounds.map((rd) => ({ ...rd, duels: rd.duels.map((d) => ({ ...d })) }));
        const rd = next[c.r];
        const duel = rd.duels[c.d];
        duel.winnerRank = (side === "a" ? duel.a : duel.b).rank;

        let champ: Candidate | null = null;
        const roundComplete = rd.duels.every((d) => d.winnerRank != null);
        if (roundComplete) {
          const winners: Candidate[] = rd.duels.map((d) =>
            d.winnerRank === d.a.rank ? d.a : d.b,
          );
          if (winners.length <= 1) {
            champ = winners[0];
          } else {
            const nextSize = winners.length; // 16,8,4,2
            const duels = nextRoundMatchups(winners).map((m) => ({
              a: m.a,
              b: m.b,
              winnerRank: null as number | null,
            }));
            next.push({ key: roundKeyForSize(nextSize), size: nextSize, duels });
          }
        }

        setRounds(next);
        setAnim(null);

        if (champ) {
          setChampion(champ);
          setPhase("champion");
          persist(next, true, champ.rank, false);
          void submit(next, champ.rank);
        } else {
          persist(next, false, null, false);
        }
      }, 340);
    },
    [cursor, currentRound, currentDuel, anim, rounds, persist, submit],
  );

  // ── render ────────────────────────────────────────────────────────────────

  if (phase === "intro") {
    return (
      <main className="play-root">
        <div className="play-intro">
          <div className="play-intro-badge">이상형 월드컵</div>
          <h1>32강부터 골라서 우승까지</h1>
          <p>둘 중 더 끌리는 쪽을 한 번의 탭으로. 우승자가 나올 때까지 계속됩니다.</p>
          <button className="btn-vs" onClick={start}>
            시작하기
          </button>
          <Link href="/" className="play-back">
            홈으로
          </Link>
        </div>
      </main>
    );
  }

  if (phase === "champion" && champion) {
    return (
      <main className="play-root">
        <div className="champion-screen">
          <div className="champion-label">우승</div>
          <div className="champion-card">
            <MemberImage rank={champion.rank} group={champion.group} member={champion.member} size={320} />
            <div className="champion-name">{champion.member}</div>
            <div className="champion-group">{champion.group}</div>
          </div>
          <p className="champion-counted">
            {counted === true
              ? "집계에 반영되었습니다."
              : counted === false
                ? "이미 참여한 기기입니다. (집계 중복 방지)"
                : submitting
                  ? "집계 반영 중…"
                  : ""}
          </p>
          <div className="champion-actions">
            <button className="btn-vs ghost" onClick={restart}>
              다시하기
            </button>
            <Link href="/bracket" className="btn-vs ghost">
              결과 보기
            </Link>
            <Link href="/results" className="btn-vs">
              전체 순위
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!currentRound || !currentDuel) {
    return (
      <main className="play-root">
        <div className="play-intro">
          <p>불러오는 중…</p>
          <button className="btn-vs" onClick={start}>
            새로 시작
          </button>
        </div>
      </main>
    );
  }

  const size = currentRound.size;
  const label = roundLabelBySize(size);
  const progressPct = totalInRound > 0 ? Math.round((decidedInRound / totalInRound) * 100) : 0;

  return (
    <main className="play-root">
      <div className="play-top">
        <div className="play-round">
          <span className="play-round-label">{label}</span>
          <span className="play-round-count">
            {decidedInRound + 1}/{totalInRound}
          </span>
        </div>
        <div className="progress">
          <div className="progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      <div className="duel">
        <button
          className={`duel-panel a ${anim ? (anim.winner === "a" ? "win" : "lose") : ""}`}
          onClick={() => pick("a")}
          aria-label={`${currentDuel.a.member} 선택`}
        >
          <div className="duel-photo">
            <MemberImage
              rank={currentDuel.a.rank}
              group={currentDuel.a.group}
              member={currentDuel.a.member}
              size={200}
              compact
              eager
            />
          </div>
          <div className="duel-caption">
            <div className="duel-name">{currentDuel.a.member}</div>
            <div className="duel-group">{currentDuel.a.group}</div>
          </div>
        </button>

        <div className="vs-badge" aria-hidden>
          VS
        </div>

        <button
          className={`duel-panel b ${anim ? (anim.winner === "b" ? "win" : "lose") : ""}`}
          onClick={() => pick("b")}
          aria-label={`${currentDuel.b.member} 선택`}
        >
          <div className="duel-photo">
            <MemberImage
              rank={currentDuel.b.rank}
              group={currentDuel.b.group}
              member={currentDuel.b.member}
              size={200}
              compact
              eager
            />
          </div>
          <div className="duel-caption">
            <div className="duel-name">{currentDuel.b.member}</div>
            <div className="duel-group">{currentDuel.b.group}</div>
          </div>
        </button>
      </div>

      <div className="play-foot">
        <Link href="/" className="play-back">
          그만두기
        </Link>
      </div>
    </main>
  );
}

function findCandByRank(rounds: StoredRound[], rank: number): Candidate | null {
  for (const rd of rounds) {
    for (const d of rd.duels) {
      if (d.a.rank === rank) return d.a;
      if (d.b.rank === rank) return d.b;
    }
  }
  return null;
}
