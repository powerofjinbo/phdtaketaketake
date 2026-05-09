#!/usr/bin/env node
// Clean Python build artifacts before `npm pack` / `npm publish`.
//
// Why this exists: package.json's `files:` whitelist is *additive* —
// when it lists a directory like `phd_matcher`, every file under that
// directory ships, regardless of `.npmignore` or `.gitignore`. That
// silently includes `__pycache__/*.pyc` from the local dev checkout
// in the published wheel. Running `node scripts/clean_pycache.mjs`
// (auto-invoked by the npm `prepack` lifecycle) removes those
// directories from the working tree right before npm walks the file
// list, so the published package is clean.
//
// Safe by design:
//   - Only deletes well-known Python build-artifact directories.
//   - Only operates inside the package root (`process.cwd()`).
//   - No side effects on git tracking — these dirs are gitignored
//     and never tracked.

import { readdirSync, rmSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(process.cwd());

const DIR_NAMES_TO_REMOVE = new Set([
  '__pycache__',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  '.tox',
  '.coverage',
]);

const SKIP_DESCEND = new Set([
  'node_modules',
  '.git',
  '.venv',
  'venv',
]);

let removed = 0;

function walk(dir) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (SKIP_DESCEND.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (DIR_NAMES_TO_REMOVE.has(entry.name)) {
      rmSync(full, { recursive: true, force: true });
      removed++;
      continue;
    }
    walk(full);
  }
}

walk(ROOT);

if (removed > 0) {
  console.log(`prepack: cleaned ${removed} Python build-artifact dir(s)`);
}
