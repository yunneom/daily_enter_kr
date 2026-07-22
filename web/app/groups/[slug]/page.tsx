import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import MemberImage from "@/components/MemberImage";
import { groupColor, groupGradient } from "@/lib/colors";
import { allGroups, groupBySlug, membersOfGroup } from "@/lib/idolContent";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const dynamicParams = false;

export function generateStaticParams() {
  return allGroups().map((g) => ({ slug: g.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const g = groupBySlug(slug);
  if (!g) return { title: "그룹 소개 — 걸그룹 이상형 월드컵" };
  const title = `${g.name} — 걸그룹 이상형 월드컵 그룹 소개`;
  const desc = `${g.name} 소개와 이상형 월드컵 참가 멤버. ${g.tagline}`;
  const url = `/groups/${g.slug}`;
  return {
    title,
    description: desc,
    alternates: { canonical: url },
    openGraph: {
      title,
      description: desc,
      type: "website",
      locale: "ko_KR",
      url,
      images: ["/api/og"],
    },
  };
}

export default async function GroupProfilePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const g = groupBySlug(slug);
  if (!g) notFound();

  const color = groupColor(g.name);
  const members = membersOfGroup(g.slug);

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "그룹", item: `${SITE_URL}/groups` },
      { "@type": "ListItem", position: 3, name: g.name, item: `${SITE_URL}/groups/${g.slug}` },
    ],
  };

  return (
    <AppShell title="그룹 소개">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb) }}
      />

      <article className="prof">
        <header className="grp-hero" style={{ background: groupGradient(g.name) }}>
          <h1 className="grp-name">{g.name}</h1>
          <p className="prof-tag">{g.tagline}</p>
          <span className="grp-count">이상형 월드컵 참가 {members.length}인</span>
        </header>

        <section className="prof-intro">
          {g.intro.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </section>

        <section>
          <h2 className="section-title">참가 멤버</h2>
          <div className="grp-members">
            {members.map((m) => (
              <Link key={m.rank} href={`/idols/${m.rank}`} className="grp-member">
                <span className="grp-member-photo">
                  <MemberImage rank={m.rank} group={m.group} member={m.member} size={64} rounded />
                </span>
                <span className="grp-member-name">{m.member}</span>
                <span className="grp-member-rank" style={{ color }}>
                  브랜드평판 {m.rank}위
                </span>
              </Link>
            ))}
          </div>
        </section>

        <div className="prof-links">
          <Link href="/play" className="btn-vs">
            이상형 월드컵 시작하기
          </Link>
          <Link href="/groups" className="prof-link-secondary">
            다른 그룹 보기
          </Link>
        </div>

        <p className="muted src-line">출처 한국기업평판연구소 · 편집 daily_enter_kr</p>
        <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
      </article>
    </AppShell>
  );
}
