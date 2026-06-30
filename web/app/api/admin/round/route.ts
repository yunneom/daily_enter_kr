import { NextRequest, NextResponse } from "next/server";
import { loadBracket, listMatches } from "@/lib/bracket";
import { getRoundStates, setRoundState, type RoundState } from "@/lib/adminStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// MVP auth: header x-admin-key must equal env ADMIN_KEY. If ADMIN_KEY is unset
// (dev), allow all. This mirrors the orchestrator already_done / window-guard
// philosophy — gate state transitions, but no full auth in MVP.
function authorized(req: NextRequest): boolean {
  const expected = process.env.ADMIN_KEY;
  if (!expected) return true;
  return req.headers.get("x-admin-key") === expected;
}

/** Default state for a round derived from the bracket. */
function defaultState(round: string, currentRound: string, hasWinner: boolean): RoundState {
  if (hasWinner) return "ANNOUNCED";
  if (round === currentRound) return "OPEN";
  return "LOCKED";
}

export async function GET() {
  const bracket = loadBracket();
  const overrides = getRoundStates();
  const rounds: Record<string, { state: RoundState; untilISO?: string; source: string }> = {};

  for (const round of Object.keys(bracket.rounds)) {
    const matches = listMatches(bracket, round);
    const hasWinner = matches.length > 0 && matches.every((m) => m.winner !== null);
    const override = overrides[round];
    if (override) {
      rounds[round] = { state: override.state, untilISO: override.untilISO, source: "admin" };
    } else {
      rounds[round] = {
        state: defaultState(round, bracket.current_round, hasWinner),
        source: "derived",
      };
    }
  }

  return NextResponse.json({ current_round: bracket.current_round, rounds });
}

interface PostBody {
  round?: string;
  action?: "open" | "lock" | "extend";
  untilISO?: string;
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "UNAUTHORIZED" }, { status: 401 });
  }

  let body: PostBody;
  try {
    body = (await req.json()) as PostBody;
  } catch {
    return NextResponse.json({ error: "INVALID_JSON" }, { status: 400 });
  }

  const { round, action, untilISO } = body;
  if (!round || (action !== "open" && action !== "lock" && action !== "extend")) {
    return NextResponse.json({ error: "INVALID_PARAMS" }, { status: 400 });
  }

  const bracket = loadBracket();
  if (!bracket.rounds[round]) {
    return NextResponse.json({ error: "NOT_FOUND" }, { status: 404 });
  }

  const matches = listMatches(bracket, round);
  const announced = matches.length > 0 && matches.every((m) => m.winner !== null);

  // State-machine guard: cannot OPEN a round already ANNOUNCED.
  if (action === "open" && announced) {
    return NextResponse.json(
      { error: "ALREADY_ANNOUNCED", detail: "이미 결과가 발표된 라운드는 다시 열 수 없습니다." },
      { status: 409 },
    );
  }

  let state: RoundState;
  if (action === "open") state = "OPEN";
  else if (action === "lock") state = "LOCKED";
  else state = "OPEN"; // extend keeps it open, just updates the window

  const entry = setRoundState(round, { state, untilISO });
  return NextResponse.json({ round, ...entry });
}
