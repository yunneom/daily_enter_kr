"use client";

import { useState } from "react";

export default function AdminClient({ round }: { round: string }) {
  const [adminKey, setAdminKey] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  async function act(action: "open" | "lock" | "extend") {
    setMsg(null);
    try {
      const res = await fetch("/api/admin/round", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(adminKey ? { "x-admin-key": adminKey } : {}),
        },
        body: JSON.stringify({ round, action }),
      });
      const data = (await res.json()) as { error?: string; state?: string };
      if (res.ok) setMsg(`${round} → ${data.state ?? action}`);
      else setMsg(`실패: ${data.error ?? res.status}`);
    } catch {
      setMsg("네트워크 오류");
    }
  }

  return (
    <div className="card">
      <strong>라운드 제어 ({round})</strong>
      <input
        className="btn"
        style={{ textAlign: "left", fontWeight: 400 }}
        placeholder="ADMIN_KEY (설정 시)"
        value={adminKey}
        onChange={(e) => setAdminKey(e.target.value)}
      />
      <button className="btn btn-primary" onClick={() => act("open")}>
        라운드 열기 (open)
      </button>
      <button className="btn" onClick={() => act("lock")}>
        라운드 마감 (lock)
      </button>
      <button className="btn" onClick={() => act("extend")}>
        연장 (extend)
      </button>
      <a className="btn" href="#" onClick={(e) => e.preventDefault()}>
        winner 정정 (stub)
      </a>
      {msg ? <p className="muted">{msg}</p> : null}
    </div>
  );
}
