import { NextResponse } from "next/server";
import { getResults } from "@/lib/runStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const results = await getResults();
    return NextResponse.json(results);
  } catch (err) {
    return NextResponse.json(
      { error: "RESULTS_FAILED", detail: String(err) },
      { status: 500 },
    );
  }
}
