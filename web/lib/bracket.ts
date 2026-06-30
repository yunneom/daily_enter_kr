/**
 * Server-only bracket loader. Re-exports the isomorphic types/helpers from
 * lib/bracketTypes.ts so existing imports of "@/lib/bracket" keep working, but
 * adds the fs-backed loadBracket(). DO NOT import this from a client component
 * (it pulls in node fs) — import "@/lib/bracketTypes" there instead.
 *
 * Single source of truth: repo-root data/worldcup_bracket.json (web/ is one
 * level below). Resolve order: env BRACKET_PATH → ../data/worldcup_bracket.json.
 * fs is read at request time (no build-time caching).
 */

import fs from "fs";
import path from "path";
import type { Bracket } from "./bracketTypes";

export * from "./bracketTypes";

export function bracketPath(): string {
  const override = process.env.BRACKET_PATH;
  if (override) return override;
  // Resolve order: repo-root ../data (local dev / self-host) → cwd-local ./data
  // (Vercel build copies the file here via scripts/copy-bracket.mjs, since the
  // repo root is outside the web/ project root and is not deployed).
  const repoRoot = path.resolve(process.cwd(), "..", "data", "worldcup_bracket.json");
  if (fs.existsSync(repoRoot)) return repoRoot;
  return path.resolve(process.cwd(), "data", "worldcup_bracket.json");
}

export function loadBracket(): Bracket {
  const raw = fs.readFileSync(bracketPath(), "utf-8");
  return JSON.parse(raw) as Bracket;
}
