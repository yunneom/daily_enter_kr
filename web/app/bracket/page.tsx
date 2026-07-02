import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import { loadRoster } from "@/lib/roster";
import BracketView from "./BracketView";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "대진표 — 걸그룹 이상형 월드컵",
  description: "32강부터 결승까지 전체 대진표. 내 결과와 전체 참여자 집계를 한눈에 봅니다.",
  alternates: { canonical: "/bracket" },
};

export default function BracketPage() {
  const roster = loadRoster();
  return (
    <AppShell title="대진표" wide>
      <BracketView seeds={roster.seeds} />
      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_BRACKET} />
    </AppShell>
  );
}
