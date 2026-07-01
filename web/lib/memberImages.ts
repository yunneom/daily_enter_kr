/**
 * Member image URL map. Owner fills web/data/member_images.json (rank → URL);
 * empty string means "no explicit URL, fall back to /members/{rank}.{ext} then
 * the group-colored gradient block" (handled in components/MemberImage.tsx).
 *
 * Imported statically so it's isomorphic (bundled at build; resolveJsonModule).
 */

import raw from "@/data/member_images.json";

const MAP = raw as Record<string, string>;

/** Explicit URL for a rank, or "" when none configured. */
export function memberImageUrl(rank: number): string {
  const v = MAP[String(rank)];
  return typeof v === "string" ? v.trim() : "";
}
