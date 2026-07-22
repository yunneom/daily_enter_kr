import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import { groupColor } from "@/lib/colors";
import { allGroups } from "@/lib/idolContent";

const TITLE = "걸그룹 소개 — 이상형 월드컵 참가 그룹";
const DESC =
  "걸그룹 이상형 월드컵에 참가하는 그룹들을 소개합니다. 각 그룹의 개성과 참가 멤버, 개별 그룹 소개 페이지로 이동할 수 있습니다.";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/groups" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "website",
    locale: "ko_KR",
    url: "/groups",
    images: ["/api/og"],
  },
};

export default function GroupsIndexPage() {
  const groups = allGroups();

  const jsonld = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: TITLE,
    description: DESC,
    url: `${SITE_URL}/groups`,
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: groups.length,
      itemListElement: groups.map((g, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: g.name,
        url: `${SITE_URL}/groups/${g.slug}`,
      })),
    },
  };

  return (
    <AppShell title="그룹 소개">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonld) }}
      />

      <section className="page-intro">
        <h1 className="page-h1">걸그룹 소개</h1>
        <p className="muted">
          이상형 월드컵에 참가하는 {groups.length}개 그룹을 소개합니다. 그룹 이름을 누르면
          소개 글과 참가 멤버를 볼 수 있습니다.
        </p>
      </section>

      <div className="grp-cards">
        {groups.map((g) => (
          <Link
            key={g.slug}
            href={`/groups/${g.slug}`}
            className="grp-card"
            style={{ borderTopColor: groupColor(g.name) }}
          >
            <span className="grp-card-name">{g.name}</span>
            <span className="grp-card-tag">{g.tagline}</span>
            <span className="grp-card-count" style={{ color: groupColor(g.name) }}>
              참가 {g.memberRanks.length}인
            </span>
          </Link>
        ))}
      </div>

      <p className="muted src-line">
        <Link href="/idols">멤버별로 보기 →</Link>
      </p>
      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
    </AppShell>
  );
}
