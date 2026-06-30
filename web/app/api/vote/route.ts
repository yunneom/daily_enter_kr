import { NextRequest, NextResponse } from "next/server";
import { loadBracket, getMatch } from "@/lib/bracket";
import { recordVote, tallyMatch } from "@/lib/voteStore";
import { matchStatus } from "@/lib/status";
import { sha256 } from "@/lib/hash";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface VoteBody {
  round?: string;
  quarter?: number;
  slot?: number;
  pick?: string;
  deviceId?: string;
}

export async function POST(req: NextRequest) {
  let body: VoteBody;
  try {
    body = (await req.json()) as VoteBody;
  } catch {
    return NextResponse.json({ error: "INVALID_JSON" }, { status: 400 });
  }

  const { round, quarter, slot, pick, deviceId } = body;
  if (
    typeof round !== "string" ||
    typeof quarter !== "number" ||
    typeof slot !== "number" ||
    (pick !== "a" && pick !== "b") ||
    typeof deviceId !== "string" ||
    !deviceId
  ) {
    return NextResponse.json({ error: "INVALID_PARAMS" }, { status: 400 });
  }

  const bracket = loadBracket();
  const match = getMatch(bracket, round, quarter, slot);
  if (!match) {
    return NextResponse.json({ error: "NOT_FOUND" }, { status: 404 });
  }

  const status = matchStatus(bracket, round, match);
  if (status !== "OPEN") {
    // no voting after lock / once decided
    return NextResponse.json({ error: "LOCKED", status }, { status: 423 });
  }

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const ua = req.headers.get("user-agent") ?? "unknown";

  try {
    recordVote({
      round,
      quarter,
      slot,
      pick,
      deviceId,
      ipHash: sha256(ip),
      uaHash: sha256(ua),
    });
  } catch (err) {
    if (err instanceof Error && err.message === "DUPLICATE") {
      return NextResponse.json({ error: "DUPLICATE" }, { status: 409 });
    }
    return NextResponse.json({ error: "STORE_FAILED", detail: String(err) }, { status: 500 });
  }

  const tally = tallyMatch(round, quarter, slot);
  return NextResponse.json({ tally });
}
