import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import ResultsClient from "./ResultsClient";

export const dynamic = "force-dynamic";

export default function ResultsPage() {
  return (
    <AppShell title="결과">
      <ResultsClient />
      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_RESULTS} />
    </AppShell>
  );
}
