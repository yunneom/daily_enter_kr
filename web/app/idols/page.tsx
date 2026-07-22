import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import { groupColor } from "@/lib/colors";
import { allMembers } from "@/lib/idolContent";

const TITLE = "걸그룹 멤버 프로필 — 이상형 월드컵 참가 32인";
const DESC =
  "걸그룹 이상형 월드컵에 참가하는 32명의 멤버 프로필. 브랜드평판 순위 순으로 정리한 소개와 개별 프로필 페이지로 이동할 수 있습니다.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/idols" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "website",
    locale: "ko_KR",
    url: "/idols",
    images: ["/api/og"],
  },
};

export default function IdolsIndexPage() {
  const members = [...allMembers()].sort((a, b) => a.rank - b.rank);

  const jsonld = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: TITLE,
    description: DESC,
    url: `${process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com"}/idols`,
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: members.length,
      itemListElement: members.map((m, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: `${m.group} ${m.member}`,
        url: `${process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com"}/idols/${m.rank}`,
      })),
    },
  };

  return (
    <AppShell title="멤버 프로필">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonld) }}
      />

      <section className="page-intro">
        <h1 className="page-h1">걸그룹 멤버 프로필</h1>
        <p className="muted">
          이상형 월드컵에 오른 32명의 멤버를 브랜드평판 순위 순으로 소개합니다. 이름을
          누르면 개별 프로필과 그룹 소개로 이어집니다.
        </p>
      </section>

      <div className="prof-cards">
        {members.map((m) => (
          <Link
            key={m.rank}
            href={`/idols/${m.rank}`}
            className="prof-card"
            style={{ borderLeftColor: groupColor(m.group) }}
          >
            <span className="prof-card-rank">{m.rank}</span>
            <span className="prof-card-body">
              <span className="prof-card-name">{m.member}</span>
              <span className="prof-card-group">{m.group}</span>
              <span className="prof-card-tag">{m.tagline}</span>
            </span>
          </Link>
        ))}
      </div>

      <p className="muted src-line">
        <Link href="/groups">그룹별로 보기 →</Link>
      </p>
      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
    </AppShell>
  );
}
