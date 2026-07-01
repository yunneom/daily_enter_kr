"use client";

import { useEffect, useMemo, useState } from "react";
import type { Candidate } from "@/lib/bracketTypes";
import type { SeedMatch } from "@/lib/tournament";
import { groupColor } from "@/lib/colors";
import { loadRun, type StoredRun } from "@/lib/runLocal";

interface Props {
  seeds: SeedMatch[];
}

interface AdvRow {
  rank: number;
  picks: number;
  appears: number;
  pickRate: number;
}

interface Cell {
  a: Candidate;
  b: Candidate;
  winnerRank: number | null;
}

type Mode = "mine" | "all";

// Round sizes present in a full 32-bracket, entering-count.
const SIZES = [32, 16, 8, 4, 2] as const;

function sizeToTabLabel(size: number): string {
  // entering-count → tab label; 2 entering = 결승, 4 entering = 준결승
  if (size === 32) return "32강";
  if (size === 16) return "16강";
  if (size === 8) return "8강";
  if (size === 4) return "준결승";
  if (size === 2) return "결승";
  return `${size}강`;
}

/** Build columns (one per round) of duel cells from seed matches + a winner
 *  resolver. resolver(a,b) → the winning candidate for that duel (or null if
 *  undecided). Later rounds are derived from the winners of earlier rounds. */
function buildColumns(
  seeds: SeedMatch[],
  resolve: (a: Candidate, b: Candidate) => Candidate | null,
): Cell[][] {
  const columns: Cell[][] = [];
  const first: Cell[] = seeds
    .slice()
    .sort((x, y) => x.index - y.index)
    .map((s) => {
      const w = resolve(s.a, s.b);
      return { a: s.a, b: s.b, winnerRank: w ? w.rank : null };
    });
  columns.push(first);

  let prev = first;
  while (prev.length > 1) {
    const winners: (Candidate | null)[] = prev.map((c) =>
      c.winnerRank == null ? null : c.winnerRank === c.a.rank ? c.a : c.b,
    );
    // If any winner missing, we can't reliably seed the next column's pairings
    // beyond names — but we still show placeholders where possible.
    const col: Cell[] = [];
    for (let i = 0; i + 1 < prev.length; i += 2) {
      const a = winners[i];
      const b = winners[i + 1];
      if (a && b) {
        const w = resolve(a, b);
        col.push({ a, b, winnerRank: w ? w.rank : null });
      } else {
        // placeholder cell (unknown entrants yet)
        col.push({
          a: a ?? placeholder(),
          b: b ?? placeholder(),
          winnerRank: null,
        });
      }
    }
    columns.push(col);
    prev = col;
  }
  return columns;
}

function placeholder(): Candidate {
  return { rank: -1, group: "", member: "?" };
}

