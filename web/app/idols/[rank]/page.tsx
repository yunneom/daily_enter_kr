import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import MemberImage from "@/components/MemberImage";
import { groupColor, groupGradient } from "@/lib/colors";
import {
  allMembers,
  memberByRank,
  membersOfGroup,
  formatBirth,
} from "@/lib/idolContent";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const dynamicParams = false;

export function generateStaticParams() {
  return allMembers().map((m) => ({ rank: String(m.rank) }));
}

function parseRank(param: string): number {
  const n = Number.parseInt(param, 10);
  return Number.isFinite(n) ? n : -1;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ rank: string }>;
}): Promise<Metadata> {
  const { rank } = await params;
  const m = memberByRank(parseRank(rank));
  if (!m) return { title: "프로필 — 걸그룹 이상형 월드컵" };
  const title = `${m.group} ${m.member} — 걸그룹 이상형 월드컵 프로필`;
  const desc = `${m.group} ${m.member} 프로필과 이상형 월드컵 참가 정보. ${m.tagline}`;
  const url = `/idols/${m.rank}`;
  return {
    title,
    description: desc,
    alternates: { canonical: url },
    openGraph: {
      title,
      description: desc,
      type: "profile",
      locale: "ko_KR",
      url,
      images: ["/api/og"],
    },
  };
}

export default async function IdolProfilePage({
  params,
}: {
  params: Promise<{ rank: string }>;
}) {
  const { rank } = await params;
  const m = memberByRank(parseRank(rank));
  if (!m) notFound();

  const color = groupColor(m.group);
  const birth = formatBirth(m.birth);
  const groupmates = membersOfGroup(m.groupSlug).filter((x) => x.rank !== m.rank);

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "프로필", item: `${SITE_URL}/idols` },
      {
        "@type": "ListItem",
        position: 3,
        name: `${m.group} ${m.member}`,
        item: `${SITE_URL}/idols/${m.rank}`,
      },
    ],
  };

  return (
    <AppShell title="멤버 프로필">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb) }}
      />

      <article className="prof">
        <header
          className="prof-hero"
          style={{ background: groupGradient(m.group) }}
        >
          <div className="prof-photo">
            <MemberImage rank={m.rank} group={m.group} member={m.member} size={120} rounded eager />
          </div>
          <div className="prof-head">
            <Link href={`/groups/${m.groupSlug}`} className="prof-group">
              {m.group}
            </Link>
            <h1 className="prof-name">{m.member}</h1>
            <p className="prof-tag">{m.tagline}</p>
          </div>
        </header>

        <dl className="prof-meta">
          <div>
            <dt>그룹</dt>
            <dd>
              <Link href={`/groups/${m.groupSlug}`} style={{ color }}>
                {m.group}
              </Link>
            </dd>
          </div>
          <div>
            <dt>브랜드평판 순위</dt>
            <dd>{m.rank}위 (2026년 6월 · 한국기업평판연구소)</dd>
          </div>
          {birth ? (
            <div>
              <dt>생일</dt>
              <dd>{birth}</dd>
            </div>
          ) : null}
        </dl>

        <section className="prof-intro">
          {m.intro.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </section>

        <div className="prof-links">
          <Link href="/play" className="btn-vs">
            이상형 월드컵에서 투표하기
          </Link>
          <Link href={`/groups/${m.groupSlug}`} className="prof-link-secondary">
            {m.group} 소개 보기
          </Link>
        </div>

        {groupmates.length > 0 ? (
          <section>
            <h2 className="section-title">같은 그룹 멤버</h2>
            <div className="roster-grid">
              {groupmates.map((g) => (
                <Link
                  key={g.rank}
                  href={`/idols/${g.rank}`}
                  className="roster-chip"
                  style={{ borderColor: groupColor(g.group) }}
                >
                  <span className="roster-dot" style={{ background: groupColor(g.group) }} />
                  <span className="roster-name">{g.member}</span>
                  <span className="roster-group">{g.rank}위</span>
                </Link>
              ))}
            </div>
          </section>
        ) : null}

        <p className="muted src-line">출처 한국기업평판연구소 · 편집 daily_enter_kr</p>
        <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
      </article>
    </AppShell>
  );
}
