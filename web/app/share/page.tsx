import AppShell from "@/components/AppShell";
import { loadBracket, getMatch } from "@/lib/bracket";
import { tallyMatch } from "@/lib/voteStore";
import { isSafeCopy } from "@/lib/safety";
import ShareClient from "./ShareClient";

export const dynamic = "force-dynamic";

interface SearchParams {
  round?: string;
  quarter?: string;
  slot?: string;
}

export default function SharePage({ searchParams }: { searchParams: SearchParams }) {
  const round = searchParams.round ?? "";
  const quarter = Number(searchParams.quarter);
  const slot = Number(searchParams.slot);

  let member = "";
  let group = "";
  let pct = 0;
  let title = "걸그룹 월드컵";

  if (round && !Number.isNaN(quarter) && !Number.isNaN(slot)) {
    try {
      const b = loadBracket();
      const m = getMatch(b, round, quarter, slot);
      if (m) {
        const t = tallyMatch(round, quarter, slot);
        // Lead candidate = higher raw count (ties → A).
        const lead = t.rawB > t.rawA ? m.b : m.a;
        const leadPct = t.rawB > t.rawA ? t.pctB : t.pctA;
        if (isSafeCopy(lead.member) && isSafeCopy(lead.group)) {
          member = lead.member;
          group = lead.group;
          pct = leadPct;
          title = `${lead.member} · ${lead.group}`;
        }
      }
    } catch {
      /* fall back to default safe copy */
    }
  }

  const ogQuery = new URLSearchParams();
  if (member) ogQuery.set("member", member);
  if (group) ogQuery.set("group", group);
  if (pct) ogQuery.set("pct", String(pct));
  const ogUrl = `/api/og${ogQuery.toString() ? `?${ogQuery.toString()}` : ""}`;

  return (
    <AppShell title="공유">
      <div className="card" style={{ textAlign: "center" }}>
        <strong>{title}</strong>
        {pct ? <p className="muted">현재 {pct}% 득표</p> : null}
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="og-preview" src={ogUrl} alt="공유 카드 미리보기" width={1080} height={1080} />
      <ShareClient title={title} />
      <p className="muted" style={{ textAlign: "center" }}>출처 한국기업평판연구소</p>
    </AppShell>
  );
}
