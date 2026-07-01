"use client";

import { useEffect, useState } from "react";

interface Results {
  runsTotal: number;
  champions: { rank: number; group: string; member: string; count: number; pct: number }[];
}

export default function LiveStats() {
  const [data, setData] = useState<Results | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/results")
      .then((r) => r.json())
      .then((d: Results) => {
        if (alive) setData(d);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  if (!data) return <div className="hero-stats placeholder" />;

  const top = data.champions.find((c) => c.count > 0);

  if (!top || data.runsTotal === 0) {
    return (
      <div className="hero-live">
        <span className="hero-live-dot" aria-hidden />
        <span className="hero-live-text">가장 먼저 참여해보세요</span>
      </div>
    );
  }

  return (
    <div className="hero-live">
      <span className="hero-live-dot" aria-hidden />
      <div className="hero-live-lines">
        <span className="hero-live-lead">
          지금 실시간 1위: {top.member} ({top.group}) {top.pct}%
        </span>
        <span className="hero-live-sub">누적 참여 {data.runsTotal.toLocaleString()}회</span>
      </div>
    </div>
  );
}
