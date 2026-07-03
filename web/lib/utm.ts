/**
 * Lightweight UTM attribution — no external analytics script required.
 *
 * Client side: captureUtm() stores the first-touch utm_source (+ optional
 * medium/campaign) in localStorage under wc_utm; an existing entry younger
 * than 7 days is never overwritten. getUtmSource() returns the stored,
 * still-valid source for attaching to POST /api/run.
 *
 * Server side: sanitizeUtmSource() is the shared validator — only
 * [a-z0-9_-]{1,32} survives, everything else is dropped. Isomorphic file
 * (no fs / no browser access outside guarded functions).
 */

const UTM_KEY = "wc_utm";
const UTM_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

const SOURCE_RE = /^[a-z0-9_-]{1,32}$/;

export interface StoredUtm {
  source: string;
  medium?: string;
  campaign?: string;
  ts: number;
}

/** Lowercase + validate. Returns null when the value is not a safe source. */
export function sanitizeUtmSource(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const s = raw.trim().toLowerCase();
  return SOURCE_RE.test(s) ? s : null;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function readStoredUtm(): StoredUtm | null {
  try {
    const raw = window.localStorage.getItem(UTM_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredUtm>;
    if (!parsed || typeof parsed.ts !== "number") return null;
    const source = sanitizeUtmSource(parsed.source);
    if (!source) return null;
    if (Date.now() - parsed.ts > UTM_TTL_MS) return null;
    return { source, medium: parsed.medium, campaign: parsed.campaign, ts: parsed.ts };
  } catch {
    return null;
  }
}

/** Capture utm_source from the current URL (first-touch, 7-day window). */
export function captureUtm(): void {
  if (!isBrowser()) return;
  try {
    const params = new URLSearchParams(window.location.search);
    const source = sanitizeUtmSource(params.get("utm_source"));
    if (!source) return;
    // First-touch: keep an existing valid (< 7d) entry.
    if (readStoredUtm()) return;
    const entry: StoredUtm = { source, ts: Date.now() };
    const medium = params.get("utm_medium");
    const campaign = params.get("utm_campaign");
    if (medium) entry.medium = medium.slice(0, 64);
    if (campaign) entry.campaign = campaign.slice(0, 64);
    window.localStorage.setItem(UTM_KEY, JSON.stringify(entry));
  } catch {
    /* localStorage unavailable — attribution is best-effort */
  }
}

/** The stored, still-valid utm_source (or null). */
export function getUtmSource(): string | null {
  if (!isBrowser()) return null;
  return readStoredUtm()?.source ?? null;
}
