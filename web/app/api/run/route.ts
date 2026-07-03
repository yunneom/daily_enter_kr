import { NextRequest, NextResponse } from "next/server";
import { submitRun, type RunPick } from "@/lib/runStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface Body {
  deviceId?: string;
  championRank?: number;
  picks?: RunPick[];
  /** optional first-touch utm_source; sanitized in runStore before counting */
  utm?: string;
}

export async function POST(req: NextRequest) {
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ error: "INVALID_JSON" }, { status: 400 });
  }

  const { deviceId, championRank, picks, utm } = body;
  if (
    typeof deviceId !== "string" ||
    !deviceId ||
    typeof championRank !== "number" ||
    !Array.isArray(picks)
  ) {
    return NextResponse.json({ error: "INVALID_PARAMS" }, { status: 400 });
  }

  try {
    const result = await submitRun({
      deviceId,
      championRank,
      picks,
      utm: typeof utm === "string" ? utm : null,
    });
    return NextResponse.json(result);
  } catch (err) {
    if (err instanceof Error && err.message === "INVALID_RUN") {
      return NextResponse.json({ error: "INVALID_RUN" }, { status: 400 });
    }
    return NextResponse.json({ error: "STORE_FAILED", detail: String(err) }, { status: 500 });
  }
}
