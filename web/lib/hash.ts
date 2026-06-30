import crypto from "crypto";

/** Simple sha256 hex digest, truncated, for non-reversible ip/ua fingerprints. */
export function sha256(value: string): string {
  return crypto.createHash("sha256").update(value).digest("hex").slice(0, 32);
}
