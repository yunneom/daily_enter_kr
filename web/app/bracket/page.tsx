import AppShell from "@/components/AppShell";
import { loadBracket, ROUND_ORDER } from "@/lib/bracket";
import BracketView from "./BracketView";

export const dynamic = "force-dynamic";

export default function BracketPage() {
  const b = loadBracket();
  const availableRounds = ROUND_ORDER.filter((r) => b.rounds[r] || (r === "R1" && b.winner));
  return (
    <AppShell title="대진표">
      <BracketView
        rounds={b.rounds}
        order={availableRounds}
        currentRound={b.current_round}
        winner={b.winner}
      />
    </AppShell>
  );
}
