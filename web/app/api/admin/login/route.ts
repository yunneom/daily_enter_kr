import { NextRequest, NextResponse } from "next/server";
import { ADMIN_COOKIE, sha256Hex } from "@/lib/adminAuth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface Body {
  password?: string;
}

export async function POST(req: NextRequest) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
    return NextResponse.json(
      { error: "ADMIN_LOCKED", detail: "ADMIN_PASSWORD 미설정" },
      { status: 403 },
    );
  }

  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ error: "INVALID_JSON" }, { status: 400 });
  }

  const password = body.password ?? "";
  if (password !== expected) {
    return NextResponse.json({ error: "WRONG_PASSWORD" }, { status: 401 });
  }

  const token = await sha256Hex(password);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(ADMIN_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12, // 12h
  });
  return res;
}
