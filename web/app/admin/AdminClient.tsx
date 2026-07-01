"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminClient() {
  const router = useRouter();
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reset() {
    if (!window.confirm("집계를 모두 초기화합니다. 되돌릴 수 없습니다. 계속할까요?")) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch("/api/admin/reset", { method: "POST" });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (res.ok && data.ok) {
        setMsg("집계를 초기화했습니다.");
        router.refresh();
      } else {
        setMsg(`실패: ${data.error ?? res.status}`);
      }
    } catch {
      setMsg("네트워크 오류");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card danger-card">
      <strong>위험 구역</strong>
      <p className="muted">전체 참여 집계(우승/진출률/중복방지)를 삭제합니다.</p>
      <button className="btn-danger" onClick={reset} disabled={busy}>
        {busy ? "처리 중…" : "집계 초기화"}
      </button>
      {msg ? <p className="admin-msg">{msg}</p> : null}
    </div>
  );
}
