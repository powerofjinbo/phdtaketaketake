// Prebuild: bundle the phd_matcher Python engine + data/ into a single JSON
// the Pyodide worker can fetch and mount. Runs from frontend/ — engine lives
// at the repo root (monorepo) or in the local skill checkout (dev).
import { readdirSync, readFileSync, statSync, mkdirSync, writeFileSync, existsSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const CANDIDATE_ROOTS = [
  process.env.ENGINE_DIR,
  resolve(process.cwd(), "../.."), // repo root when frontend = repo/app/frontend
  join(homedir(), ".claude/skills/phdtaketaketake"),
].filter(Boolean);

const root = CANDIDATE_ROOTS.find((r) => existsSync(join(r, "phd_matcher")));
if (!root) {
  console.error("bundle-engine: phd_matcher not found in", CANDIDATE_ROOTS);
  process.exit(1);
}

const files = {};
function walk(dir, rel) {
  for (const name of readdirSync(dir)) {
    if (name === "__pycache__" || name.startsWith(".")) continue;
    const abs = join(dir, name);
    const r = `${rel}/${name}`;
    if (statSync(abs).isDirectory()) walk(abs, r);
    else if (/\.(py|yaml|yml|json)$/.test(name))
      files[r] = readFileSync(abs, "utf8");
  }
}
walk(join(root, "phd_matcher"), "phd_matcher");
walk(join(root, "data"), "data");

mkdirSync("public/engine", { recursive: true });
writeFileSync(
  "public/engine/bundle.json",
  JSON.stringify({ generated_from: root, files })
);
console.log(
  `bundle-engine: ${Object.keys(files).length} files from ${root} → public/engine/bundle.json`
);
