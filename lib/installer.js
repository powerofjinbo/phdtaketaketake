// phdtaketaketake installer (Node ≥ 20, ESM, zero runtime deps).
//
// Public surface (stable for tests / future hosts):
//   run(argv)                                       — CLI dispatch
//   installClaude({ packageRoot, env, console })    — Claude Code host
//   installCodex({ packageRoot, env, console, ... })   — added in c4
//   installCursor({ packageRoot, projectDir, ... }) — added in c5
//   doctor({ packageRoot, env, console })           — environment health check
//   detectClaudeCli({ env })
//   readVersionFromPackageJson(packageRoot)
//   readVersionFromPluginJson(packageRoot)
//   readVersionFromPyproject(packageRoot)
//
// Design rules locked by the distribution-compliance patchset SCOPE GUARD:
//   - No `postinstall` hook in package.json. Installation requires the
//     user to explicitly run `phdtake install --<host>`.
//   - No `pip install` from this script. We print the recommended pip
//     command; the user runs it in the Python environment they want.
//   - No silent host-config writes. Either we use the host's official
//     install command (`claude plugin marketplace add` / `claude plugin
//     install`), or we print explicit instructions. `--manual-copy` opts
//     into the local-copy fallback explicitly.
//   - No npm publish from inside this script.

import { spawnSync } from 'node:child_process';
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Resolve the npm package root (where package.json lives). */
export const PACKAGE_ROOT = resolve(__dirname, '..');

/** Files / dirs that must never be copied into a host install location. */
const COPY_EXCLUDE = new Set([
  '.git',
  '.github',
  '.github_workflows', // legacy; should be gone but defended-against
  'node_modules',
  'dist',
  'build',
  '__pycache__',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  '.tox',
  '.venv',
  'venv',
  '.DS_Store',
  '.cache',
  '.coverage',
  '.idea',
  '.vscode',
  '.claude', // host install dir; never recurse into it from a source tree
  '.codex',
  '.agents',
  '.cursor',
]);

// -- CLI dispatch ---------------------------------------------------------

const HELP_TEXT = `phdtake — installer for the phdtaketaketake skill

Usage:
  phdtake install --claude              install for Claude Code
  phdtake install --codex               install for OpenAI Codex
  phdtake install --cursor --project .  install Cursor project rule
  phdtake install --all                 install for every detected host
  phdtake install <host> --manual-copy  use the manual-copy fallback for
                                        hosts where we can't reach a CLI
  phdtake doctor                        check Node / Python / claude CLI
                                        / manifest / version-sync health

Notes:
  - We never run \`pip install\` for you. The Python CLIs in pyproject.toml
    install separately; \`phdtake doctor\` prints the recommended command.
  - We never run \`npm publish\`. Distribution maintainers run that
    explicitly.
  - For Claude Code we prefer \`claude plugin marketplace add\` +
    \`claude plugin install\`; --manual-copy is a fallback only.
`;

export async function run(argv, deps = {}) {
  const out = deps.console || console;
  const env = deps.env || process.env;
  const packageRoot = deps.packageRoot || PACKAGE_ROOT;

  const cmd = argv[0];
  if (!cmd || cmd === '--help' || cmd === '-h' || cmd === 'help') {
    out.log(HELP_TEXT);
    return 0;
  }
  if (cmd === '--version' || cmd === '-v') {
    const v = readVersionFromPackageJson(packageRoot);
    out.log(v);
    return 0;
  }
  if (cmd === 'install') {
    return installCmd(argv.slice(1), { packageRoot, env, console: out });
  }
  if (cmd === 'doctor') {
    return doctor({ packageRoot, env, console: out });
  }
  out.error(`Unknown command: ${cmd}\n`);
  out.error(HELP_TEXT);
  return 2;
}

function parseInstallFlags(args) {
  const flags = {
    claude: false,
    codex: false,
    cursor: false,
    all: false,
    manualCopy: false,
    projectDir: null,
  };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--claude') flags.claude = true;
    else if (a === '--codex') flags.codex = true;
    else if (a === '--cursor') flags.cursor = true;
    else if (a === '--all') flags.all = true;
    else if (a === '--manual-copy') flags.manualCopy = true;
    else if (a === '--project') {
      flags.projectDir = args[++i];
    } else if (a.startsWith('--project=')) {
      flags.projectDir = a.slice('--project='.length);
    } else {
      throw new Error(
        `Unknown install flag: ${a}\nSupported: --claude --codex --cursor --all --manual-copy --project <path>`,
      );
    }
  }
  return flags;
}

