/**
 * Admin auth helpers. The expected admin cookie value is sha256(ADMIN_PASSWORD).
 *
 * Two sha256 implementations because the code runs in two runtimes:
 *   - `sha256Edge` uses Web Crypto (crypto.subtle) — works in the edge
 *     middleware AND in node18+/route handlers.
 *   - Route handlers (node runtime) can use either; we default to the edge one
 *     so there's a single source of truth.
 *
 * Security posture: if ADMIN_PASSWORD is UNSET, admin is LOCKED (no valid
 * cookie can ever be produced), never open by default.
 */

export const ADMIN_COOKIE = "wc_admin";

/** Web Crypto sha256 → lowercase hex. Isomorphic (edge + node18+). */
export async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = new Uint8Array(digest);
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    out += bytes[i].toString(16).padStart(2, "0");
  }
  return out;
}

/** The token a valid cookie must equal, or null when admin is locked. */
export async function expectedAdminToken(): Promise<string | null> {
  const pw = process.env.ADMIN_PASSWORD;
  if (!pw) return null;
  return sha256Hex(pw);
}

/** True when the presented cookie value authorizes admin access. */
export async function isAdminCookieValid(cookieValue: string | undefined): Promise<boolean> {
  if (!cookieValue) return false;
  const expected = await expectedAdminToken();
  if (!expected) return false; // locked
  return timingSafeEqual(cookieValue, expected);
}

/** Constant-ish time string compare (both hex of same length). */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
