import type { Metadata } from "next";
import Link from "next/link";
import AppShell from "@/components/AppShell";

const TITLE = "이용약관 — 걸그룹 이상형 월드컵";
const DESC =
  "걸그룹 이상형 월드컵 서비스 이용약관. 서비스 성격, 콘텐츠 저작권, 면책, 광고에 관한 안내입니다.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/terms" },
};

const UPDATED = "2026-07-25";
const VERSION = "1.0";

export default function TermsPage() {
  return (
    <AppShell title="이용약관">
      <div className="legal-doc">
        <p className="legal-meta">
          최종 개정일 {UPDATED} · 버전 {VERSION}
        </p>
        <p>
          본 약관은 걸그룹 이상형 월드컵(dailyenterkr.com, 이하 &ldquo;서비스&rdquo;) 이용에
          관한 조건을 안내합니다. 서비스를 이용함으로써 이용자는 본 약관에 동의한 것으로
          봅니다.
        </p>

        <h2>1. 서비스의 성격</h2>
        <p>
          서비스는 걸그룹 멤버를 대상으로 한 취향 선택형 콘텐츠(이상형 월드컵)와 관련
          소개 글을 제공합니다. 집계 결과는 참여자의 주관적 선택을 모은 것으로, 특정
          인물에 대한 객관적 평가나 순위를 보증하지 않습니다.
        </p>

        <h2>2. 콘텐츠와 저작권</h2>
        <p>
          서비스가 직접 작성한 소개 글·가이드·디자인의 저작권은 운영자에게 있습니다.
          멤버 사진은 위키미디어 공용의 자유 라이선스 저작물을 사용하며, 각 사진의 저작자와
          라이선스는 <Link href="/credits">이미지 출처</Link> 페이지에 표기합니다. 순위
          데이터의 출처는 한국기업평판연구소입니다. 서비스의 창작 콘텐츠를 무단으로 복제·
          배포하는 것은 제한될 수 있습니다.
        </p>

        <h2>3. 이용자의 책임</h2>
        <p>
          이용자는 서비스를 자동화된 방식으로 대량 조작하거나, 집계의 무결성을 훼손하는
          행위를 해서는 안 됩니다. 서비스 운영을 방해하는 행위가 확인되면 이용이 제한될 수
          있습니다.
        </p>

        <h2>4. 광고</h2>
        <p>
          서비스에는 Google AdSense 등 제3자 광고가 게재될 수 있습니다. 광고와 관련한
          쿠키 사용 및 옵트아웃 안내는 <Link href="/privacy">개인정보처리방침</Link>을
          참고해 주세요.
        </p>

        <h2>5. 면책</h2>
        <p>
          서비스는 콘텐츠의 정확성을 위해 노력하지만, 제공되는 정보의 완전성이나 특정 목적
          적합성을 보증하지 않습니다. 서비스 이용으로 발생한 결과에 대해 운영자는 관련
          법령이 허용하는 범위에서 책임을 제한합니다.
        </p>

        <h2>6. 약관의 변경</h2>
        <p>
          본 약관은 필요에 따라 개정될 수 있으며, 개정 시 본 페이지에 최종 개정일과 함께
          게시합니다.
        </p>

        <h2>7. 문의</h2>
        <p>
          약관에 관한 문의는 <Link href="/contact">문의 페이지</Link>를 통해 연락해
          주세요.
        </p>
      </div>
    </AppShell>
  );
}
