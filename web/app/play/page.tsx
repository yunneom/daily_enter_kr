import { loadRoster } from "@/lib/roster";
import PlayClient from "./PlayClient";

export const dynamic = "force-dynamic";

export default function PlayPage() {
  const roster = loadRoster();
  // Only the pure seed data crosses to the client (no fs).
  return <PlayClient seeds={roster.seeds} tournamentName={roster.tournamentName} />;
}