async function installCmd(args, { packageRoot, env, console: out }) {
  const flags = parseInstallFlags(args);
  if (!flags.claude && !flags.codex && !flags.cursor && !flags.all) {
    out.error('Specify at least one host: --claude / --codex / --cursor / --all\n');
    out.error(HELP_TEXT);
    return 2;
  }

  const targets = flags.all
    ? ['claude', 'codex', 'cursor']
    : [
        flags.claude && 'claude',
        flags.codex && 'codex',
        flags.cursor && 'cursor',
      ].filter(Boolean);

  let hadError = false;
  for (const target of targets) {
    out.log(`\n--- Installing for ${target} ---`);
    let code = 0;
    if (target === 'claude') {
      code = await installClaude({
        packageRoot,
        env,
        console: out,
        manualCopy: flags.manualCopy,
      });
    } else if (target === 'codex') {
      code = await installCodex({
        packageRoot,
        env,
        console: out,
        projectDir: flags.projectDir,
      });
    } else if (target === 'cursor') {
      code = await installCursor({
        packageRoot,
        env,
        console: out,
        projectDir: flags.projectDir,
      });
    }
    if (code !== 0) hadError = true;
  }
  return hadError ? 1 : 0;
}

// -- Claude installer -----------------------------------------------------

/** Detect the `claude` CLI on PATH. Returns the resolved path or null. */
export function detectClaudeCli({ env, runner } = {}) {
  const run = runner || ((cmd, args) => spawnSync(cmd, args, { env }));
  const result = run('which', ['claude']);
  if (result.status === 0 && result.stdout) {
    return result.stdout.toString().trim() || null;
  }
  return null;
}

/**
 * Install for Claude Code.
 *
 * Default path: detect `claude` CLI; if found, run
 *   claude plugin marketplace add <packageRoot>
 *   claude plugin install phdtaketaketake@powerofjinbo
 * If `claude` is absent OR `--manual-copy` was passed, fall back to
 * copying the package into ~/.claude/plugins/local/phdtaketaketake/
 * (with a backup of any existing dir).
 */
export async function installClaude({
  packageRoot,
  env = process.env,
  console: out = console,
  manualCopy = false,
  runner,
} = {}) {
  if (!packageRoot) packageRoot = PACKAGE_ROOT;
  const run = runner || ((cmd, args, opts) => spawnSync(cmd, args, { env, ...opts }));

  const claudeCli = manualCopy ? null : detectClaudeCli({ env, runner });

  if (claudeCli) {
    out.log(`Found claude CLI at ${claudeCli}`);
    out.log('Running: claude plugin marketplace add <package-root>');
    const addRes = run(
      claudeCli,
      ['plugin', 'marketplace', 'add', packageRoot],
      { stdio: 'inherit' },
    );
    if (addRes.status !== 0) {
      out.warn('  marketplace add returned non-zero; continuing with install attempt');
    }
    out.log('Running: claude plugin install phdtaketaketake@powerofjinbo');
    const installRes = run(
      claudeCli,
      ['plugin', 'install', 'phdtaketaketake@powerofjinbo'],
      { stdio: 'inherit' },
    );
    if (installRes.status === 0) {
      out.log('\n✓ Claude Code plugin installed.');
      printPythonCliNote(out);
      return 0;
    }
    out.warn('  claude plugin install returned non-zero. Falling back to printing manual instructions.');
  }

  // Fallback path: print the canonical slash commands the user can run
  // inside Claude Code, plus the --manual-copy escape hatch.
  if (!manualCopy) {
    out.log('claude CLI not detected on PATH (or invocation failed).');
    out.log('');
    out.log('Inside a Claude Code session, run:');
    out.log(`  /plugin marketplace add ${packageRoot}`);
    out.log('  /plugin install phdtaketaketake@powerofjinbo');
    out.log('');
    out.log('Or re-run this installer with --manual-copy to copy the');
    out.log('package directly into ~/.claude/plugins/local/phdtaketaketake/.');
    printPythonCliNote(out);
    return 0;
  }

  // --manual-copy: explicit local-copy fallback.
  const claudeHome = env.CLAUDE_HOME || join(homedir(), '.claude');
  const dest = join(claudeHome, 'plugins', 'local', 'phdtaketaketake');
  const backedUp = backupIfExists(dest);
  if (backedUp) {
    out.log(`Backed up existing install: ${backedUp}`);
  }
  copyPackage(packageRoot, dest);
  out.log(`✓ Copied package → ${dest}`);
  printPythonCliNote(out, dest);
  return 0;
}

