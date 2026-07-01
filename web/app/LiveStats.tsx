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

  return (
    <div className="hero-stats">
      <div className="hero-stat">
        <span className="hero-stat-num">{data.runsTotal.toLocaleString()}</span>
        <span className="hero-stat-label">참여</span>
      </div>
      {top ? (
        <div className="hero-stat">
          <span className="hero-stat-num">{top.member}</span>
          <span className="hero-stat-label">현재 우승 1위 · {top.pct}%</span>
        </div>
      ) : (
        <div className="hero-stat">
          <span className="hero-stat-num">-</span>
          <span className="hero-stat-label">첫 우승자를 정해보세요</span>
        </div>
      )}
    </div>
  );
}
