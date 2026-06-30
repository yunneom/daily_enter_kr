// Build-time snapshot: copy the repo-root single source of truth
// (../data/worldcup_bracket.json) into web/data/ so a Vercel deploy whose
// Root Directory is "web" can still read it (the repo root is outside the
// project root and is not bundled). Each commit to bracket.json triggers a
// Vercel redeploy, so this snapshot stays fresh. Live vote tallies come from
// the vote store (lib/voteStore.ts), not from this file.
import fs from "node:fs";
import path from "node:path";

const src = path.resolve(process.cwd(), "..", "data", "worldcup_bracket.json");
const destDir = path.resolve(process.cwd(), "data");
const dest = path.join(destDir, "worldcup_bracket.json");

if (!fs.existsSync(src)) {
  console.warn(`[copy-bracket] source not found at ${src} — skipping (using existing ${dest} if present)`);
  process.exit(0);
}
fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(src, dest);
console.log(`[copy-bracket] ${src} -> ${dest}`);
