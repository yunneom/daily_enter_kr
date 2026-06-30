"use client";

import { useState } from "react";
import Link from "next/link";
import type { Candidate, Match, Round, RoundKey } from "@/lib/bracketTypes";
import { roundLabel } from "@/lib/bracketTypes";

interface Props {
  rounds: Record<string, Round>;
  order: RoundKey[];
  currentRound: string;
  winner: Candidate | null;
}

function sameCandidate(a: Candidate | null, b: Candidate): boolean {
  if (!a) return false;
  return a.member === b.member && a.group === b.group && a.rank === b.rank;
}

function typeLabel(m: Match): string | null {
  if (m.type === "final") return "결승";
  if (m.type === "third_place") return "3·4위전";
  return null;
}

export default function BracketView({ rounds, order, currentRound, winner }: Props) {
  const defaultTab = (order.includes(currentRound as RoundKey)
    ? currentRound
    : order[order.length - 1]) as RoundKey;
  const [tab, setTab] = useState<RoundKey>(defaultTab ?? "R32");

  const round = rounds[tab];

  return (
    <div>
      <div className="tabs">
        {order.map((r) => (
          <button
            key={r}
            className={`tab ${r === tab ? "active" : ""}`}
            onClick={() => setTab(r)}
          >
            {roundLabel(r)}
          </button>
        ))}
      </div>

      {tab === "R1" || (round && round.matches.length === 0) ? (
        <div className="card" style={{ textAlign: "center" }}>
          <strong>우승</strong>
          {winner ? (
            <p style={{ fontSize: 22, fontWeight: 700, margin: "8px 0" }}>
              {winner.member} · {winner.group}
            </p>
          ) : (
            <p className="muted">아직 우승자가 결정되지 않았습니다.</p>
          )}
        </div>
      ) : round ? (
        round.matches.map((m) => {
          const aWin = sameCandidate(m.winner, m.a);
          const bWin = sameCandidate(m.winner, m.b);
          const tl = typeLabel(m);
          return (
            <Link
              key={`${m.quarter}-${m.slot}`}
              href={`/vote/${tab}/${m.quarter}/${m.slot}`}
              className="match-row"
            >
              <div className={`side ${aWin ? "win" : ""}`}>
                {m.a.member}
                {aWin ? <span className="badge">승</span> : null}
                {m.votes ? <span className="muted"> {m.votes.raw_a}</span> : null}
              </div>
              <div className="muted" style={{ padding: "0 8px" }}>
                {tl ?? "vs"}
              </div>
              <div className={`side ${bWin ? "win" : ""}`} style={{ textAlign: "right" }}>
                {m.votes ? <span className="muted">{m.votes.raw_b} </span> : null}
                {bWin ? <span className="badge">승</span> : null}
                {m.b.member}
              </div>
            </Link>
          );
        })
      ) : (
        <div className="notice">해당 라운드 데이터가 없습니다.</div>
      )}
    </div>
  );
}
