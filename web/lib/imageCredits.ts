/**
 * Image attribution for member photos sourced from Wikimedia Commons.
 *
 * Every photo shown on the site comes from Wikimedia Commons (freely licensed);
 * Commons' licenses (mostly CC BY / CC BY-SA) require attribution, so we derive
 * a link back to each file's Commons description page (where author + license
 * are listed) and surface them all on /credits.
 *
 * member_images.json stores URLs in the form
 *   https://commons.wikimedia.org/wiki/Special:FilePath/<FileName>?width=400
 * from which we recover <FileName> and build the /wiki/File:<FileName> page.
 *
 * Isomorphic (no fs) — safe to import from server components.
 */

import raw from "@/data/member_images.json";
import { allMembers } from "@/lib/idolContent";

const MAP = raw as Record<string, string>;

export interface ImageCredit {
  rank: number;
  member: string;
  group: string;
  fileName: string;
  filePageUrl: string;
}

function fileNameFromUrl(url: string): string | null {
  const m = /Special:FilePath\/([^?]+)/.exec(url);
  if (!m) return null;
  try {
    return decodeURIComponent(m[1]);
  } catch {
    return m[1];
  }
}

/** All Wikimedia Commons-sourced photos, with a link to each file's description page. */
export function imageCredits(): ImageCredit[] {
  const byRank = new Map(allMembers().map((m) => [m.rank, m]));
  const out: ImageCredit[] = [];
  for (const [rankStr, url] of Object.entries(MAP)) {
    const u = (url || "").trim();
    if (!u.includes("commons.wikimedia.org")) continue;
    const fileName = fileNameFromUrl(u);
    if (!fileName) continue;
    const rank = Number.parseInt(rankStr, 10);
    const m = byRank.get(rank);
    if (!m) continue;
    out.push({
      rank,
      member: m.member,
      group: m.group,
      fileName,
      filePageUrl: `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(fileName)}`,
    });
  }
  return out.sort((a, b) => a.rank - b.rank);
}
