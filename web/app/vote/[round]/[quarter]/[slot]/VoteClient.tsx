"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { Match } from "@/lib/bracketTypes";
import { getDeviceId, getVotedKeys, addVotedKey } from "@/lib/device";

type MatchStatus = "OPEN" | "LOCKED" | "DECIDED";
interface MatchTally {
  rawA: number;
  rawB: number;
  total: number;
  pctA: number;
  pctB: number;
}

interface Props {
  round: string;
  quarter: number;
  slot: number;
  match: Match;
  initialTally: MatchTally;
  initialStatus: MatchStatus;
}

type View = "vote" | "result" | "duplicate" | "locked";

// [가정] polling MVP — refresh tally every 4s while on the result view.
const POLL_MS = 4000;

export default function VoteClient({
  round,
  quarter,
  slot,
  match,
  initialTally,
  initialStatus,
}: Props) {
  const [tally, setTally] = useState<MatchTally>(initialTally);
  const [view, setView] = useState<View>(
    initialStatus === "LOCKED" ? "locked" : initialStatus === "DECIDED" ? "result" : "vote",
  );
  const [busy, setBusy] = useState(false);
  const [nextHref, setNextHref] = useState<string | null>(null);

  // If this device already voted (recorded locally), jump straight to results.
  useEffect(() => {
    if (initialStatus === "OPEN" && getVotedKeys(round).has(`${quarter}-${slot}`)) {
      setView("result");
    }
  }, [initialStatus, round, quarter, slot]);

  const refreshTally = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/match?round=${encodeURIComponent(round)}&quarter=${quarter}&slot=${slot}`,
        { cache: "no-store" },
      );
      if (res.ok) {
        const data = (await res.json()) as { tally: MatchTally };
        setTally(data.tally);
      }
    } catch {
      /* ignore poll errors */
    }
  }, [round, quarter, slot]);

  // Poll while viewing results.
  useEffect(() => {
    if (view !== "result") return;
    const id = setInterval(refreshTally, POLL_MS);
    return () => clearInterval(id);
  }, [view, refreshTally]);

  // Compute next match recommendation from full bracket + local voted keys.
  const computeNext = useCallback(async () => {
    try {
      const res = await fetch("/api/bracket", { cache: "no-store" });
      if (!res.ok) return;
      const b = (await res.json()) as {
        rounds: Record<string, { matches: Match[] }>;
      };
      const matches = (b.rounds[round]?.matches ?? []).filter((m) => m.winner === null);
      const voted = getVotedKeys(round);
      const isOpen = (m: Match) => !voted.has(`${m.quarter}-${m.slot}`);
      // 1. same quarter adjacent slot
      const adjacentSlot = slot % 2 === 0 ? slot + 1 : slot - 1;
      const adj = matches.find((m) => m.quarter === quarter && m.slot === adjacentSlot && isOpen(m));
      const ordered = [...matches].sort((a, c) =>
        a.quarter !== c.quarter ? a.quarter - c.quarter : a.slot - c.slot,
      );
      const target = adj ?? ordered.find(isOpen);
      setNextHref(target ? `/vote/${round}/${target.quarter}/${target.slot}` : null);
    } catch {
      setNextHref(null);
    }
  }, [round, quarter, slot]);

  useEffect(() => {
    if (view === "result") void computeNext();
  }, [view, computeNext]);

  async function vote(pick: "a" | "b") {
    if (busy) return;
    setBusy(true);
    try {
      const deviceId = getDeviceId();
      const res = await fetch("/api/vote", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ round, quarter, slot, pick, deviceId }),
      });
      if (res.status === 409) {
        setView("duplicate");
        await refreshTally();
        return;
      }
      if (res.status === 423) {
        setView("locked");
        return;
      }
      if (res.ok) {
        const data = (await res.json()) as { tally: MatchTally };
        setTally(data.tally);
        addVotedKey(round, quarter, slot);
        setView("result");
        return;
      }
    } catch {
      /* network error — stay on vote view */
    } finally {
      setBusy(false);
    }
  }

  const shareHref = `/share?round=${round}&quarter=${quarter}&slot=${slot}`;

  if (view === "locked") {
    return (
      <div className="notice">
        <p>이 라운드는 마감되었습니다.</p>
        <Link href="/bracket" className="btn">
          대진표에서 결과 보기
        </Link>
      </div>
    );
  }

  if (view === "vote") {
    return (
      <div className="vs-wrap">
        <Candidate label="이 팀 선택" name={match.a.member} group={match.a.group} onPick={() => vote("a")} disabled={busy} />
        <div className="vs-divider">VS</div>
        <Candidate label="이 팀 선택" name={match.b.member} group={match.b.group} onPick={() => vote("b")} disabled={busy} />
      </div>
    );
  }

  // result or duplicate
  return (
    <div>
      {view === "duplicate" ? (
        <div className="card muted">이미 이 경기에 투표하셨습니다. 현재 결과를 보여드립니다.</div>
      ) : null}

      <ResultBar name={match.a.member} group={match.a.group} pct={tally.pctA} count={tally.rawA} />
      <ResultBar name={match.b.member} group={match.b.group} pct={tally.pctB} count={tally.rawB} />
      <p className="muted" style={{ textAlign: "center" }}>총 {tally.total}표</p>

      {nextHref ? (
        <Link href={nextHref} className="btn btn-primary">
          다음 매치로
        </Link>
      ) : (
        <Link href="/bracket" className="btn btn-primary">
          대진표 보기
        </Link>
      )}
      <Link href={shareHref} className="btn">
        결과 공유하기
      </Link>
    </div>
  );
}

function Candidate({
  label,
  name,
  group,
  onPick,
  disabled,
}: {
  label: string;
  name: string;
  group: string;
  onPick: () => void;
  disabled: boolean;
}) {
  return (
    <div className="candidate">
      <div className="placeholder">이미지 준비중</div>
      <div className="group">{group}</div>
      <div className="member">{name}</div>
      <button className="btn btn-primary" onClick={onPick} disabled={disabled}>
        {label}
      </button>
    </div>
  );
}

function ResultBar({
  name,
  group,
  pct,
  count,
}: {
  name: string;
  group: string;
  pct: number;
  count: number;
}) {
  return (
    <div>
      <div className="muted">
        {group} · {name}
      </div>
      <div className="bar">
        <div className="fill" style={{ width: `${pct}%` }} />
        <div className="label">
          <span>{name}</span>
          <span>
            {pct}% ({count}표)
          </span>
        </div>
      </div>
    </div>
  );
}
