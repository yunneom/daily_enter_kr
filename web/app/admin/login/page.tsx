import AppShell from "@/components/AppShell";
import LoginClient from "./LoginClient";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default function AdminLoginPage() {
  const locked = !process.env.ADMIN_PASSWORD;
  return (
    <AppShell title="어드민 로그인">
      {locked ? (
        <div className="card danger-card">
          <strong>ADMIN_PASSWORD 미설정</strong>
          <p className="muted">
            환경변수 ADMIN_PASSWORD 가 설정되지 않아 어드민이 잠겨 있습니다. 배포 환경에
            ADMIN_PASSWORD 를 추가한 뒤 다시 시도하세요.
          </p>
        </div>
      ) : (
        <LoginClient />
      )}
    </AppShell>
  );
}
