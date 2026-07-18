import type { Metadata } from "next";
import { loadRoster } from "@/lib/roster";
import PlayClient from "./PlayClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "이상형 월드컵 플레이 — 걸그룹 이상형 월드컵",
  description: "32강부터 결승까지 1:1 대결로 직접 완주하는 걸그룹 이상형 월드컵. 지금 바로 최애를 골라보세요.",
  alternates: { canonical: "/play" },
};

export default function PlayPage() {
  const roster = loadRoster();
  // Only the pure seed data crosses to the client (no fs).
  return <PlayClient seeds={roster.seeds} tournamentName={roster.tournamentName} />;
}
