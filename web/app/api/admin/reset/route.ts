import { NextRequest, NextResponse } from "next/server";
import { resetAll } from "@/lib/runStore";
import { ADMIN_COOKIE, isAdminCookieValid } from "@/lib/adminAuth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  // Defense in depth: middleware already gates this, re-check server-side.
  const cookie = req.cookies.get(ADMIN_COOKIE)?.value;
  const ok = await isAdminCookieValid(cookie);
  if (!ok) {
    return NextResponse.json({ error: "UNAUTHORIZED" }, { status: 401 });
  }

  try {
    await resetAll();
    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ error: "RESET_FAILED", detail: String(err) }, { status: 500 });
  }
}
