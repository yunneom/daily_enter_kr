import { NextResponse } from "next/server";
import { loadBracket } from "@/lib/bracket";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const bracket = loadBracket();
    return NextResponse.json(bracket);
  } catch (err) {
    return NextResponse.json(
      { error: "BRACKET_LOAD_FAILED", detail: String(err) },
      { status: 500 },
    );
  }
}
