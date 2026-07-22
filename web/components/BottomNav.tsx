"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// 어드민은 공개 내비게이션에서 숨김(비밀번호 잠금 + /admin 직접 접근만).
const TABS: { href: string; label: string }[] = [
  { href: "/", label: "홈" },
  { href: "/idols", label: "프로필" },
  { href: "/bracket", label: "대진표" },
  { href: "/results", label: "결과" },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="bottom-nav">
      {TABS.map((t) => {
        const active =
          t.href === "/"
            ? pathname === "/"
            : pathname === t.href || pathname.startsWith(t.href + "/");
        return (
          <Link key={t.href} href={t.href} className={active ? "active" : ""}>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
