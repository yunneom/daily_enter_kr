/**
 * Client-side device id. Browser-only (uses localStorage). deviceId is a UUID
 * persisted in localStorage 'wc_device_id' and mirrored to a cookie so the
 * server can correlate it too.
 */

const DEVICE_KEY = "wc_device_id";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getDeviceId(): string {
  if (!isBrowser()) return "";
  let id = "";
  try {
    id = window.localStorage.getItem(DEVICE_KEY) ?? "";
  } catch {
    /* storage blocked */
  }
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `dev_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
    try {
      window.localStorage.setItem(DEVICE_KEY, id);
    } catch {
      /* ignore */
    }
  }
  try {
    document.cookie = `${DEVICE_KEY}=${id}; path=/; max-age=31536000; samesite=lax`;
  } catch {
    /* ignore */
  }
  return id;
}
