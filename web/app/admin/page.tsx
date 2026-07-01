import AppShell from "@/components/AppShell";
import { getResults } from "@/lib/runStore";
import { groupColor } from "@/lib/colors";
import AdminClient from "./AdminClient";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// This page is only reachable when the middleware has already verified the
// wc_admin cookie, so no gameplay-side auth check is needed here.
export default async function AdminPage() {
  let runsTotal = 0;
  let champions: { rank: number; group: string; member: string; count: number; pct: number }[] = [];
  let error = "";
  try {
    const r = await getResults();
    runsTotal = r.runsTotal;
    champions = r.champions;
  } catch (e) {
    error = String(e);
  }

  const withCounts = champions.filter((c) => c.count > 0);

  return (
    <AppShell title="어드민">
      <div className="card">
        <strong>집계 요약</strong>
        <p className="admin-total">
          총 참여 <b>{runsTotal.toLocaleString()}</b>회
        </p>
        {error ? <p className="muted">집계 로드 오류: {error}</p> : null}
      </div>

      <div className="card">
        <strong>우승 현황</strong>
        {withCounts.length === 0 ? (
          <p className="muted">아직 집계된 우승자가 없습니다.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>#</th>
                <th>멤버</th>
                <th>우승</th>
                <th>%</th>
              </tr>
            </thead>
            <tbody>
              {withCounts.map((c, i) => (
                <tr key={c.rank}>
                  <td>{i + 1}</td>
                  <td>
                    <span className="lb-dot sm" style={{ background: groupColor(c.group) }} />
                    {c.member} <span className="lb-group">{c.group}</span>
                  </td>
                  <td>{c.count}</td>
                  <td>{c.pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AdminClient />
    </AppShell>
  );
}
