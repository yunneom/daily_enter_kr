import AppShell from "@/components/AppShell";
import ResultsClient from "./ResultsClient";

export const dynamic = "force-dynamic";

export default function ResultsPage() {
  return (
    <AppShell title="결과">
      <ResultsClient />
    </AppShell>
  );
}