export default function BracketView({ seeds }: Props) {
  const [mode, setMode] = useState<Mode>("mine");
  const [run, setRun] = useState<StoredRun | null>(null);
  const [adv, setAdv] = useState<Record<number, AdvRow>>({});
  const [tab, setTab] = useState<number>(32);
  const [hasMine, setHasMine] = useState(false);

  useEffect(() => {
    const r = loadRun();
    setRun(r);
    const mine = !!(r && r.rounds.length > 0);
    setHasMine(mine);
    setMode(mine ? "mine" : "all");
  }, []);

  useEffect(() => {
    let alive = true;
    fetch("/api/results")
      .then((res) => res.json())
      .then((d: { advancement?: AdvRow[] }) => {
        if (!alive) return;
        const map: Record<number, AdvRow> = {};
        for (const row of d.advancement ?? []) map[row.rank] = row;
        setAdv(map);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Personal columns: resolve winners from the stored run by looking up which
  // rank the user picked for that exact (a,b) pair.
  const mineWinnerLookup = useMemo(() => {
    const map = new Map<string, number>();
    if (run) {
      for (const rd of run.rounds) {
        for (const d of rd.duels) {
          if (d.winnerRank != null) map.set(pairKey(d.a.rank, d.b.rank), d.winnerRank);
        }
      }
    }
    return map;
  }, [run]);

  const columns = useMemo(() => {
    if (mode === "mine" && hasMine) {
      return buildColumns(seeds, (a, b) => {
        const w = mineWinnerLookup.get(pairKey(a.rank, b.rank));
        if (w == null) return null;
        return w === a.rank ? a : b;
      });
    }
    // aggregate consensus: winner = higher aggregate pickRate (tie → picks → seed)
    return buildColumns(seeds, (a, b) => {
      const ra = adv[a.rank];
      const rb = adv[b.rank];
      const sa = ra?.picks ?? 0;
      const sb = rb?.picks ?? 0;
      const pa = ra?.pickRate ?? 0;
      const pb = rb?.pickRate ?? 0;
      if (sa === 0 && sb === 0) return null; // no data yet → undecided (seed names only)
      if (pa !== pb) return pa > pb ? a : b;
      if (sa !== sb) return sa > sb ? a : b;
      return a.rank <= b.rank ? a : b;
    });
  }, [mode, hasMine, seeds, mineWinnerLookup, adv]);

  const activeColIndex = SIZES.indexOf(tab as (typeof SIZES)[number]);

  return (
    <div className="bracket-wrap">
      <div className="bracket-controls">
        <div className="seg">
          <button
            className={`seg-btn ${mode === "mine" ? "on" : ""}`}
            onClick={() => setMode("mine")}
            disabled={!hasMine}
          >
            내 결과
          </button>
          <button
            className={`seg-btn ${mode === "all" ? "on" : ""}`}
            onClick={() => setMode("all")}
          >
            전체 집계
          </button>
        </div>
        {!hasMine && mode === "mine" ? null : null}
      </div>

      <div className="round-tabs">
        {SIZES.map((s) => (
          <button
            key={s}
            className={`round-tab ${tab === s ? "active" : ""}`}
            onClick={() => setTab(s)}
          >
            {sizeToTabLabel(s)}
          </button>
        ))}
      </div>

      {mode === "mine" && !hasMine ? (
        <div className="bracket-empty">아직 플레이한 기록이 없습니다. 홈에서 월드컵을 시작해보세요.</div>
      ) : null}

      <div className="bracket-scroll">
        <div className="bracket-tree">
          {columns.map((col, ci) => {
            const size = SIZES[ci] ?? col.length * 2;
            const focused = ci === activeColIndex;
            return (
              <div
                key={ci}
                className={`bracket-col ${focused ? "focus" : ""}`}
                data-round={size}
              >
                <div className="bracket-col-head">{sizeToTabLabel(size)}</div>
                <div className="bracket-col-body">
                  {col.map((cell, mi) => (
                    <BracketCell key={mi} cell={cell} />
                  ))}
                </div>
              </div>
            );
          })}
          {/* champion column */}
          <ChampionCol columns={columns} />
        </div>
      </div>
    </div>
  );
}

function ChampionCol({ columns }: { columns: Cell[][] }) {
  const finalCol = columns[columns.length - 1];
  const final = finalCol?.[0];
  const champ =
    final && final.winnerRank != null
      ? final.winnerRank === final.a.rank
        ? final.a
        : final.b
      : null;
  return (
    <div className="bracket-col champion-col">
      <div className="bracket-col-head">우승</div>
      <div className="bracket-col-body">
        {champ ? (
          <div className="bracket-cell champ" style={{ borderColor: groupColor(champ.group) }}>
            <span className="cell-crown">우승</span>
            <span className="cell-name">{champ.member}</span>
            <span className="cell-group" style={{ color: groupColor(champ.group) }}>
              {champ.group}
            </span>
          </div>
        ) : (
          <div className="bracket-cell empty">
            <span className="cell-name muted">?</span>
          </div>
        )}
      </div>
    </div>
  );
}

function BracketCell({ cell }: { cell: Cell }) {
  const aWin = cell.winnerRank != null && cell.winnerRank === cell.a.rank;
  const bWin = cell.winnerRank != null && cell.winnerRank === cell.b.rank;
  return (
    <div className="bracket-cell">
      <div className={`cell-side ${aWin ? "win" : cell.winnerRank != null ? "lose" : ""}`}>
        <span className="cell-dot" style={{ background: groupColor(cell.a.group) }} />
        <span className="cell-name">{cell.a.member}</span>
        <span className="cell-group">{cell.a.group}</span>
      </div>
      <div className={`cell-side ${bWin ? "win" : cell.winnerRank != null ? "lose" : ""}`}>
        <span className="cell-dot" style={{ background: groupColor(cell.b.group) }} />
        <span className="cell-name">{cell.b.member}</span>
        <span className="cell-group">{cell.b.group}</span>
      </div>
    </div>
  );
}

function pairKey(x: number, y: number): string {
  return x < y ? `${x}:${y}` : `${y}:${x}`;
}
