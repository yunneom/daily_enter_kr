import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import MemberImage from "@/components/MemberImage";
import { getResults, type AdvancementRow, type ChampionRow } from "@/lib/runStore";
import { groupColor } from "@/lib/colors";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TITLE = "우승 리캡 — 걸그룹 이상형 월드컵";
const DESC =
  "전체 참여자가 뽑은 걸그룹 이상형 월드컵 우승 리캡. 현재 1위와 TOP 5, 라운드별 진출률 흐름을 정리했습니다.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/recap" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "website",
    locale: "ko_KR",
    url: "/recap",
    images: ["/api/og?mode=recap"],
  },
};

/**
 * Aggregate-data editorial recap. Plain factual tone — numbers only, no
 * clickbait vocabulary, no emoji (brand safety mirrors lib/safety.ts).
 */
function buildRecapParagraphs(
  runsTotal: number,
  champions: ChampionRow[],
  advancement: AdvancementRow[],
): string[] {
  const paras: string[] = [];
  const ranked = champions.filter((c) => c.count > 0);

  if (runsTotal > 0 && ranked.length > 0) {
    const first = ranked[0];
    let p = `지금까지 총 ${runsTotal.toLocaleString()}회의 완주가 집계되었습니다. 현재 1위는 ${first.group} ${first.member}로, 전체 참여자의 ${first.pct}%가 우승 픽으로 선택했습니다.`;
    if (ranked.length > 1) {
      const second = ranked[1];
      const gap = Math.round((first.pct - second.pct) * 10) / 10;
      p += ` 2위 ${second.group} ${second.member}(${second.pct}%)와의 격차는 ${gap}%포인트입니다.`;
    }
    paras.push(p);
  }

  // pickRate 상위 언급 — 실제로 여러 번 등장한 멤버만.
  const adv = advancement.filter((a) => a.appears >= 2 && a.picks > 0);
  if (adv.length >= 3) {
    const [a, b, c] = adv;
    paras.push(
      `라운드 진출률 기준으로는 ${a.group} ${a.member}가 ${a.pickRate}%로 가장 높았고, ${b.member}(${b.pickRate}%)와 ${c.member}(${c.pickRate}%)가 뒤를 이었습니다. 진출률은 맞대결 화면에 등장했을 때 선택받은 비율로, 우승 횟수와는 조금 다른 흐름을 보여줍니다.`,
    );
  }

  // 박빙 구도 — 선택이 절반 근처에서 갈린 멤버들.
  const close = adv.filter((a) => a.pickRate >= 45 && a.pickRate <= 55).slice(0, 3);
  if (close.length >= 2) {
    paras.push(
      `${close.map((c) => c.member).join(", ")}은 선택 비율이 절반에 가까워 참여자마다 판단이 갈리는 박빙 구도였습니다. 참여가 이어지면 순위는 계속 바뀔 수 있습니다.`,
    );
  }

  return paras;
}

export default async function RecapPage() {
  let runsTotal = 0;
  let champions: ChampionRow[] = [];
  let advancement: AdvancementRow[] = [];
  try {
    const r = await getResults();
    runsTotal = r.runsTotal;
    champions = r.champions;
    advancement = r.advancement;
  } catch {
    /* store unreachable — render the evergreen shell */
  }

  const ranked = champions.filter((c) => c.count > 0);
  const leader = ranked[0] ?? null;
  const top5 = ranked.slice(0, 5);
  const paragraphs = buildRecapParagraphs(runsTotal, champions, advancement);

  return (
    <AppShell title="우승 리캡">
      <div className="recap-wrap">
        {/* (a) 현재 1위 */}
        <section className="recap-hero">
          <div className="recap-kicker">전체 참여자 집계 기준</div>
          {leader ? (
            <div className="recap-champ-card" style={{ borderColor: groupColor(leader.group) }}>
              <div className="recap-champ-photo">
                <MemberImage
                  rank={leader.rank}
                  group={leader.group}
                  member={leader.member}
                  size={280}
                />
              </div>
              <div className="recap-champ-label">현재 1위</div>
              <div className="recap-champ-name">{leader.member}</div>
              <div className="recap-champ-group">{leader.group}</div>
              <div className="recap-champ-pct" style={{ color: groupColor(leader.group) }}>
                우승 픽 {leader.pct}%
              </div>
            </div>
          ) : (
            <div className="bracket-empty">
              아직 집계된 우승 기록이 없습니다. 첫 참여자가 되어보세요.
            </div>
          )}
        </section>

        {/* (b) TOP 5 */}
        {top5.length > 0 ? (
          <section>
            <h2 className="section-title">우승 픽 TOP 5</h2>
            <table className="adv-table">
              <thead>
                <tr>
                  <th>순위</th>
                  <th>멤버</th>
                  <th>우승</th>
                  <th>비율</th>
                </tr>
              </thead>
              <tbody>
                {top5.map((c, i) => (
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
          </section>
        ) : null}

        {/* (c) 라운드 리캡 */}
        {paragraphs.length > 0 ? (
          <section>
            <h2 className="section-title">라운드 리캡</h2>
            <div className="recap-editorial">
              {paragraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </section>
        ) : null}

        {/* (d) CTA */}
        <section className="recap-cta">
          <Link href="/play" className="btn-vs">
            직접 플레이하기
          </Link>
          <Link href="/results" className="recap-sub-link">
            실시간 전체 결과 보기
          </Link>
        </section>

        {/* (e) 참여 방법 / 규칙 — evergreen */}
        <section>
          <h2 className="section-title">참여 방법과 집계 규칙</h2>
          <div className="recap-editorial">
            <p>
              걸그룹 이상형 월드컵은 32강 토너먼트 형식으로 진행됩니다. 화면에 나오는 두 명의 후보
              중 더 마음이 가는 쪽을 선택하면 다음 라운드로 진출하고, 16강과 8강, 4강, 결승을 거쳐
              한 명의 우승자가 정해집니다. 완주한 결과는 기기당 1회만 전체 집계에 반영되어 중복
              참여가 순위를 왜곡하지 않도록 관리됩니다. 우승 랭킹과 라운드 진출률은 결과 페이지에서
              실시간으로 확인할 수 있으며, 참가 명단은 한국기업평판연구소의 걸그룹 개인 브랜드평판
              순위를 기준으로 구성했습니다.
            </p>
          </div>
        </section>

        <p className="muted src-line">출처 한국기업평판연구소</p>
      </div>

      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_RESULTS} />
    </AppShell>
  );
}
