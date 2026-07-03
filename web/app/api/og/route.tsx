import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";
import { assertSafeCopy, SOURCE_ATTRIBUTION } from "@/lib/safety";
import { groupColor } from "@/lib/colors";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * OG champion/pick card. Query: member, group, pct (all optional).
 * ?mode=recap renders the gold "우승" recap variant instead.
 * Any dynamic text is brand-safety gated; on violation it falls back to a
 * neutral title so we never render banned copy.
 */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const mode = sp.get("mode") ?? "";
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

  if (mode === "recap") {
    return recapCard(safeMember, safeGroup, pctLabel);
  }

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

/**
 * Recap variant — gold "우승" styling. Crown drawn with inline SVG (CSS/SVG
 * only, no emoji). Copy already passed the safety gate upstream.
 */
function recapCard(member: string, group: string, pctLabel: string) {
  const gold = "#fbbf24";
  const title = member ? member : "우승 리캡";
  const accent = group ? groupColor(group) : gold;

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
          background: "linear-gradient(160deg, #0b0b12 0%, #1c1730 60%, #16121f 100%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
          padding: "80px",
        }}
      >
        {/* crown */}
        <svg width="150" height="104" viewBox="0 0 150 104">
          <path
            d="M14 96 L14 34 L50 62 L75 14 L100 62 L136 34 L136 96 Z"
            fill={gold}
          />
          <rect x="14" y="86" width="122" height="10" fill="#d97706" />
        </svg>
        <div
          style={{
            fontSize: 40,
            color: gold,
            marginTop: 28,
            fontWeight: 700,
            letterSpacing: 10,
            display: "flex",
          }}
        >
          우승
        </div>
        <div
          style={{
            width: 220,
            height: 4,
            background: gold,
            borderRadius: 4,
            marginTop: 26,
            marginBottom: 34,
            display: "flex",
          }}
        />
        <div style={{ fontSize: 118, fontWeight: 800, textAlign: "center", lineHeight: 1.12 }}>
          {title}
        </div>
        {group ? (
          <div style={{ fontSize: 46, color: accent, marginTop: 18, fontWeight: 700 }}>{group}</div>
        ) : null}
        {pctLabel ? (
          <div style={{ fontSize: 84, fontWeight: 800, marginTop: 34, color: gold }}>
            {`우승 픽 ${pctLabel}`}
          </div>
        ) : null}
        <div style={{ fontSize: 34, color: "#c9c9d6", marginTop: 48 }}>
          걸그룹 이상형 월드컵 리캡
        </div>
        <div style={{ fontSize: 28, color: "#7d7d8c", marginTop: 20 }}>
          {`dailyenterkr.com · 출처 ${SOURCE_ATTRIBUTION}`}
        </div>
      </div>
    ),
    { width: 1080, height: 1080 },
  );
}
