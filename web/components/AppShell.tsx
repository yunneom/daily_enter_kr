import BottomNav from "./BottomNav";

export default function AppShell({
  title = "이상형 월드컵",
  subtitle,
  hideNav = false,
  wide = false,
  children,
}: {
  title?: string;
  subtitle?: string;
  hideNav?: boolean;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`app-shell ${wide ? "wide" : ""}`}>
      <header className="app-header">
        <span className="app-header-title">{title}</span>
        {subtitle ? <span className="app-header-sub">{subtitle}</span> : null}
      </header>
      <main className={`app-main ${hideNav ? "no-nav" : ""}`}>{children}</main>
      {hideNav ? null : <BottomNav />}
    </div>
  );
}
