import Link from "next/link";
import AppShell from "@/components/AppShell";
import { loadBracket, roundLabel } from "@/lib/bracket";

export const dynamic = "force-dynamic";

export default function HomePage() {
  let currentLabel = "";
  try {
    const b = loadBracket();
    currentLabel = roundLabel(b.current_round);
  } catch {
    currentLabel = "";
  }

  return (
    <AppShell>
      <div className="hero">
        <h1>걸그룹 월드컵</h1>
        <p>1:1 투표로 가리는 32강 토너먼트{currentLabel ? ` · 현재 ${currentLabel}` : ""}</p>
        <Link href="/vote" className="btn btn-primary">
          지금 투표하기
        </Link>
      </div>

      <div className="card">
        <strong>투표 참여 방법</strong>
        <ol className="steps">
          <li>두 후보 중 한 명을 한 번의 탭으로 선택합니다.</li>
          <li>실시간 득표율과 다음 매치를 바로 확인합니다.</li>
          <li>대진표에서 라운드별 결과를 보고 친구에게 공유합니다.</li>
        </ol>
      </div>

      <p className="muted" style={{ textAlign: "center" }}>
        출처 한국기업평판연구소
      </p>
    </AppShell>
  );
}
