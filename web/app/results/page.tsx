import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import ResultsClient from "./ResultsClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "실시간 결과 — 걸그룹 이상형 월드컵",
  description: "전체 참여자가 뽑은 우승 랭킹과 진출률을 실시간으로 집계해 보여줍니다.",
  alternates: { canonical: "/results" },
};

export default function ResultsPage() {
  return (
    <AppShell title="결과">
      <ResultsClient />
      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_RESULTS} />
    </AppShell>
  );
}
