import BottomNav from "./BottomNav";

export default function AppShell({
  title = "걸그룹 월드컵",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="app-header">{title}</header>
      <main className="app-main">{children}</main>
      <BottomNav />
    </div>
  );
}
