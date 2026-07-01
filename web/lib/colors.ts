/**
 * Group color palette. A distinct strong color per group so member cards and
 * the roster preview are visually distinguishable even before real photos are
 * added. Any group not listed falls back to DEFAULT_GROUP_COLOR.
 *
 * Isomorphic (no fs / no node builtins) — safe to import from client & server.
 */

export const GROUP_COLORS: Record<string, string> = {
  아이브: "#2563eb",
  에스파: "#7c3aed",
  블랙핑크: "#db2777",
  소녀시대: "#d97706",
  엔믹스: "#059669",
  뉴진스: "#0891b2",
  르세라핌: "#dc2626",
  아일릿: "#ea580c",
  트와이스: "#e11d48",
  레드벨벳: "#be123c",
  아이들: "#7e22ce",
  시그니처: "#0d9488",
  프로미스나인: "#4f46e5",
  케플러: "#0284c7",
  // groups present in the current bracket without a dedicated palette entry
  // still resolve via DEFAULT_GROUP_COLOR below, but give a couple stable ones:
  다이아: "#9333ea",
  리센느: "#0ea5e9",
  우주소녀: "#c026d3",
  위키미키: "#f59e0b",
};

export const DEFAULT_GROUP_COLOR = "#6b7280";

export function groupColor(group: string): string {
  return GROUP_COLORS[group] ?? DEFAULT_GROUP_COLOR;
}

/**
 * A soft 2-stop gradient derived from the group color, for panel/card
 * backgrounds. Returns a CSS linear-gradient string.
 */
export function groupGradient(group: string): string {
  const base = groupColor(group);
  return `linear-gradient(160deg, ${base} 0%, ${shade(base, -28)} 100%)`;
}

/** Darken/lighten a hex color by pct (-100..100). Pure, no deps. */
export function shade(hex: string, pct: number): string {
  const m = hex.replace("#", "");
  const num = parseInt(m.length === 3 ? m.split("").map((c) => c + c).join("") : m, 16);
  const r = (num >> 16) & 0xff;
  const g = (num >> 8) & 0xff;
  const b = num & 0xff;
  const adj = (c: number) => {
    const v = Math.round(c + (pct / 100) * (pct < 0 ? c : 255 - c));
    return Math.max(0, Math.min(255, v));
  };
  const rr = adj(r).toString(16).padStart(2, "0");
  const gg = adj(g).toString(16).padStart(2, "0");
  const bb = adj(b).toString(16).padStart(2, "0");
  return `#${rr}${gg}${bb}`;
}
