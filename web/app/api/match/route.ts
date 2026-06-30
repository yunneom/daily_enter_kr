import { NextRequest, NextResponse } from "next/server";
import { loadBracket, getMatch } from "@/lib/bracket";
import { tallyMatch } from "@/lib/voteStore";
import { matchStatus } from "@/lib/status";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const round = sp.get("round");
  const quarter = Number(sp.get("quarter"));
  const slot = Number(sp.get("slot"));

  if (!round || Number.isNaN(quarter) || Number.isNaN(slot)) {
    return NextResponse.json({ error: "INVALID_PARAMS" }, { status: 400 });
  }

  const bracket = loadBracket();
  const match = getMatch(bracket, round, quarter, slot);
  if (!match) {
    return NextResponse.json({ error: "NOT_FOUND" }, { status: 404 });
  }

  const tally = tallyMatch(round, quarter, slot);
  const status = matchStatus(bracket, round, match);

  return NextResponse.json({ match, tally, status });
}
