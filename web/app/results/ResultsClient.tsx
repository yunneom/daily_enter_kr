"use client";

import { useEffect, useState } from "react";
import { groupColor } from "@/lib/colors";

interface ChampionRow {
  rank: number;
  group: string;
  member: string;
  count: number;
  pct: number;
}
interface AdvancementRow {
  rank: number;
  group: string;
  member: string;
  picks: number;
  appears: number;
  pickRate: number;
}
interface Results {
  runsTotal: number;
  champions: ChampionRow[];
  advancement: AdvancementRow[];
}

export default function ResultsClient() {
  const [data, setData] = useState<Results | null>(null);
  const [reveal, setReveal] = useState(false);
  const [tab, setTab] = useState<"champ" | "adv">("champ");
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [ago, setAgo] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = (force = false) => {
      // Pause polling while the tab is hidden — no point burning KV reads
      // for a page nobody is looking at.
      if (!force && document.hidden) return;
      fetch("/api/results")
        .then((r) => r.json())
        .then((d: Results) => {
          if (alive) {
            setData(d);
            setUpdatedAt(Date.now());
          }
        })
        .catch(() => {});
    };
    load(true);
    const id = window.setInterval(() => load(), 5000);
    const onVisibility = () => {
      if (!document.hidden) load(true); // refresh immediately on return
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      alive = false;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  // Tick "N초 전 갱신" once a second.
  useEffect(() => {
    const id = window.setInterval(() => {
      if (updatedAt != null) setAgo(Math.round((Date.now() - updatedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [updatedAt]);

  if (!data) {
    return <div className="results-loading">불러오는 중…</div>;
  }

  const champs = data.champions.filter((c) => c.count > 0);
  const maxPct = champs.length ? Math.max(...champs.map((c) => c.pct), 1) : 1;

  return (
    <div className="results-wrap">
      <div className="results-live-row">
        <span className="live-badge">
          <span className="live-dot" aria-hidden />
          LIVE · 실시간 집계
        </span>
        <span className="results-ago">{ago <= 1 ? "방금 갱신" : `${ago}초 전 갱신`}</span>
      </div>
      <div className="results-head">
        <div className="results-total">
          <span className="results-total-num">{data.runsTotal.toLocaleString()}</span>
          <span className="results-total-label">총 참여</span>
        </div>
        <button className={`reveal-toggle ${reveal ? "on" : ""}`} onClick={() => setReveal((v) => !v)}>
          발표 모드
        </button>
      </div>

      <div className="round-tabs">
        <button className={`round-tab ${tab === "champ" ? "active" : ""}`} onClick={() => setTab("champ")}>
          우승 랭킹
        </button>
        <button className={`round-tab ${tab === "adv" ? "active" : ""}`} onClick={() => setTab("adv")}>
          진출률
        </button>
      </div>

      {tab === "champ" ? (
        champs.length === 0 ? (
          <div className="bracket-empty">아직 집계된 우승자가 없습니다.</div>
        ) : (
          <ol className={`leaderboard ${reveal ? "reveal" : ""}`}>
            {champs.map((c, i) => (
              <li
                key={c.rank}
                className="lb-row"
                style={reveal ? { animationDelay: `${i * 90}ms` } : undefined}
              >
                <span className="lb-rank">{i + 1}</span>
                <span className="lb-dot" style={{ background: groupColor(c.group) }} />
                <span className="lb-name">
                  {c.member}
                  <span className="lb-group">{c.group}</span>
                </span>
                <span className="lb-bar-wrap">
                  <span
                    className="lb-bar"
                    style={{
                      width: `${Math.max(6, (c.pct / maxPct) * 100)}%`,
                      background: groupColor(c.group),
                    }}
                  />
                </span>
                <span className="lb-pct">
                  {c.pct}% <span className="muted">({c.count})</span>
                </span>
              </li>
            ))}
          </ol>
        )
      ) : (
        <table className="adv-table">
          <thead>
            <tr>
              <th>멤버</th>
              <th>선택</th>
              <th>등장</th>
              <th>진출률</th>
            </tr>
          </thead>
          <tbody>
            {data.advancement.map((r) => (
              <tr key={r.rank}>
                <td>
                  <span className="lb-dot sm" style={{ background: groupColor(r.group) }} />
                  {r.member}
                  <span className="lb-group">{r.group}</span>
                </td>
                <td>{r.picks}</td>
                <td>{r.appears}</td>
                <td>{r.pickRate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted src-line">5초마다 자동 갱신 · 출처 한국기업평판연구소</p>
    </div>
  );
}
