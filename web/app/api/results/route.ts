import { NextResponse } from "next/server";
import { getResults } from "@/lib/runStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const results = await getResults();
    // Short shared cache: Vercel's edge serves polling traffic for 3s per
    // region instead of hitting KV on every request. Clients still see
    // near-realtime numbers (poll interval is 5s).
    return NextResponse.json(results, {
      headers: {
        "Cache-Control": "public, s-maxage=3, stale-while-revalidate=10",
      },
    });
  } catch (err) {
    return NextResponse.json(
      { error: "RESULTS_FAILED", detail: String(err) },
      { status: 500 },
    );
  }
}
