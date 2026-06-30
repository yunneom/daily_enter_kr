/**
 * Client-side device + voted-key helpers. Browser-only (uses localStorage).
 * deviceId is a UUID persisted in localStorage 'wc_device_id' and mirrored to
 * a cookie so the server can read it too.
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
  // mirror to cookie (1 year) for server-side correlation
  try {
    document.cookie = `${DEVICE_KEY}=${id}; path=/; max-age=31536000; samesite=lax`;
  } catch {
    /* ignore */
  }
  return id;
}

function votedStorageKey(round: string): string {
  return `wc_voted_${round}`;
}

export function getVotedKeys(round: string): Set<string> {
  if (!isBrowser()) return new Set();
  try {
    const raw = window.localStorage.getItem(votedStorageKey(round));
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as unknown;
    if (Array.isArray(arr)) return new Set(arr.filter((x): x is string => typeof x === "string"));
  } catch {
    /* ignore */
  }
  return new Set();
}

export function addVotedKey(round: string, quarter: number, slot: number): void {
  if (!isBrowser()) return;
  const set = getVotedKeys(round);
  set.add(`${quarter}-${slot}`);
  try {
    window.localStorage.setItem(votedStorageKey(round), JSON.stringify([...set]));
  } catch {
    /* ignore */
  }
}