// -- Codex / Cursor installers (stubs filled in by c4 / c5) ---------------

export async function installCodex({ console: out = console } = {}) {
  out.log('Codex installer arrives in the next commit of this patchset.');
  return 0;
}

export async function installCursor({ console: out = console } = {}) {
  out.log('Cursor installer arrives in the next commit of this patchset.');
  return 0;
}

// -- Doctor: environment health check ------------------------------------

/**
 * Check the install environment.
 *   - Node ≥ 20
 *   - Python on PATH (any version; we don't enforce a minimum here —
 *     pyproject.toml requires-python="...>=3.11" handles that on pip install)
 *   - claude CLI presence
 *   - plugin.json + marketplace.json parse cleanly
 *   - package.json / pyproject.toml / plugin.json versions match
 *
 * Returns 0 if all checks pass, 1 if any non-fatal warnings, 2 if a hard
 * failure (e.g. malformed JSON manifest).
 */
export async function doctor({
  packageRoot,
  env = process.env,
  console: out = console,
  runner,
} = {}) {
  if (!packageRoot) packageRoot = PACKAGE_ROOT;
  const run = runner || ((cmd, args) => spawnSync(cmd, args, { env }));

  let warnCount = 0;
  let errCount = 0;
  const ok = (msg) => out.log(`  ✓ ${msg}`);
  const warn = (msg) => {
    warnCount++;
    out.log(`  ! ${msg}`);
  };
  const err = (msg) => {
    errCount++;
    out.log(`  ✗ ${msg}`);
  };

  out.log('phdtake doctor — install-environment health check\n');

  // Node version
  const major = Number(process.versions.node.split('.')[0]);
  if (major >= 20) ok(`Node ${process.versions.node} (≥ 20 required)`);
  else err(`Node ${process.versions.node} is < 20; please upgrade`);

  // Python availability
  const pyRes = run('python3', ['--version']);
  if (pyRes.status === 0) {
    ok(`python3: ${(pyRes.stdout || pyRes.stderr).toString().trim()}`);
  } else {
    warn('python3 not found on PATH (pip-installed CLIs phdtaketaketake-* will be unavailable until you install Python 3.11+)');
  }

  // claude CLI
  const claudePath = detectClaudeCli({ env, runner });
  if (claudePath) ok(`claude CLI: ${claudePath}`);
  else warn('claude CLI not on PATH (npx phdtake install --claude will fall back to printing manual instructions)');

  // Manifests
  let pluginVersion = null;
  let marketplaceOk = false;
  try {
    pluginVersion = readVersionFromPluginJson(packageRoot);
    ok('.claude-plugin/plugin.json parses cleanly');
  } catch (e) {
    err(`.claude-plugin/plugin.json: ${e.message}`);
  }
  try {
    const m = JSON.parse(readFileSync(join(packageRoot, '.claude-plugin', 'marketplace.json'), 'utf8'));
    if (Array.isArray(m.plugins) && m.plugins.length > 0) {
      ok(`.claude-plugin/marketplace.json parses cleanly (${m.plugins.length} plugin entry/entries)`);
      marketplaceOk = true;
    } else {
      warn('.claude-plugin/marketplace.json: no plugins listed');
    }
  } catch (e) {
    err(`.claude-plugin/marketplace.json: ${e.message}`);
  }

  // Version sync
  const pkgVersion = readVersionFromPackageJson(packageRoot);
  const pyVersion = readVersionFromPyproject(packageRoot);
  const allMatch = pkgVersion && pluginVersion && pyVersion
    && pkgVersion === pluginVersion && pluginVersion === pyVersion;
  if (allMatch) {
    ok(`version sync: package.json / plugin.json / pyproject.toml all at ${pkgVersion}`);
  } else {
    warn(
      `version drift: package.json=${pkgVersion} plugin.json=${pluginVersion} pyproject.toml=${pyVersion}`,
    );
  }

  // SKILL.md sanity
  if (existsSync(join(packageRoot, 'SKILL.md'))) ok('SKILL.md present at package root');
  else err('SKILL.md missing at package root');

  out.log('');
  if (errCount > 0) {
    out.log(`✗ ${errCount} error(s), ${warnCount} warning(s).`);
    return 2;
  }
  if (warnCount > 0) {
    out.log(`! ${warnCount} warning(s) — install will work, but some hosts may need manual setup.`);
    return 1;
  }
  out.log('✓ All checks passed.');
  // Suppress mention here — we already printed everything above.
  return 0;
}

