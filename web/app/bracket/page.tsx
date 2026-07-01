import AppShell from "@/components/AppShell";
import { loadRoster } from "@/lib/roster";
import BracketView from "./BracketView";

export const dynamic = "force-dynamic";

export default function BracketPage() {
  const roster = loadRoster();
  return (
    <AppShell title="대진표" wide>
      <BracketView seeds={roster.seeds} />
    </AppShell>
  );
}
