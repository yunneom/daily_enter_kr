"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import momentRaw from "@/data/moment.json";

/**
 * Campaign moment banner (e.g. IG 결승 게시 → 우승 발표 window).
 * Config is bundled from data/moment.json — change + redeploy to update.
 *
 *   active:false      → renders nothing
 *   before deadline   → title + live countdown + CTA (cfg.href / cfg.cta)
 *   after deadline    → announcement copy + CTA to /recap
 */

interface MomentConfig {
  active: boolean;
  title: string;
  deadlineISO: string;
  deadlineLabel: string;
  href: string;
  cta: string;
}

const cfg = momentRaw as MomentConfig;

function formatRemaining(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(total / 86400);
  const h = String(Math.floor((total % 86400) / 3600)).padStart(2, "0");
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return days > 0 ? `D-${days} ${h}:${m}:${s}` : `${h}:${m}:${s}`;
}

export default function MomentBanner() {
  // null until mounted → SSR and first client render agree (no hydration diff).
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  if (!cfg.active) return null;
  const deadline = Date.parse(cfg.deadlineISO);
  if (!Number.isFinite(deadline)) return null;

  const over = now != null && now >= deadline;

  if (over) {
    return (
      <div className="moment-banner" role="status">
        <div className="moment-banner-lines">
          <span className="moment-banner-title">우승자가 발표되었습니다</span>
        </div>
        <Link href="/recap" className="moment-banner-cta">
          우승 리캡 보기
        </Link>
      </div>
    );
  }

  return (
    <div className="moment-banner" role="status">
      <div className="moment-banner-lines">
        <span className="moment-banner-title">{cfg.title}</span>
        <span className="moment-banner-count">
          {cfg.deadlineLabel}{" "}
          <b suppressHydrationWarning>{now == null ? "--:--:--" : formatRemaining(deadline - now)}</b>
        </span>
      </div>
      <Link href={cfg.href} className="moment-banner-cta">
        {cfg.cta}
      </Link>
    </div>
  );
}
