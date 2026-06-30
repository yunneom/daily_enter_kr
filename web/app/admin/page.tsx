import AppShell from "@/components/AppShell";
import { loadBracket, listMatches, roundLabel } from "@/lib/bracket";
import { tallyMatch } from "@/lib/voteStore";
import { getRoundStates } from "@/lib/adminStore";
import AdminClient from "./AdminClient";

export const dynamic = "force-dynamic";

export default function AdminPage() {
  const b = loadBracket();
  const overrides = getRoundStates();
  const round = b.current_round;
  const matches = listMatches(b, round);

  const tallies = matches.map((m) => ({
    quarter: m.quarter,
    slot: m.slot,
    a: m.a.member,
    bMember: m.b.member,
    tally: tallyMatch(round, m.quarter, m.slot),
  }));

  const stateLabel = overrides[round]?.state ?? "OPEN (derived)";

  return (
    <AppShell title="어드민">
      <div className="card muted">[MVP] 로그인 미구현. ADMIN_KEY 환경변수로 쓰기 보호.</div>

      <div className="card">
        <strong>현재 라운드</strong>
        <p>
          {roundLabel(round)} ({round}) · 상태 {stateLabel}
        </p>
      </div>

      <div className="card">
        <strong>웹 득표 현황</strong>
        {tallies.length === 0 ? (
          <p className="muted">매치 없음</p>
        ) : (
          tallies.map((t) => (
            <p key={`${t.quarter}-${t.slot}`} className="muted">
              {t.a} {t.tally.rawA} : {t.tally.rawB} {t.bMember} (총 {t.tally.total})
            </p>
          ))
        )}
      </div>

      <AdminClient round={round} />
    </AppShell>
  );
}
