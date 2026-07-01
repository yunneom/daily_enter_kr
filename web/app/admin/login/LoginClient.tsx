"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginClient() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        router.replace("/admin");
        router.refresh();
        return;
      }
      const data = (await res.json()) as { error?: string };
      if (data.error === "ADMIN_LOCKED") setMsg("ADMIN_PASSWORD 미설정");
      else if (data.error === "WRONG_PASSWORD") setMsg("비밀번호가 올바르지 않습니다.");
      else setMsg(`실패: ${data.error ?? res.status}`);
    } catch {
      setMsg("네트워크 오류");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card login-card" onSubmit={submit}>
      <strong>어드민 로그인</strong>
      <input
        type="password"
        className="login-input"
        placeholder="비밀번호"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        autoFocus
      />
      <button className="btn-vs" type="submit" disabled={busy || !password}>
        {busy ? "확인 중…" : "로그인"}
      </button>
      {msg ? <p className="admin-msg err">{msg}</p> : null}
    </form>
  );
}
