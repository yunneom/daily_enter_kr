import type { MetadataRoute } from "next";
import { allGroups, allMembers } from "@/lib/idolContent";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  // 멤버/그룹 상세는 오리지널 에디토리얼이 실린 본문 페이지다. 색인 대상에서
  // 빠지면 사이트의 콘텐츠 가치가 사실상 검색에 노출되지 않으므로 반드시 등재한다
  // (2026-07: 인덱스 3개만 올리고 상세 47개가 누락돼 있던 것을 바로잡음).
  // 각 상세 페이지는 자기참조 canonical 을 라우트 값으로 선언한다 —
  // scripts/check-canonical.mjs 가 동적 라우트도 함께 검증한다.
  const memberPages: MetadataRoute.Sitemap = allMembers().map((m) => ({
    url: `${SITE_URL}/idols/${m.rank}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));
  const groupPages: MetadataRoute.Sitemap = allGroups().map((g) => ({
    url: `${SITE_URL}/groups/${g.slug}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/play`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/bracket`, lastModified: now, changeFrequency: "daily", priority: 0.7 },
    { url: `${SITE_URL}/results`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${SITE_URL}/recap`, lastModified: now, changeFrequency: "daily", priority: 0.6 },
    { url: `${SITE_URL}/guide`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${SITE_URL}/groups`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE_URL}/idols`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/contact`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/credits`, lastModified: now, changeFrequency: "weekly", priority: 0.3 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    ...memberPages,
    ...groupPages,
  ];
}
