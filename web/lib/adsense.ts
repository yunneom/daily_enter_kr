/**
 * Normalizes the AdSense publisher id regardless of what format the owner
 * pastes into NEXT_PUBLIC_ADSENSE_CLIENT — "ca-pub-XXXX", "pub-XXXX", or
 * just the bare digits all resolve to the same canonical values.
 *
 * (Root cause of a past bug: env was set to "pub-XXXX", ads.txt's route did
 * `.replace(/^ca-pub-/, "")` — a no-op on "pub-" — then re-prepended "pub-",
 * producing "pub-pub-XXXX". The AdSense <script> loader and <ins
 * data-ad-client> also expect the full "ca-pub-XXXX" form, so the same
 * malformed value silently broke ad loading too, not just ads.txt.)
 */

/** → "ca-pub-XXXX" (the form the AdSense loader script / data-ad-client need), or null. */
export function normalizeAdsClient(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const digits = raw.trim().replace(/^ca-pub-/i, "").replace(/^pub-/i, "");
  if (!/^\d+$/.test(digits)) return null; // guard against garbage/partial paste
  return `ca-pub-${digits}`;
}

/** → bare numeric publisher id (the form ads.txt needs after "pub-"), or null. */
export function adsPubId(raw: string | undefined | null): string | null {
  const normalized = normalizeAdsClient(raw);
  return normalized ? normalized.replace(/^ca-pub-/, "") : null;
}
