import type { Metadata, Viewport } from "next";
import Script from "next/script";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "이상형 월드컵",
  description: "32강부터 골라 우승까지. 나만의 이상형 월드컵. 출처 한국기업평판연구소.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0b0b12",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const adsClient = process.env.NEXT_PUBLIC_ADSENSE_CLIENT;

  return (
    <html lang="ko">
      <body>
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
