/**
 * Edge middleware gating /admin and /api/admin.
 *
 * - /admin/login and /api/admin/login always pass (so you can authenticate).
 * - Everything else under /admin requires cookie wc_admin === sha256(ADMIN_PASSWORD).
 * - If ADMIN_PASSWORD is unset, admin is LOCKED: page requests redirect to
 *   /admin/login (which shows the "미설정" notice), API requests get 401.
 *
 * Uses Web Crypto for sha256 so it runs on the edge runtime.
 */

import { NextRequest, NextResponse } from "next/server";
import { ADMIN_COOKIE, isAdminCookieValid } from "@/lib/adminAuth";

export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};

function isLoginPath(pathname: string): boolean {
  return pathname === "/admin/login" || pathname === "/api/admin/login";
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (isLoginPath(pathname)) {
    return NextResponse.next();
  }

  const cookie = req.cookies.get(ADMIN_COOKIE)?.value;
  const ok = await isAdminCookieValid(cookie);
  if (ok) return NextResponse.next();

  // Not authorized.
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "UNAUTHORIZED" }, { status: 401 });
  }

  const url = req.nextUrl.clone();
  url.pathname = "/admin/login";
  url.search = "";
  return NextResponse.redirect(url);
}
