// Prebuild: self-host the Pyodide runtime + the wheels the engine needs.
// Serving these from our own origin (instead of a third-party CDN) makes the
// app work on restricted networks and keeps zero runtime dependencies.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const pkgDir = join(here, "..", "node_modules", "pyodide");
const outDir = join(here, "..", "public", "pyodide");
mkdirSync(outDir, { recursive: true });

if (!existsSync(pkgDir)) {
  console.error("fetch-pyodide: pyodide npm package not installed");
  process.exit(1);
}

// Core runtime files ship inside the npm package — copy them.
const CORE = [
  "pyodide.js",
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
];
for (const f of CORE) {
  const src = join(pkgDir, f);
  if (!existsSync(src)) {
    console.error(`fetch-pyodide: missing core file in npm package: ${f}`);
    process.exit(1);
  }
  copyFileSync(src, join(outDir, f));
}

// The engine's wheel closure (verified by running phd_matcher in Pyodide):
const WHEEL_PKGS = [
  "pydantic",
  "pydantic_core",
  "pyyaml",
  "typing-extensions",
  "typing_extensions",
  "annotated-types",
  "annotated_types",
  "typing-inspection",
  "typing_inspection",
];
const lock = JSON.parse(readFileSync(join(pkgDir, "pyodide-lock.json"), "utf8"));
const version = JSON.parse(
  readFileSync(join(pkgDir, "package.json"), "utf8")
).version;

const wanted = new Map();
for (const [name, info] of Object.entries(lock.packages || {})) {
  if (WHEEL_PKGS.includes(name) || WHEEL_PKGS.includes(name.replace(/-/g, "_")))
    wanted.set(info.file_name, name);
}
if (wanted.size < 6) {
  console.error(
    `fetch-pyodide: expected ≥6 wheels in lock, found ${wanted.size}:`,
    [...wanted.values()]
  );
  process.exit(1);
}

let downloaded = 0;
for (const [file] of wanted) {
  const dst = join(outDir, file);
  if (existsSync(dst)) continue;
  const local = join(pkgDir, file); // our node test may have cached it
  if (existsSync(local)) {
    copyFileSync(local, dst);
    downloaded++;
    continue;
  }
  const url = `https://cdn.jsdelivr.net/pyodide/v${version}/full/${file}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    console.error(`fetch-pyodide: download failed ${url}: ${resp.status}`);
    process.exit(1);
  }
  writeFileSync(dst, Buffer.from(await resp.arrayBuffer()));
  downloaded++;
}
console.log(
  `fetch-pyodide: v${version} core (${CORE.length} files) + ${wanted.size} wheels ready (${downloaded} fetched) → public/pyodide/`
);
