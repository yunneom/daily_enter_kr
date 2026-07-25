import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { imageCredits } from "@/lib/imageCredits";

const TITLE = "이미지 출처 — 걸그룹 이상형 월드컵";
const DESC =
  "사이트에 사용된 멤버 사진의 출처와 라이선스 안내. 모든 사진은 위키미디어 공용(Wikimedia Commons)의 자유 이용 저작물이며, 각 파일의 설명 문서로 연결됩니다.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/credits" },
};

export default function CreditsPage() {
  const credits = imageCredits();

  return (
    <AppShell title="이미지 출처">
      <div className="legal-doc">
        <p>
          이 사이트에 표시되는 멤버 사진은 모두 위키미디어 공용(Wikimedia Commons)에
          자유 라이선스로 공개된 저작물을 사용합니다. 각 사진의 저작자와 정확한
          라이선스(대개 CC BY 또는 CC BY-SA)는 아래 파일별 링크의 설명 문서에서 확인할
          수 있습니다. 사진을 제공해 주신 촬영자와 기여자분들께 감사드립니다.
        </p>
        <p className="muted">
          라이선스 정정이나 사진 관련 문의는 <Link href="/contact">문의 페이지</Link>를
          통해 알려주시면 신속히 반영하겠습니다. 별도의 사진이 지정되지 않은 멤버는
          사이트 자체 디자인(그룹 색상 카드)으로 표시됩니다.
        </p>

        <h2>사진 출처 목록</h2>
        <ul className="credits-list">
          {credits.map((c) => (
            <li key={c.rank}>
              <span className="credits-name">
                {c.group} {c.member}
              </span>
              <a href={c.filePageUrl} target="_blank" rel="noopener noreferrer nofollow">
                {c.fileName}
              </a>
            </li>
          ))}
        </ul>

        <p className="muted">
          모든 파일: Wikimedia Commons · 각 링크의 설명 문서에 저작자 및 라이선스 표기.
        </p>
      </div>
    </AppShell>
  );
}
