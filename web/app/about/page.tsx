import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";

const TITLE = "사이트 소개 — 걸그룹 이상형 월드컵";
const DESC =
  "걸그룹 이상형 월드컵(dailyenterkr.com)이 어떤 사이트인지, 참가자 선정과 데이터·이미지 출처, 운영 방식을 안내합니다.";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/about" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "website",
    locale: "ko_KR",
    url: "/about",
  },
};

export default function AboutPage() {
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: TITLE,
    description: DESC,
    url: `${SITE_URL}/about`,
    publisher: { "@type": "Organization", name: "daily_enter_kr" },
  };

  return (
    <AppShell title="사이트 소개">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonld) }}
      />
      <div className="legal-doc">
        <h1 className="page-h1">사이트 소개</h1>
        <p>
          걸그룹 이상형 월드컵(dailyenterkr.com)은 대한민국 걸그룹을 좋아하는 사람들이
          자신의 취향을 가볍게 확인하고 나눌 수 있도록 만든 참여형 콘텐츠 사이트입니다.
          32명의 멤버를 두 명씩 맞붙이는 토너먼트를 직접 진행해 나만의 우승자를 뽑고,
          전체 참여자의 선택이 어떻게 모이는지 실시간으로 확인할 수 있습니다.
        </p>

        <h2>무엇을 하는 곳인가요</h2>
        <p>
          핵심은 <Link href="/play">이상형 월드컵</Link> 플레이입니다. 여기에 더해 참가
          멤버 한 명 한 명을 소개하는 <Link href="/idols">멤버 프로필</Link>, 그룹별
          <Link href="/groups"> 그룹 소개</Link>, 규칙과 집계 방식을 정리한{" "}
          <Link href="/guide">가이드</Link>를 제공합니다. 모든 소개 글은 직접 작성한
          창작 텍스트이며, 특정 기사나 자료를 그대로 옮기지 않습니다.
        </p>

        <h2>참가자는 어떻게 정하나요</h2>
        <p>
          참가 32인은 매달 발표되는 한국기업평판연구소의 걸그룹 개인 브랜드평판 순위에서
          상위 인원을 기준으로 구성합니다. 브랜드평판 지수는 소비자 참여·미디어·소통·
          커뮤니티 지표를 종합한 공개 지표로, 특정 순간의 화제성에 치우치지 않는 출발선을
          만들기 위해 참고합니다. 시드는 시작점일 뿐이며, 최종 결과는 참여자의 선택으로
          결정됩니다.
        </p>

        <h2>데이터와 이미지 출처</h2>
        <p>
          순위 데이터의 출처는 한국기업평판연구소입니다. 멤버 사진은 모두 위키미디어
          공용(Wikimedia Commons)에 자유 라이선스로 공개된 저작물만 사용하며, 사진별
          저작자와 라이선스는 <Link href="/credits">이미지 출처</Link> 페이지에 정리해
          두었습니다. 사진이 지정되지 않은 멤버는 사이트 자체 디자인으로 표시됩니다.
        </p>

        <h2>운영과 연락</h2>
        <p>
          이 사이트는 걸그룹 관련 콘텐츠를 만드는 개인 운영 채널 daily_enter_kr가
          운영합니다. 인스타그램 <strong>@daily_enter_kr</strong>에서 같은 시즌의
          월드컵을 함께 진행합니다. 문의·정정·제휴 요청은{" "}
          <Link href="/contact">문의 페이지</Link>를 참고해 주세요.
        </p>

        <h2>지향</h2>
        <p>
          우리는 특정 멤버를 깎아내리거나 외모·사생활을 자극적으로 다루지 않습니다. 모든
          소개는 존중하는 톤을 유지하며, 확인되지 않은 사생활·건강·연애 관련 추측은 싣지
          않습니다. 이상형 월드컵은 어디까지나 취향을 즐기는 놀이라는 점을 가장 중요하게
          생각합니다.
        </p>

        <p className="muted src-line">
          <Link href="/">홈으로</Link> · <Link href="/guide">가이드</Link> ·{" "}
          <Link href="/privacy">개인정보처리방침</Link>
        </p>
      </div>
    </AppShell>
  );
}
