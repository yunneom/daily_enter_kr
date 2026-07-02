"use client";

import { useMemo, useState } from "react";
import { memberImageUrl } from "@/lib/memberImages";
import { groupColor, groupGradient } from "@/lib/colors";

interface Props {
  rank: number;
  group: string;
  member: string;
  /** rendered edge length hint; also drives font sizing of the fallback */
  size?: number;
  className?: string;
  rounded?: boolean;
  /** avatar mode: gradient fallback shows only the big initial (name comes from the caption) */
  compact?: boolean;
  /** load immediately (current duel) instead of lazy */
  eager?: boolean;
}

/**
 * Resolves a member photo through a fallback chain using a plain <img> +
 * onError (simplest reliable approach — no next/image domain config needed):
 *   1. explicit URL from data/member_images.json (if non-empty)
 *   2. /members/{rank}.jpg → .png → .webp (public/)
 *   3. group-colored gradient block with centered name (+ group tag + initial)
 *
 * When the whole chain fails we render the gradient fallback (no <img>).
 */
export default function MemberImage({
  rank,
  group,
  member,
  size = 240,
  className,
  rounded = false,
  compact = false,
  eager = false,
}: Props) {
  // Build the ordered source candidates once.
  const sources = useMemo(() => {
    const list: string[] = [];
    const explicit = memberImageUrl(rank);
    if (explicit) list.push(explicit);
    list.push(`/members/${rank}.jpg`, `/members/${rank}.png`, `/members/${rank}.webp`);
    return list;
  }, [rank]);

  const [idx, setIdx] = useState(0);
  const exhausted = idx >= sources.length;

  const color = groupColor(group);
  const initial = member.slice(0, 1);

  if (exhausted) {
    return (
      <div
        className={`member-fallback ${rounded ? "rounded" : ""} ${className ?? ""}`}
        style={{
          background: groupGradient(group),
          // scale text roughly to the box
          ["--mi-size" as string]: `${size}px`,
        }}
        aria-label={`${member} ${group}`}
      >
        <span className={`member-fallback-initial ${compact ? "solo" : ""}`} aria-hidden>
          {initial}
        </span>
        {compact ? null : (
          <>
            <span className="member-fallback-name">{member}</span>
            <span className="member-fallback-group" style={{ color }}>
              {group}
            </span>
          </>
        )}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={sources[idx]}
      alt={`${member} ${group}`}
      width={size}
      height={size}
      className={`member-img ${rounded ? "rounded" : ""} ${className ?? ""}`}
      onError={() => setIdx((i) => i + 1)}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={eager ? "high" : "auto"}
      decoding="async"
    />
  );
}
