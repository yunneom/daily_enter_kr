import Link from "next/link";
import AppShell from "@/components/AppShell";
import AdSlot from "@/components/AdSlot";
import { loadRoster } from "@/lib/roster";
import { groupColor } from "@/lib/colors";
import LiveStats from "./LiveStats";

export const dynamic = "force-dynamic";

export default function HomePage() {
  const roster = loadRoster();

  return (
    <AppShell title="이상형 월드컵">
      <section className="hero-wc">
        <div className="hero-kicker">2026 상반기 걸그룹 월드컵</div>
        <h1 className="hero-title">당신이 뽑는 우승자는?</h1>
        <p className="hero-sub">TOP 32 중 최애를 골라 결승까지 · 결과는 실시간 집계</p>
        <Link href="/play" className="btn-vs hero-cta">
          지금 월드컵 시작
        </Link>
        <LiveStats />
      </section>

      <section className="how">
        <h2 className="section-title">어떻게 진행되나</h2>
        <ol className="how-steps">
          <li>
            <span className="how-num">1</span>
            <span>32강부터 둘 중 한 명을 탭으로 고릅니다.</span>
          </li>
          <li>
            <span className="how-num">2</span>
            <span>16강 · 8강 · 4강 · 준결승 · 결승까지 이어집니다.</span>
          </li>
          <li>
            <span className="how-num">3</span>
            <span>우승자가 정해지면 전체 참여자 결과에 집계됩니다.</span>
          </li>
        </ol>
      </section>

      <section className="roster">
        <h2 className="section-title">참가 32팀</h2>
        <div className="roster-grid">
          {roster.candidates.map((c) => (
            <div key={c.rank} className="roster-chip" style={{ borderColor: groupColor(c.group) }}>
              <span className="roster-dot" style={{ background: groupColor(c.group) }} />
              <span className="roster-name">{c.member}</span>
              <span className="roster-group">{c.group}</span>
            </div>
          ))}
        </div>
      </section>

      <p className="muted src-line">출처 한국기업평판연구소</p>

      <AdSlot slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOME} />
    </AppShell>
  );
}
