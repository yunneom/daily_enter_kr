import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";
import { assertSafeCopy, SOURCE_ATTRIBUTION } from "@/lib/safety";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const member = sp.get("member") ?? "";
  const group = sp.get("group") ?? "";
  const pctRaw = sp.get("pct") ?? "";

  // Brand-safety gate: any dynamic text must pass; on violation fall back.
  let safeMember = "";
  let safeGroup = "";
  try {
    assertSafeCopy(member);
    assertSafeCopy(group);
    safeMember = member;
    safeGroup = group;
  } catch {
    safeMember = "";
    safeGroup = "";
  }

  const pctNum = Number(pctRaw);
  const pctLabel = Number.isFinite(pctNum) && pctNum > 0 ? `${Math.round(pctNum)}%` : "";

  const title = safeMember
    ? `${safeMember}${safeGroup ? ` · ${safeGroup}` : ""}`
    : "걸그룹 월드컵";

  return new ImageResponse(
    (
      <div
        style={{
          width: "1080px",
          height: "1080px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#111111",
          color: "#ffffff",
          fontFamily: "sans-serif",
          padding: "80px",
        }}
      >
        <div style={{ fontSize: 44, color: "#bbbbbb", marginBottom: 24 }}>걸그룹 월드컵</div>
        <div style={{ fontSize: 96, fontWeight: 700, textAlign: "center", lineHeight: 1.2 }}>
          {title}
        </div>
        {pctLabel ? (
          <div style={{ fontSize: 120, fontWeight: 800, marginTop: 40, color: "#ffffff" }}>
            {pctLabel}
          </div>
        ) : null}
        <div style={{ fontSize: 32, color: "#888888", marginTop: 60 }}>
          {`출처 ${SOURCE_ATTRIBUTION}`}
        </div>
      </div>
    ),
    { width: 1080, height: 1080 },
  );
}
