"use client";

import { useState } from "react";
import { isSafeCopy } from "@/lib/safety";

export default function ShareClient({ title }: { title: string }) {
  const [copied, setCopied] = useState<string | null>(null);

  // Share copy is brand-safety checked; fall back to a neutral safe message.
  const baseCopy = `${title} 걸그룹 월드컵 투표하러 가기`;
  const shareCopy = isSafeCopy(baseCopy) ? baseCopy : "걸그룹 월드컵 투표하러 가기";

  async function copy(text: string, tag: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(tag);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setCopied(null);
    }
  }

  function currentUrl(): string {
    return typeof window !== "undefined" ? window.location.href : "";
  }

  return (
    <div>
      <button className="btn btn-primary" onClick={() => copy(currentUrl(), "url")}>
        {copied === "url" ? "링크 복사됨" : "링크 복사하기"}
      </button>
      <button className="btn" onClick={() => copy(`${shareCopy} ${currentUrl()}`, "kakao")}>
        {copied === "kakao" ? "카카오용 문구 복사됨" : "카카오톡 공유 문구 복사"}
      </button>
      <p className="muted" style={{ textAlign: "center" }}>
        [MVP] 클립보드 복사 방식. 추후 카카오/네이티브 공유 SDK 연동.
      </p>
    </div>
  );
}
