import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";
import { assertSafeCopy, SOURCE_ATTRIBUTION } from "@/lib/safety";
import { groupColor } from "@/lib/colors";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * OG champion/pick card. Query: member, group, pct (all optional).
 * Any dynamic text is brand-safety gated; on violation it falls back to a
 * neutral title so we never render banned copy.
 */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const member = sp.get("member") ?? "";
  const group = sp.get("group") ?? "";
  const pctRaw = sp.get("pct") ?? "";

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

  const title = safeMember ? safeMember : "이상형 월드컵";
  const accent = safeGroup ? groupColor(safeGroup) : "#7c3aed";

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
          background: `linear-gradient(160deg, #0b0b12 0%, #16121f 100%)`,
          color: "#ffffff",
          fontFamily: "sans-serif",
          padding: "80px",
        }}
      >
        <div style={{ fontSize: 44, color: accent, marginBottom: 24, fontWeight: 700 }}>
          이상형 월드컵 우승
        </div>
        <div style={{ fontSize: 120, fontWeight: 800, textAlign: "center", lineHeight: 1.15 }}>
          {title}
        </div>
        {safeGroup ? (
          <div style={{ fontSize: 46, color: "#c9c9d6", marginTop: 18 }}>{safeGroup}</div>
        ) : null}
        {pctLabel ? (
          <div style={{ fontSize: 96, fontWeight: 800, marginTop: 36, color: accent }}>
            {pctLabel}
          </div>
        ) : null}
        <div style={{ fontSize: 30, color: "#7d7d8c", marginTop: 60 }}>
          {`출처 ${SOURCE_ATTRIBUTION}`}
        </div>
      </div>
    ),
    { width: 1080, height: 1080 },
  );
}
