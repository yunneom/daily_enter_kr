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
import MomentBanner from "@/components/MomentBanner";
import ShareCard from "@/components/ShareCard";
import { memberImageUrl } from "@/lib/memberImages";
import { groupColor } from "@/lib/colors";
import { getDeviceId } from "@/lib/device";
import { getUtmSource } from "@/lib/utm";
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

type Phase = "intro" | "already" | "playing" | "champion";

interface LiveResults {
  runsTotal: number;
  champions: { rank: number; group: string; member: string; count: number; pct: number }[];
}

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
  const [live, setLive] = useState<LiveResults | null>(null);
  const [shareOpen, setShareOpen] = useState(false);

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
  //
  // Re-participation gate (best-effort): a device that has a finished AND
  // server-submitted run lands on an "already participated" screen instead of a
  // fresh start. NOTE: full prevention requires login — localStorage/cookies can
  // be cleared, so this is best-effort only. Server-side dedup (per deviceId)
  // remains the real aggregate protection.
  useEffect(() => {
    const saved = loadRun();
    if (saved && saved.rounds.length > 0) {
      setRounds(saved.rounds);
      if (saved.finished && saved.championRank != null) {
        const champ = findCandByRank(saved.rounds, saved.championRank);
        setChampion(champ);
        setCounted(saved.submitted ? true : null);
        setPhase(saved.submitted ? "already" : "champion");
      } else {
        setPhase("playing");
      }
    }
  }, []);

  // Live TOP 3 for the champion / already screens. Fetch on entry, light 8s refresh.
  // Paused while the tab is hidden; refreshes immediately on return.
  useEffect(() => {
    if (phase !== "champion" && phase !== "already") return;
    let alive = true;
    const load = (force = false) => {
      if (!force && document.hidden) return;
      fetch("/api/results")
        .then((r) => r.json())
        .then((d: LiveResults) => {
          if (alive) setLive(d);
        })
        .catch(() => {});
    };
    load(true);
    const id = window.setInterval(() => load(), 8000);
    const onVisibility = () => {
      if (!document.hidden) load(true);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      alive = false;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [phase]);

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

  // Show the user's own saved champion screen (from the "already" gate).
  const viewOwnResult = useCallback(() => {
    setPhase("champion");
  }, []);

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
        const utm = getUtmSource();
        const res = await fetch("/api/run", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ deviceId, championRank, picks, ...(utm ? { utm } : {}) }),
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

  const liveTop3 = live?.champions.filter((c) => c.count > 0).slice(0, 3) ?? [];
  const miniLeaderboard =
    live && liveTop3.length > 0 ? (
      <div className="mini-lb">
        <div className="mini-lb-head">
          <span className="live-badge">
            <span className="live-dot" aria-hidden />
            LIVE · 실시간 집계
          </span>
          <span className="mini-lb-total">누적 참여 {live.runsTotal.toLocaleString()}회</span>
        </div>
        <ol className="mini-lb-list">
          {liveTop3.map((c, i) => (
            <li key={c.rank} className="mini-lb-row">
              <span className="mini-lb-rank">{i + 1}</span>
              <span className="mini-lb-dot" style={{ background: groupColor(c.group) }} />
              <span className="mini-lb-name">{c.member}</span>
              <span className="mini-lb-pct">{c.pct}%</span>
            </li>
          ))}
        </ol>
      </div>
    ) : null;

  if (phase === "already") {
    return (
      <main className="play-root">
        <div className="play-intro">
          <div className="play-intro-badge">참여 완료</div>
          <h1>이미 참여 완료</h1>
          <p>이미 이 월드컵에 참여하셨습니다. 결과는 실시간으로 집계됩니다.</p>
          {miniLeaderboard}
          <Link href="/results" className="btn-vs">
            실시간 결과 보기
          </Link>
          <div className="already-secondary">
            <button className="already-link" onClick={viewOwnResult}>
              내 결과 다시 보기
            </button>
            <button className="already-link" onClick={restart}>
              다시 둘러보기 (집계 반영 안 됨)
            </button>
          </div>
          <Link href="/" className="play-back">
            홈으로
          </Link>
        </div>
      </main>
    );
  }

  if (phase === "intro") {
    return (
      <main className="play-root">
        <MomentBanner />
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
    const liveChampRow = live?.champions.find((c) => c.rank === champion.rank && c.count > 0);
    const championPct = liveChampRow ? liveChampRow.pct : null;
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
          {miniLeaderboard}
          <div className="champion-actions">
            <button className="btn-vs" onClick={() => setShareOpen(true)}>
              공유 카드 만들기
            </button>
            <Link href="/results" className="btn-vs ghost">
              실시간 전체 결과
            </Link>
            <Link href="/bracket" className="btn-vs ghost">
              대진표 보기
            </Link>
            <button className="btn-vs ghost" onClick={restart}>
              다시 플레이 (집계 반영 안 됨)
            </button>
          </div>
        </div>
        {shareOpen ? (
          <ShareCard
            rank={champion.rank}
            group={champion.group}
            member={champion.member}
            pct={championPct}
            onClose={() => setShareOpen(false)}
          />
        ) : null}
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
