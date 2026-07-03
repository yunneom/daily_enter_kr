import type { Metadata, Viewport } from "next";
import Script from "next/script";
import Link from "next/link";
import { normalizeAdsClient } from "@/lib/adsense";
import UtmCapture from "@/components/UtmCapture";
import "./globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";
const SITE_TITLE = "걸그룹 이상형 월드컵 — 당신이 뽑는 우승자는?";
const SITE_DESC =
  "32강부터 결승까지 직접 선택하는 걸그룹 이상형 월드컵. 우승자는 전체 참여자 기준으로 실시간 집계됩니다.";
// Official AdSense site-ownership meta tag (<meta name="google-adsense-account">) —
// a second, independent verification signal alongside the adsbygoogle.js snippet
// and ads.txt. Renders only once NEXT_PUBLIC_ADSENSE_CLIENT is set.
const ADS_CLIENT = normalizeAdsClient(process.env.NEXT_PUBLIC_ADSENSE_CLIENT);

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: SITE_TITLE,
  description: SITE_DESC,
  alternates: { canonical: "/" },
  ...(ADS_CLIENT ? { other: { "google-adsense-account": ADS_CLIENT } } : {}),
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
  const adsClient = normalizeAdsClient(process.env.NEXT_PUBLIC_ADSENSE_CLIENT);
  // Optional GA4 — renders nothing until NEXT_PUBLIC_GA4_ID is set.
  // Restrict to a safe id shape so the inline snippet never gets odd input.
  const ga4Raw = process.env.NEXT_PUBLIC_GA4_ID || "";
  const ga4Id = /^[A-Za-z0-9-]{1,32}$/.test(ga4Raw) ? ga4Raw : "";

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
        <UtmCapture />
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
        {ga4Id ? (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${ga4Id}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${ga4Id}');`}
            </Script>
          </>
        ) : null}
      </body>
    </html>
  );
}
