/**
 * Admin round-state store at repo-root data/web_admin.json.
 *
 * Mirrors the orchestrator's already_done / window-guard philosophy: a round
 * has an explicit state and you cannot re-OPEN a round that has already been
 * ANNOUNCED (its matches have winners). No real auth in MVP — gate writes with
 * header x-admin-key === env ADMIN_KEY (default allow when ADMIN_KEY unset).
 */

import fs from "fs";
import path from "path";

export type RoundState = "OPEN" | "LOCKED" | "ANNOUNCED";

export interface RoundStateEntry {
  state: RoundState;
  untilISO?: string;
}

interface AdminFile {
  rounds: Record<string, RoundStateEntry>;
}

function adminPath(): string {
  const override = process.env.WEB_ADMIN_PATH;
  if (override) return override;
  return path.resolve(process.cwd(), "..", "data", "web_admin.json");
}

function readFile(): AdminFile {
  try {
    const raw = fs.readFileSync(adminPath(), "utf-8");
    const parsed = JSON.parse(raw) as Partial<AdminFile>;
    return { rounds: parsed.rounds ?? {} };
  } catch {
    return { rounds: {} };
  }
}

function writeFile(data: AdminFile): void {
  const p = adminPath();
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(data, null, 2), "utf-8");
}

export function getRoundStates(): Record<string, RoundStateEntry> {
  return readFile().rounds;
}

export function getRoundState(round: string): RoundStateEntry | undefined {
  return readFile().rounds[round];
}

export function setRoundState(round: string, entry: RoundStateEntry): RoundStateEntry {
  const data = readFile();
  data.rounds[round] = entry;
  writeFile(data);
  return entry;
}