// -- Version readers (used by doctor + tests) -----------------------------

export function readVersionFromPackageJson(packageRoot) {
  const p = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
  return p.version || null;
}

export function readVersionFromPluginJson(packageRoot) {
  const p = JSON.parse(readFileSync(join(packageRoot, '.claude-plugin', 'plugin.json'), 'utf8'));
  return p.version || null;
}

export function readVersionFromPyproject(packageRoot) {
  // Minimal TOML parsing: scan for `version = "..."` inside [project].
  // We deliberately avoid a TOML parser dep; the field is always quoted.
  const text = readFileSync(join(packageRoot, 'pyproject.toml'), 'utf8');
  const projectMatch = text.match(/\[project\]([\s\S]*?)(?=\n\[|$)/);
  const block = projectMatch ? projectMatch[1] : text;
  const m = block.match(/^\s*version\s*=\s*"([^"]+)"\s*$/m);
  return m ? m[1] : null;
}

// -- Marketplace upsert (used by --manual-copy flow + tests) -------------

/**
 * Upsert the phdtaketaketake plugin entry into a Claude marketplace
 * manifest at `marketplacePath` without clobbering other plugins on
 * the same marketplace. Creates the marketplace if it doesn't exist.
 *
 * Used by the --manual-copy fallback when we're writing into an
 * existing user-level Claude marketplaces dir; the canonical install
 * path runs `claude plugin marketplace add` instead and never touches
 * marketplace files directly.
 */
export function upsertMarketplaceEntry(marketplacePath, entry, owner) {
  let manifest;
  if (existsSync(marketplacePath)) {
    manifest = JSON.parse(readFileSync(marketplacePath, 'utf8'));
    if (!manifest.plugins) manifest.plugins = [];
  } else {
    manifest = {
      name: owner.name,
      owner,
      plugins: [],
    };
  }
  const idx = manifest.plugins.findIndex((p) => p.name === entry.name);
  if (idx >= 0) {
    manifest.plugins[idx] = { ...manifest.plugins[idx], ...entry };
  } else {
    manifest.plugins.push(entry);
  }
  writeFileSync(marketplacePath, JSON.stringify(manifest, null, 2) + '\n');
  return manifest;
}

// -- File operations ------------------------------------------------------

/**
 * Recursively copy `src` → `dest`, skipping anything in COPY_EXCLUDE.
 * Used by --manual-copy and (in c4) the Codex installer.
 */
export function copyPackage(src, dest) {
  mkdirSync(dest, { recursive: true });
  for (const entry of readdirSync(src, { withFileTypes: true })) {
    if (COPY_EXCLUDE.has(entry.name)) continue;
    const from = join(src, entry.name);
    const to = join(dest, entry.name);
    if (entry.isDirectory()) {
      cpSync(from, to, {
        recursive: true,
        // Skip excluded dirs anywhere in the tree.
        filter: (p) => {
          const rel = p.slice(from.length + 1).split(sep);
          return !rel.some((seg) => COPY_EXCLUDE.has(seg));
        },
      });
    } else if (entry.isFile() || entry.isSymbolicLink()) {
      cpSync(from, to);
    }
  }
}

/**
 * If `dest` exists, rename it to `${dest}.bak-${ISO_DATE}` and return
 * the backup path. Returns null when there was nothing to back up.
 */
export function backupIfExists(dest) {
  if (!existsSync(dest)) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backup = `${dest}.bak-${stamp}`;
  // Use rename via cp + rm to handle cross-device; for our case (same
  // home dir) the simple rename works. Fall back if rename fails.
  try {
    statSync(dest);
    cpSync(dest, backup, { recursive: true });
    rmSync(dest, { recursive: true, force: true });
    return backup;
  } catch {
    return null;
  }
}

// -- Internal utilities ---------------------------------------------------

function printPythonCliNote(out, installPath) {
  out.log('');
  out.log('Python CLIs (phdtaketaketake-match / -audit / -collect-evidence /');
  out.log('  -discovery-plan / -export-schemas / -cv-template / -cv-compile)');
  out.log('install separately. In the Python environment of your choice:');
  if (installPath) {
    out.log(`  python -m pip install -e ${installPath}`);
  } else {
    out.log('  python -m pip install -e <path-to-the-installed-plugin-dir>');
  }
  out.log('');
  out.log('We deliberately do not run pip for you (conda / venv / system');
  out.log('Python environments differ).');
}
