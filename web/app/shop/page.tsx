import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import { SHOP_LINKS, COUPANG_DISCLOSURE } from "@/lib/shopLinks";

export const metadata: Metadata = {
  title: "쇼핑 · daily_enter_kr",
  description: "K-POP 굿즈부터 야식까지 — daily_enter_kr 카테고리별 추천템.",
};

// 이 페이지를 '리뷰 있는 상품(Product)'이 아니라 '제휴 카테고리 링크 모음(CollectionPage)'으로
// 정확히 명시 → Google 의 Product 스니펫(review/aggregateRating) 오탐지 방지. (가짜 리뷰 X)
const SHOP_JSONLD = {
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  name: "쇼핑 추천 · daily_enter_kr",
  url: "https://dailyenterkr.com/shop",
  inLanguage: "ko",
  isPartOf: { "@type": "WebSite", url: "https://dailyenterkr.com" },
  about: "K-POP 굿즈부터 야식까지 카테고리별 추천 링크 모음 (쿠팡 파트너스 제휴)",
  mainEntity: {
    "@type": "ItemList",
    itemListElement: SHOP_LINKS.map((s, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: s.category,
    })),
  },
};

export default function ShopPage() {
  return (
    <AppShell title="쇼핑" subtitle="daily_enter_kr PICK">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(SHOP_JSONLD) }}
      />
      <section className="hero-wc">
        <div className="hero-kicker">daily_enter_kr PICK</div>
        <h1 className="hero-title">오늘의 추천템</h1>
        <p className="hero-sub">K-POP 굿즈부터 야식까지 · 카테고리별 큐레이션</p>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "14px",
          marginTop: "8px",
        }}
      >
        {SHOP_LINKS.map((s) => (
          <a
            key={s.category}
            href={s.url}
            target="_blank"
            rel="sponsored nofollow noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "18px",
              padding: "20px 22px",
              borderRadius: "18px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <span style={{ fontSize: "40px", lineHeight: 1 }} aria-hidden>
              {s.emoji}
            </span>
            <span style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
              <span style={{ fontSize: "22px", fontWeight: 800 }}>{s.category}</span>
              <span style={{ fontSize: "15px", opacity: 0.66 }}>{s.hint}</span>
            </span>
            <span style={{ fontSize: "22px", opacity: 0.5 }} aria-hidden>
              ›
            </span>
          </a>
        ))}
      </section>

      <p className="muted" style={{ marginTop: "22px", fontSize: "13px", lineHeight: 1.5 }}>
        {COUPANG_DISCLOSURE}
      </p>
    </AppShell>
  );
}
