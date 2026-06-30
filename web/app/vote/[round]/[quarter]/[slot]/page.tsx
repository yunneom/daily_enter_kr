import AppShell from "@/components/AppShell";
import { loadBracket, getMatch, roundLabel } from "@/lib/bracket";
import { tallyMatch } from "@/lib/voteStore";
import { matchStatus } from "@/lib/status";
import VoteClient from "./VoteClient";

export const dynamic = "force-dynamic";

export default function VoteMatchPage({
  params,
}: {
  params: { round: string; quarter: string; slot: string };
}) {
  const round = params.round;
  const quarter = Number(params.quarter);
  const slot = Number(params.slot);

  const b = loadBracket();
  const match = getMatch(b, round, quarter, slot);

  if (!match || Number.isNaN(quarter) || Number.isNaN(slot)) {
    return (
      <AppShell title="투표">
        <div className="notice">매치를 찾을 수 없습니다.</div>
      </AppShell>
    );
  }

  const tally = tallyMatch(round, quarter, slot);
  const status = matchStatus(b, round, match);

  return (
    <AppShell title={`투표 · ${roundLabel(round)}`}>
      <VoteClient
        round={round}
        quarter={quarter}
        slot={slot}
        match={match}
        initialTally={tally}
        initialStatus={status}
      />
    </AppShell>
  );
}
