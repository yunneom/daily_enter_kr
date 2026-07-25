import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";

const TITLE = "문의 — 걸그룹 이상형 월드컵";
const DESC =
  "걸그룹 이상형 월드컵 운영 문의, 사진 라이선스 정정, 콘텐츠 관련 요청을 보내는 방법을 안내합니다.";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/contact" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "website",
    locale: "ko_KR",
    url: "/contact",
  },
};

export default function ContactPage() {
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "ContactPage",
    name: TITLE,
    description: DESC,
    url: `${SITE_URL}/contact`,
  };

  return (
    <AppShell title="문의">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonld) }}
      />
      <div className="legal-doc">
        <h1 className="page-h1">문의</h1>
        <p>
          사이트 운영, 콘텐츠, 사진 라이선스 정정, 제휴 등 어떤 문의든 아래 채널로 연락해
          주세요. 확인하는 대로 성실히 답변드리겠습니다.
        </p>

        <h2>연락 방법</h2>
        <ul>
          <li>
            인스타그램 다이렉트 메시지: <strong>@daily_enter_kr</strong> —{" "}
            <a
              href="https://www.instagram.com/daily_enter_kr/"
              target="_blank"
              rel="noopener noreferrer"
            >
              instagram.com/daily_enter_kr
            </a>
          </li>
          <li>인스타그램 게시물 댓글로 남겨주셔도 확인합니다.</li>
        </ul>

        <h2>사진·저작권 관련</h2>
        <p>
          사이트의 모든 멤버 사진은 위키미디어 공용의 자유 라이선스 저작물을 사용합니다.
          출처 표기 정정이나 특정 사진의 사용 중단을 원하시면{" "}
          <Link href="/credits">이미지 출처</Link> 페이지에서 해당 파일을 확인한 뒤 위
          채널로 알려주세요. 요청은 신속히 반영하겠습니다.
        </p>

        <h2>정정·삭제 요청</h2>
        <p>
          소개 글에 사실과 다른 내용이 있거나 당사자로서 정보 수정을 원하시는 경우에도 위
          채널로 연락 주시면 검토 후 조치하겠습니다.
        </p>

        <p className="muted src-line">
          <Link href="/about">사이트 소개</Link> ·{" "}
          <Link href="/privacy">개인정보처리방침</Link> ·{" "}
          <Link href="/terms">이용약관</Link>
        </p>
      </div>
    </AppShell>
  );
}
