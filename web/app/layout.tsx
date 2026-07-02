import type { Metadata, Viewport } from "next";
import Script from "next/script";
import Link from "next/link";
import "./globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";
const SITE_TITLE = "걸그룹 이상형 월드컵 — 당신이 뽑는 우승자는?";
const SITE_DESC =
  "32강부터 결승까지 직접 선택하는 걸그룹 이상형 월드컵. 우승자는 전체 참여자 기준으로 실시간 집계됩니다.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: SITE_TITLE,
  description: SITE_DESC,
  alternates: { canonical: "/" },
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESC,
    type: "website",
    locale: "ko_KR",
    url: "/",
    siteName: "걸그룹 이상형 월드컵",
    images: ["/api/og"],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESC,
    images: ["/api/og"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0b0b12",
};

// Member photos are served from these external hosts (plain <img>).
// Preconnect/dns-prefetch cuts the first-image latency on /play.
const IMAGE_HOSTS = [
  "https://commons.wikimedia.org",
  "https://upload.wikimedia.org",
  "https://encrypted-tbn0.gstatic.com",
];

const WEBSITE_JSONLD = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "걸그룹 이상형 월드컵",
  url: SITE_URL,
  inLanguage: "ko",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const adsClient = process.env.NEXT_PUBLIC_ADSENSE_CLIENT;

  return (
    <html lang="ko">
      <head>
        {IMAGE_HOSTS.map((host) => (
          <link key={`pc-${host}`} rel="preconnect" href={host} crossOrigin="anonymous" />
        ))}
        {IMAGE_HOSTS.map((host) => (
          <link key={`dp-${host}`} rel="dns-prefetch" href={host} />
        ))}
      </head>
      <body>
        <script
          type="application/ld+json"
          // Static, build-time JSON — no user input flows in here.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(WEBSITE_JSONLD) }}
        />
        {children}
        <footer className="site-footer">
          <Link href="/privacy" className="site-footer-link">
            개인정보처리방침
          </Link>
          <span className="site-footer-sep">·</span>
          <span className="site-footer-handle">@daily_enter_kr</span>
        </footer>
        {adsClient ? (
          <Script
            async
            src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsClient}`}
            crossOrigin="anonymous"
            strategy="afterInteractive"
          />
        ) : null}
      </body>
    </html>
  );
}
