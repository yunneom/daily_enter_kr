import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";

const TITLE = "걸그룹 이상형 월드컵 가이드 — 규칙, 시드, 자주 묻는 질문";
const DESC =
  "걸그룹 이상형 월드컵을 어떻게 진행하는지, 32강 시드는 어떻게 정해지는지, 결과는 어떻게 집계되는지 정리한 가이드입니다.";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://dailyenterkr.com";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/guide" },
  openGraph: {
    title: TITLE,
    description: DESC,
    type: "article",
    locale: "ko_KR",
    url: "/guide",
    images: ["/api/og"],
  },
};

const FAQ: { q: string; a: string }[] = [
  {
    q: "이상형 월드컵은 어떻게 진행되나요?",
    a: "32강부터 시작합니다. 화면에 두 명이 함께 나오면 더 마음에 드는 한 명을 탭으로 고릅니다. 고른 사람이 다음 라운드로 올라가고, 16강 · 8강 · 4강 · 준결승 · 결승까지 같은 방식으로 좁혀집니다. 결승에서 마지막으로 고른 한 명이 당신의 우승자입니다.",
  },
  {
    q: "32강 시드는 어떻게 정해지나요?",
    a: "매달 발표되는 한국기업평판연구소의 걸그룹 개인 브랜드평판 순위를 기준으로 상위 32명을 시드로 배치합니다. 브랜드평판은 소비자 참여 · 미디어 · 소통 · 커뮤니티 지표를 종합한 공개 지표로, 특정 팬덤의 화력만으로 좌우되지 않도록 균형을 잡는 출발점 역할을 합니다.",
  },
  {
    q: "결과는 어떻게 집계되나요?",
    a: "당신이 결승까지 완주하면 그 우승자가 전체 참여자 집계에 한 표로 더해집니다. 결과 페이지에서는 지금까지 가장 많이 우승한 멤버와 라운드별 진출률을 실시간으로 확인할 수 있습니다. 개인을 식별하는 정보는 저장하지 않습니다.",
  },
  {
    q: "매번 대진이 같나요?",
    a: "시드(참가자)는 같지만 맞대결에서 누구를 고르느냐에 따라 매 판의 흐름이 달라집니다. 같은 멤버라도 어떤 상대를 만나느냐에 따라 결과가 바뀌기 때문에, 여러 번 돌려보면 자신의 취향을 더 또렷하게 확인할 수 있습니다.",
  },
  {
    q: "인스타그램 월드컵과는 다른가요?",
    a: "같은 시즌을 두 곳에서 함께 진행합니다. 인스타그램(@daily_enter_kr)에서는 라운드별로 맞대결을 카드·릴스로 올려 댓글과 좋아요로 투표를 받고, 이 웹에서는 처음부터 끝까지 혼자 완주하는 방식입니다. 두 경로의 결과를 함께 보면 흐름이 더 재미있습니다.",
  },
];

export default function GuidePage() {
  const faqJsonld = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };
  const articleJsonld = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: TITLE,
    description: DESC,
    inLanguage: "ko",
    url: `${SITE_URL}/guide`,
    publisher: { "@type": "Organization", name: "daily_enter_kr" },
  };

  return (
    <AppShell title="가이드">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonld) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonld) }}
      />

      <article className="guide-doc">
        <h1 className="page-h1">걸그룹 이상형 월드컵 가이드</h1>
        <p className="guide-lead">
          걸그룹 이상형 월드컵은 32명의 걸그룹 멤버를 두 명씩 맞붙여, 당신의 선택만으로
          한 명의 우승자를 가려내는 토너먼트입니다. 정답이 없는 취향의 게임이라, 누구를
          고르든 그 판의 우승자는 오롯이 당신의 몫입니다. 이 페이지는 규칙과 시드 방식,
          그리고 자주 묻는 질문을 정리한 안내서입니다.
        </p>

        <section>
          <h2 className="section-title">진행 방식</h2>
          <p>
            시작 버튼을 누르면 32강 첫 대결이 나옵니다. 두 멤버 중 더 끌리는 쪽을 한 번
            탭하면 바로 다음 대결로 넘어갑니다. 고민이 길어질 필요는 없습니다. 첫인상,
            무대, 이미지, 그날의 기분 — 무엇을 기준으로 삼아도 괜찮습니다.
          </p>
          <p>
            라운드는 32강 → 16강 → 8강 → 4강 → 준결승 → 결승 순으로 좁혀집니다. 매
            라운드에서 살아남은 절반만 다음 판으로 올라가고, 마지막 결승에서 고른 한
            명이 당신만의 우승자가 됩니다. 완주까지는 보통 1~2분이면 충분합니다.
          </p>
        </section>

        <section>
          <h2 className="section-title">시드는 어떻게 정하나</h2>
          <p>
            참가자는 매달 발표되는 한국기업평판연구소의 걸그룹 개인 브랜드평판 순위에서
            상위 32명을 추립니다. 브랜드평판 지수는 특정 이슈나 순간의 화제성만이 아니라
            꾸준한 참여도와 소통, 미디어 노출을 함께 반영하기 때문에, 시즌의 출발선을
            공정하게 긋는 기준으로 삼기에 적합합니다.
          </p>
          <p>
            다만 시드는 어디까지나 시작점일 뿐입니다. 브랜드평판 1위라고 해서 반드시
            우승하는 것은 아니고, 낮은 시드의 멤버가 맞대결을 거듭하며 끝까지 살아남는
            경우도 많습니다. 순위표를 뒤집는 재미가 이 게임의 핵심입니다.
          </p>
        </section>

        <section>
          <h2 className="section-title">결과와 집계</h2>
          <p>
            당신이 결승까지 완주하면 그 우승자가 전체 참여자 집계에 한 표로 반영됩니다.
            결과 페이지에서는 지금까지 가장 많이 우승한 멤버, 라운드별 진출률, 그리고
            전체 흐름을 실시간으로 확인할 수 있습니다. 우리는 개인을 식별할 수 있는
            정보를 저장하지 않으며, 집계는 익명 합산으로만 이루어집니다.
          </p>
          <p>
            더 자세한 흐름은 <Link href="/results">결과</Link> 페이지와{" "}
            <Link href="/recap">우승 리캡</Link>에서, 전체 대진은{" "}
            <Link href="/bracket">대진표</Link>에서 볼 수 있습니다.
          </p>
        </section>

        <section>
          <h2 className="section-title">자주 묻는 질문</h2>
          <div className="guide-faq">
            {FAQ.map((f) => (
              <details key={f.q} className="guide-faq-item">
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section>
          <h2 className="section-title">더 둘러보기</h2>
          <p>
            참가 멤버 한 명 한 명이 궁금하다면 <Link href="/idols">멤버 프로필</Link>을,
            그룹별 소개가 보고 싶다면 <Link href="/groups">그룹 소개</Link>를 확인해
            보세요. 준비가 됐다면 지금 바로 월드컵을 시작할 수 있습니다.
          </p>
          <div className="prof-links">
            <Link href="/play" className="btn-vs">
              지금 월드컵 시작
            </Link>
          </div>
        </section>

        <p className="muted src-line">출처 한국기업평판연구소 · 편집 daily_enter_kr</p>
        <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
      </article>
    </AppShell>
  );
}
