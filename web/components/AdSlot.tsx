"use client";

import { useEffect, useRef } from "react";
import { normalizeAdsClient } from "@/lib/adsense";

/**
 * Google AdSense slot. Renders NOTHING until NEXT_PUBLIC_ADSENSE_CLIENT is set,
 * so the app stays visually clean until a real publisher id (ca-pub-XXXX) is
 * configured AND the AdSense account/domain is approved.
 *
 * Placement rule: only on non-intrusive surfaces (bottom of /results, /bracket).
 * Never inside the /play voting flow.
 */
export default function AdSlot({ slot, className }: { slot?: string; className?: string }) {
  const client = normalizeAdsClient(process.env.NEXT_PUBLIC_ADSENSE_CLIENT);
  const pushed = useRef(false);

  useEffect(() => {
    if (!client) return;
    if (pushed.current) return; // guard against duplicate push (StrictMode / re-render)
    pushed.current = true;
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ((window as any).adsbygoogle = (window as any).adsbygoogle || []).push({});
    } catch {
      /* ignore — loader not ready or blocked */
    }
  }, [client]);

  if (!client) return null;

  return (
    <div className={`ad-slot ${className ?? ""}`}>
      <ins
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={client}
        data-ad-slot={slot}
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </div>
  );
}
