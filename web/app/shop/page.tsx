import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import { SHOP_LINKS, COUPANG_DISCLOSURE } from "@/lib/shopLinks";

export const metadata: Metadata = {
  title: "쇼핑 · daily_enter_kr",
  description: "K-POP 굿즈부터 야식까지 — daily_enter_kr 카테고리별 추천템.",
};

export default function ShopPage() {
  return (
    <AppShell title="쇼핑" subtitle="daily_enter_kr PICK">
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
