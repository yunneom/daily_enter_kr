import Link from "next/link";
import AppShell from "@/components/AppShell";
import { loadBracket, listMatches, roundLabel } from "@/lib/bracket";

export const dynamic = "force-dynamic";

export default function VoteEntryPage() {
  const b = loadBracket();
  const round = b.current_round;
  const matches = listMatches(b, round);
  const firstOpen = matches.find((m) => m.winner === null) ?? matches[0];

  return (
    <AppShell title={`투표 · ${roundLabel(round)}`}>
      <div className="card">
        <strong>{roundLabel(round)} 진행 중</strong>
        <p className="muted">남은 매치 {matches.filter((m) => m.winner === null).length}개</p>
      </div>

      {firstOpen ? (
        <Link
          href={`/vote/${round}/${firstOpen.quarter}/${firstOpen.slot}`}
          className="btn btn-primary"
        >
          {firstOpen.a.member} vs {firstOpen.b.member} — 투표 시작
        </Link>
      ) : (
        <div className="notice">현재 라운드에 투표할 매치가 없습니다.</div>
      )}

      <Link href="/bracket" className="btn">
        대진표 보기
      </Link>
    </AppShell>
  );
}
