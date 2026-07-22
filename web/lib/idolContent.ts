/**
 * Original editorial content for group & member profile pages.
 *
 * Source: web/data/idol_content.json — hand-authored Korean prose (group intros,
 * member blurbs). Isomorphic static import (resolveJsonModule) so it is safe to
 * use from server components and pure helpers alike. No fs, no node builtins.
 *
 * These pages exist to give the site substantial, unique editorial content
 * (profiles, a guide) beyond the interactive voting flow.
 */

import raw from "@/data/idol_content.json";

export interface GroupContent {
  slug: string;
  name: string;
  tagline: string;
  intro: string[];
  memberRanks: number[];
}

export interface MemberContent {
  rank: number;
  member: string;
  group: string;
  groupSlug: string;
  birth?: string;
  tagline: string;
  intro: string[];
}

interface ContentFile {
  groups: GroupContent[];
  members: MemberContent[];
}

const DATA = raw as unknown as ContentFile;

export function allGroups(): GroupContent[] {
  return DATA.groups ?? [];
}

export function allMembers(): MemberContent[] {
  return DATA.members ?? [];
}

export function groupBySlug(slug: string): GroupContent | undefined {
  return (DATA.groups ?? []).find((g) => g.slug === slug);
}

export function memberByRank(rank: number): MemberContent | undefined {
  return (DATA.members ?? []).find((m) => m.rank === rank);
}

export function membersOfGroup(slug: string): MemberContent[] {
  return (DATA.members ?? [])
    .filter((m) => m.groupSlug === slug)
    .sort((a, b) => a.rank - b.rank);
}

/** "2004-08-31" → "2004년 8월 31일" (or "" if absent/malformed). */
export function formatBirth(birth?: string): string {
  if (!birth) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birth.trim());
  if (!m) return "";
  return `${m[1]}년 ${Number(m[2])}월 ${Number(m[3])}일`;
}
