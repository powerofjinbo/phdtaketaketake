// Node-native test suite for the phdtake installer (Sprint distribution
// compliance patchset, c6).
//
// Run with: `npm test`  →  `node --test test/`
//
// Covers the install contract:
//   - Manifest parsing + version sync across package.json / plugin.json /
//     pyproject.toml.
//   - Marketplace upsert: preserves existing plugin entries (no clobber),
//     creates manifest cleanly when absent.
//   - Codex installer: writes to $HOME/.agents/skills/<name>/ (default)
//     and to <project>/.agents/skills/<name>/ (with --project), backs up
//     existing installs, never leaks excluded dirs.
//   - Cursor installer: writes .cursor/rules/<name>.mdc with frontmatter;
//     errors when --project missing.
//   - Claude installer (manual-copy path): writes to ~/.claude/plugins/
//     local/<name>/, backs up existing installs.
//   - CLI dispatch: --help, doctor, unknown commands, install without
//     a host flag.
//
// All tests use os.tmpdir-based fixtures so we never write into the real
// home directory. The installer reads CLAUDE_HOME / AGENTS_HOME env
// overrides to make this possible.

import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  PACKAGE_ROOT,
  backupIfExists,
  copyPackage,
  detectClaudeCli,
  doctor,
  installClaude,
  installCodex,
  installCursor,
  readVersionFromPackageJson,
  readVersionFromPluginJson,
  readVersionFromPyproject,
  renderCursorMdc,
  run,
  upsertMarketplaceEntry,
} from '../lib/installer.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');

// --- Helpers --------------------------------------------------------------

function makeTmp(prefix) {
  return mkdtempSync(join(tmpdir(), `phdtake-${prefix}-`));
}

/** Return a console-shaped sink that captures `.log` / `.warn` / `.error`. */
function captureConsole() {
  const log = [];
  const warn = [];
  const err = [];
  return {
    sink: {
      log: (...args) => log.push(args.join(' ')),
      warn: (...args) => warn.push(args.join(' ')),
      error: (...args) => err.push(args.join(' ')),
    },
    log,
    warn,
    err,
    text: () => [...log, ...warn, ...err].join('\n'),
  };
}

// --- Version readers ------------------------------------------------------

test('readVersionFromPackageJson returns 0.1.0 for the repo', () => {
  assert.equal(readVersionFromPackageJson(REPO_ROOT), '0.1.0');
});

test('readVersionFromPluginJson returns 0.1.0 for the repo', () => {
  assert.equal(readVersionFromPluginJson(REPO_ROOT), '0.1.0');
});

test('readVersionFromPyproject returns 0.1.0 for the repo', () => {
  assert.equal(readVersionFromPyproject(REPO_ROOT), '0.1.0');
});

test('all three version sources are equal (no version drift)', () => {
  // This test catches the canonical drift bug: someone bumps one file
  // but forgets the others. CI will fail here on every drift.
  const pkg = readVersionFromPackageJson(REPO_ROOT);
  const plugin = readVersionFromPluginJson(REPO_ROOT);
  const py = readVersionFromPyproject(REPO_ROOT);
  assert.equal(pkg, plugin, `package.json (${pkg}) vs plugin.json (${plugin})`);
  assert.equal(plugin, py, `plugin.json (${plugin}) vs pyproject.toml (${py})`);
});

// --- Marketplace upsert --------------------------------------------------

test('upsertMarketplaceEntry creates manifest when file is absent', () => {
  const tmp = makeTmp('mkt-create');
  const path = join(tmp, 'marketplace.json');
  upsertMarketplaceEntry(
    path,
    { name: 'phdtaketaketake', source: '.' },
    { name: 'powerofjinbo', url: 'https://example.com' },
  );
  const m = JSON.parse(readFileSync(path, 'utf8'));
  assert.equal(m.name, 'powerofjinbo');
  assert.equal(m.plugins.length, 1);
  assert.equal(m.plugins[0].name, 'phdtaketaketake');
  rmSync(tmp, { recursive: true, force: true });
});

test('upsertMarketplaceEntry preserves existing third-party plugins', () => {
  const tmp = makeTmp('mkt-preserve');
  const path = join(tmp, 'marketplace.json');
  // Pre-existing manifest with another plugin already in it.
  writeFileSync(
    path,
    JSON.stringify(
      {
        name: 'powerofjinbo',
        owner: { name: 'Jinbo Z' },
        plugins: [
          { name: 'some-other-plugin', source: 'github.com/other/plugin' },
        ],
      },
      null,
      2,
    ),
  );
  upsertMarketplaceEntry(
    path,
    { name: 'phdtaketaketake', source: '.' },
    { name: 'powerofjinbo' },
  );
  const m = JSON.parse(readFileSync(path, 'utf8'));
  assert.equal(m.plugins.length, 2);
  // Third-party plugin must not have been clobbered.
  const other = m.plugins.find((p) => p.name === 'some-other-plugin');
  assert.ok(other, 'pre-existing plugin entry was clobbered');
  assert.equal(other.source, 'github.com/other/plugin');
  rmSync(tmp, { recursive: true, force: true });
});

test('upsertMarketplaceEntry replaces an existing entry of the same name', () => {
  const tmp = makeTmp('mkt-replace');
  const path = join(tmp, 'marketplace.json');
  writeFileSync(
    path,
    JSON.stringify(
      {
        name: 'powerofjinbo',
        owner: { name: 'Jinbo Z' },
        plugins: [
          {
            name: 'phdtaketaketake',
            source: 'old-source',
            description: 'old description',
          },
        ],
      },
      null,
      2,
    ),
  );
  upsertMarketplaceEntry(
    path,
    { name: 'phdtaketaketake', source: 'new-source', description: 'new description' },
    { name: 'powerofjinbo' },
  );
  const m = JSON.parse(readFileSync(path, 'utf8'));
  assert.equal(m.plugins.length, 1);
  assert.equal(m.plugins[0].source, 'new-source');
  assert.equal(m.plugins[0].description, 'new description');
  rmSync(tmp, { recursive: true, force: true });
});

// --- File ops -------------------------------------------------------------

test('copyPackage skips excluded directories', () => {
  const src = makeTmp('copy-src');
  const dst = makeTmp('copy-dst');
  // Build a fake package: includes both legitimate and excluded paths.
  mkdirSync(join(src, 'phd_matcher'));
  writeFileSync(join(src, 'phd_matcher', 'real.py'), '# real source');
  mkdirSync(join(src, 'phd_matcher', '__pycache__'));
  writeFileSync(join(src, 'phd_matcher', '__pycache__', 'cached.pyc'), 'binary');
  mkdirSync(join(src, '.git'));
  writeFileSync(join(src, '.git', 'HEAD'), 'ref: refs/heads/main');
  mkdirSync(join(src, 'node_modules'));
  writeFileSync(join(src, 'node_modules', 'whatever.js'), '');
  writeFileSync(join(src, 'SKILL.md'), '# skill');

  copyPackage(src, dst);

  assert.ok(existsSync(join(dst, 'SKILL.md')));
  assert.ok(existsSync(join(dst, 'phd_matcher', 'real.py')));
  assert.ok(!existsSync(join(dst, '.git')), '.git should be excluded');
  assert.ok(!existsSync(join(dst, 'node_modules')), 'node_modules should be excluded');
  assert.ok(
    !existsSync(join(dst, 'phd_matcher', '__pycache__')),
    '__pycache__ should be excluded even when nested',
  );

  rmSync(src, { recursive: true, force: true });
  rmSync(dst, { recursive: true, force: true });
});

test('backupIfExists returns null when destination is absent', () => {
  const tmp = makeTmp('bk-absent');
  const dest = join(tmp, 'doesnt-exist');
  assert.equal(backupIfExists(dest), null);
  rmSync(tmp, { recursive: true, force: true });
});

test('backupIfExists renames an existing dir to <dest>.bak-<ts>', () => {
  const tmp = makeTmp('bk-present');
  const dest = join(tmp, 'phdtaketaketake');
  mkdirSync(dest);
  writeFileSync(join(dest, 'marker.txt'), 'old install');
  const backup = backupIfExists(dest);
  assert.ok(backup, 'expected a backup path to be returned');
  assert.ok(backup.startsWith(`${dest}.bak-`), `unexpected backup path: ${backup}`);
  assert.ok(!existsSync(dest), 'original dest should be moved away');
  assert.ok(existsSync(join(backup, 'marker.txt')), 'backup should preserve contents');
  rmSync(tmp, { recursive: true, force: true });
});

// --- Codex installer -----------------------------------------------------

test('installCodex (user-level) writes to $AGENTS_HOME/.agents/skills/<name>/', async () => {
  const home = makeTmp('codex-user');
  const cap = captureConsole();
  const code = await installCodex({
    packageRoot: REPO_ROOT,
    env: { AGENTS_HOME: home },
    console: cap.sink,
  });
  assert.equal(code, 0);
  const dest = join(home, '.agents', 'skills', 'phdtaketaketake');
  assert.ok(existsSync(join(dest, 'SKILL.md')), 'SKILL.md should land in skill dir');
  assert.ok(existsSync(join(dest, 'AGENTS.md')), 'AGENTS.md should land in skill dir');
  assert.ok(existsSync(join(dest, 'phd_matcher')), 'phd_matcher/ should be copied');
  assert.ok(!existsSync(join(dest, '.git')), '.git must not leak into install');
  assert.ok(cap.text().includes('user-level install'), 'expected user-level wording');
  rmSync(home, { recursive: true, force: true });
});

test('installCodex (--project) writes to <project>/.agents/skills/<name>/', async () => {
  const project = makeTmp('codex-proj');
  const cap = captureConsole();
  const code = await installCodex({
    packageRoot: REPO_ROOT,
    env: {},
    console: cap.sink,
    projectDir: project,
  });
  assert.equal(code, 0);
  const dest = join(project, '.agents', 'skills', 'phdtaketaketake');
  assert.ok(existsSync(join(dest, 'SKILL.md')));
  assert.ok(cap.text().includes('project-local install'), 'expected project-local wording');
  rmSync(project, { recursive: true, force: true });
});

test('installCodex backs up an existing install before overwriting', async () => {
  const home = makeTmp('codex-backup');
  const dest = join(home, '.agents', 'skills', 'phdtaketaketake');
  mkdirSync(dest, { recursive: true });
  writeFileSync(join(dest, 'OLD_INSTALL.txt'), 'previous run');
  const cap = captureConsole();
  await installCodex({
    packageRoot: REPO_ROOT,
    env: { AGENTS_HOME: home },
    console: cap.sink,
  });
  // The new install replaces the old contents.
  assert.ok(existsSync(join(dest, 'SKILL.md')));
  assert.ok(!existsSync(join(dest, 'OLD_INSTALL.txt')), 'old install file should be gone');
  // The backup directory exists alongside.
  const skillsDir = dirname(dest);
  const entries = readdirSync(skillsDir);
  const backups = entries.filter((e) => e.startsWith('phdtaketaketake.bak-'));
  assert.ok(backups.length >= 1, 'expected one backup directory');
  assert.ok(
    existsSync(join(skillsDir, backups[0], 'OLD_INSTALL.txt')),
    'backup should preserve old install file',
  );
  rmSync(home, { recursive: true, force: true });
});

// --- Cursor installer ----------------------------------------------------

test('installCursor errors with exit 2 when --project is missing', async () => {
  const cap = captureConsole();
  const code = await installCursor({
    packageRoot: REPO_ROOT,
    env: {},
    console: cap.sink,
  });
  assert.equal(code, 2);
  assert.ok(cap.text().toLowerCase().includes('--project'));
});

test('installCursor writes .cursor/rules/<name>.mdc with frontmatter', async () => {
  const project = makeTmp('cursor-proj');
  const cap = captureConsole();
  const code = await installCursor({
    packageRoot: REPO_ROOT,
    env: {},
    console: cap.sink,
    projectDir: project,
  });
  assert.equal(code, 0);
  const mdcPath = join(project, '.cursor', 'rules', 'phdtaketaketake.mdc');
  assert.ok(existsSync(mdcPath), `.mdc file should be at ${mdcPath}`);
  const body = readFileSync(mdcPath, 'utf8');
  assert.ok(body.startsWith('---\n'), 'must start with frontmatter delimiter');
  assert.ok(body.includes('alwaysApply: false'), 'must declare alwaysApply: false');
  assert.ok(
    body.includes('Connection-first') && body.includes('Evidence-first'),
    'must surface the hard rules from SKILL.md',
  );
  // It MUST be a pointer, not a copy of SKILL.md (drift avoidance).
  assert.ok(
    body.length < 4000,
    `Cursor .mdc should be a short pointer (<4000 chars); got ${body.length}`,
  );
  rmSync(project, { recursive: true, force: true });
});

test('renderCursorMdc is pure and respects skillPath param', () => {
  const a = renderCursorMdc({ skillPath: './SKILL.md' });
  const b = renderCursorMdc({ skillPath: '/abs/path/SKILL.md' });
  assert.ok(a.includes('./SKILL.md'));
  assert.ok(b.includes('/abs/path/SKILL.md'));
  // Frontmatter and hard rules are stable.
  for (const out of [a, b]) {
    assert.ok(out.startsWith('---\n'));
    assert.ok(out.includes('alwaysApply: false'));
    assert.ok(out.includes('Connection-first'));
    assert.ok(out.includes('CV source-of-truth'));
  }
});

// --- Claude installer (manual-copy path) ---------------------------------

test('installClaude --manual-copy writes to $CLAUDE_HOME/plugins/local/<name>/', async () => {
  const claudeHome = makeTmp('claude-manual');
  const cap = captureConsole();
  const code = await installClaude({
    packageRoot: REPO_ROOT,
    env: { CLAUDE_HOME: claudeHome },
    console: cap.sink,
    manualCopy: true,
  });
  assert.equal(code, 0);
  const dest = join(claudeHome, 'plugins', 'local', 'phdtaketaketake');
  assert.ok(existsSync(join(dest, 'SKILL.md')));
  assert.ok(existsSync(join(dest, '.claude-plugin', 'plugin.json')));
  assert.ok(existsSync(join(dest, '.claude-plugin', 'marketplace.json')));
  rmSync(claudeHome, { recursive: true, force: true });
});

test('installClaude (no claude CLI, no --manual-copy) prints fallback instructions', async () => {
  const cap = captureConsole();
  // Stub out claude detection: pretend it's absent.
  const code = await installClaude({
    packageRoot: REPO_ROOT,
    env: {},
    console: cap.sink,
    manualCopy: false,
    runner: () => ({ status: 1, stdout: '', stderr: '' }),
  });
  assert.equal(code, 0);
  const text = cap.text();
  assert.ok(text.includes('/plugin marketplace add'), 'must print slash-command hint');
  assert.ok(text.includes('--manual-copy'), 'must mention manual-copy fallback');
});

test('installClaude with claude CLI present invokes the right subcommands', async () => {
  const calls = [];
  const cap = captureConsole();
  const fakeRunner = (cmd, args) => {
    calls.push({ cmd, args: args || [] });
    if ((args || [])[0] === 'plugin' && args[1] === 'marketplace' && args[2] === 'add') {
      return { status: 0 };
    }
    if ((args || [])[0] === 'plugin' && args[1] === 'install') {
      return { status: 0 };
    }
    // detectClaudeCli's `which claude` call.
    if (cmd === 'which') {
      return { status: 0, stdout: Buffer.from('/fake/bin/claude\n') };
    }
    return { status: 0 };
  };
  const code = await installClaude({
    packageRoot: REPO_ROOT,
    env: {},
    console: cap.sink,
    runner: fakeRunner,
  });
  assert.equal(code, 0);
  // We expect: which claude → marketplace add → plugin install.
  const calledClaude = calls.filter((c) => c.cmd === '/fake/bin/claude');
  assert.equal(calledClaude.length, 2, 'should call claude exactly twice');
  assert.deepEqual(calledClaude[0].args.slice(0, 3), ['plugin', 'marketplace', 'add']);
  assert.deepEqual(calledClaude[1].args.slice(0, 2), ['plugin', 'install']);
  assert.equal(calledClaude[1].args[2], 'phdtaketaketake@powerofjinbo');
});

// --- Doctor --------------------------------------------------------------

test('doctor returns 0 on the real repo (or 1 on warning, never 2)', async () => {
  const cap = captureConsole();
  const code = await doctor({
    packageRoot: REPO_ROOT,
    env: process.env,
    console: cap.sink,
  });
  // 0 or 1 acceptable (depending on whether claude CLI is on this CI box).
  // 2 means a hard manifest error, which would be a real bug.
  assert.ok(code === 0 || code === 1, `doctor returned exit ${code}`);
  const text = cap.text();
  assert.ok(text.includes('Node'));
  assert.ok(text.includes('plugin.json'));
  assert.ok(text.includes('marketplace.json'));
  assert.ok(text.includes('version sync'));
});

// --- CLI dispatch via run() ----------------------------------------------

test('run([]) prints help and exits 0', async () => {
  const cap = captureConsole();
  const code = await run([], { packageRoot: REPO_ROOT, console: cap.sink });
  assert.equal(code, 0);
  assert.ok(cap.text().includes('phdtake'));
});

test('run(["--help"]) prints help and exits 0', async () => {
  const cap = captureConsole();
  const code = await run(['--help'], { packageRoot: REPO_ROOT, console: cap.sink });
  assert.equal(code, 0);
});

test('run(["unknown"]) exits 2 with usage', async () => {
  const cap = captureConsole();
  const code = await run(['unknown'], { packageRoot: REPO_ROOT, console: cap.sink });
  assert.equal(code, 2);
});

test('run(["install"]) without a host flag exits 2', async () => {
  const cap = captureConsole();
  const code = await run(['install'], { packageRoot: REPO_ROOT, console: cap.sink });
  assert.equal(code, 2);
  assert.ok(cap.text().toLowerCase().includes('host'));
});

test('run(["--version"]) prints the package version', async () => {
  const cap = captureConsole();
  const code = await run(['--version'], { packageRoot: REPO_ROOT, console: cap.sink });
  assert.equal(code, 0);
  assert.equal(cap.log[0], '0.1.0');
});

// --- bin/phdtake.js integration -----------------------------------------

test('bin/phdtake.js --help via subprocess exits 0 and prints help', () => {
  const result = spawnSync(
    process.execPath,
    [join(REPO_ROOT, 'bin', 'phdtake.js'), '--help'],
    { encoding: 'utf8' },
  );
  assert.equal(result.status, 0);
  assert.ok(result.stdout.includes('phdtake'));
});

test('bin/phdtake.js doctor via subprocess exits 0 or 1', () => {
  const result = spawnSync(
    process.execPath,
    [join(REPO_ROOT, 'bin', 'phdtake.js'), 'doctor'],
    { encoding: 'utf8' },
  );
  assert.ok(result.status === 0 || result.status === 1, `unexpected exit ${result.status}`);
});

// --- npm-pack contents (smoke check) -------------------------------------

// --- Pre-pack consistency (post-c7 review) ----------------------------

test('marketplace.json plugin source uses canonical "./" path form', () => {
  const m = JSON.parse(
    readFileSync(join(REPO_ROOT, '.claude-plugin', 'marketplace.json'), 'utf8'),
  );
  const entry = m.plugins.find((p) => p.name === 'phdtaketaketake');
  assert.ok(entry, 'phdtaketaketake entry must exist in marketplace.json');
  // Claude plugin docs canonicalize on the "./..." relative form for
  // marketplace `source` fields. Plain "." can fail validators / future
  // CLI versions even though it's filesystem-equivalent.
  assert.ok(
    entry.source.startsWith('./'),
    `marketplace source must start with "./"; got "${entry.source}"`,
  );
});

test('install --badflag exits 2 with a friendly error (not a stack trace)', async () => {
  const cap = captureConsole();
  const code = await run(['install', '--gemini'], {
    packageRoot: REPO_ROOT,
    console: cap.sink,
  });
  assert.equal(code, 2, 'unknown flag must exit 2');
  const text = cap.text();
  // The friendly message names the flag and lists supported alternatives.
  assert.ok(text.includes('--gemini'), 'error must name the unknown flag');
  assert.ok(text.includes('--claude'), 'error must list supported alternatives');
  // Stack-trace markers MUST NOT appear in the user-facing output.
  assert.ok(!text.includes('at parseInstallFlags'), 'must not surface a stack trace');
  assert.ok(!text.includes('at installCmd'), 'must not surface a stack trace');
});

test('install --all without --project skips Cursor with a notice (does not fail)', async () => {
  // We exercise the dispatch logic without doing any real install side-
  // effects. The dispatcher logs "--- Skipping cursor (requires --project) ---"
  // when --all is requested but no project dir was provided. We verify
  // that message appears, and that the overall dispatch reaches Claude
  // and Codex but never enters Cursor.
  //
  // We don't actually invoke installClaude / installCodex with real
  // filesystem effects — we set CLAUDE_HOME / AGENTS_HOME to throwaway
  // tmp dirs.
  const claudeHome = makeTmp('all-no-proj-claude');
  const agentsHome = makeTmp('all-no-proj-agents');
  const cap = captureConsole();
  const code = await run(
    ['install', '--all', '--manual-copy'], // manualCopy → skip claude CLI shell-out
    {
      packageRoot: REPO_ROOT,
      env: { CLAUDE_HOME: claudeHome, AGENTS_HOME: agentsHome },
      console: cap.sink,
    },
  );
  assert.equal(code, 0, '--all with Cursor skipped should return 0');
  const text = cap.text();
  assert.ok(text.includes('Skipping cursor'), 'must log the skip notice');
  assert.ok(
    text.includes('--cursor --project'),
    'must point user at the explicit re-run command',
  );
  // Confirm Claude + Codex still ran.
  assert.ok(
    existsSync(join(claudeHome, 'plugins', 'local', 'phdtaketaketake', 'SKILL.md')),
    'Claude install should have run',
  );
  assert.ok(
    existsSync(
      join(agentsHome, '.agents', 'skills', 'phdtaketaketake', 'SKILL.md'),
    ),
    'Codex install should have run',
  );
  rmSync(claudeHome, { recursive: true, force: true });
  rmSync(agentsHome, { recursive: true, force: true });
});

test('install --all with --project installs all three including Cursor', async () => {
  const claudeHome = makeTmp('all-proj-claude');
  const agentsHome = makeTmp('all-proj-agents');
  const project = makeTmp('all-proj-cursor');
  const cap = captureConsole();
  const code = await run(
    ['install', '--all', '--project', project, '--manual-copy'],
    {
      packageRoot: REPO_ROOT,
      env: { CLAUDE_HOME: claudeHome, AGENTS_HOME: agentsHome },
      console: cap.sink,
    },
  );
  assert.equal(code, 0);
  // All three hosts saw an install.
  assert.ok(existsSync(join(claudeHome, 'plugins', 'local', 'phdtaketaketake', 'SKILL.md')));
  // Codex with --project goes to <project>/.agents/skills/, NOT $AGENTS_HOME.
  assert.ok(existsSync(join(project, '.agents', 'skills', 'phdtaketaketake', 'SKILL.md')));
  assert.ok(existsSync(join(project, '.cursor', 'rules', 'phdtaketaketake.mdc')));
  rmSync(claudeHome, { recursive: true, force: true });
  rmSync(agentsHome, { recursive: true, force: true });
  rmSync(project, { recursive: true, force: true });
});

test('detectClaudeCli uses `where` on win32 and `which` elsewhere', () => {
  const calls = [];
  const fakeRunner = (cmd, _args) => {
    calls.push(cmd);
    return { status: 1 }; // pretend not found, we only care about the cmd
  };
  detectClaudeCli({ env: {}, runner: fakeRunner, platform: 'win32' });
  assert.equal(calls[calls.length - 1], 'where', 'Windows should use `where`');
  detectClaudeCli({ env: {}, runner: fakeRunner, platform: 'darwin' });
  assert.equal(calls[calls.length - 1], 'which', 'POSIX should use `which`');
  detectClaudeCli({ env: {}, runner: fakeRunner, platform: 'linux' });
  assert.equal(calls[calls.length - 1], 'which', 'POSIX should use `which`');
});

test('detectClaudeCli on Windows takes the first line of `where` output', () => {
  // `where claude` on Windows can return multiple lines (one per match
  // on PATH). detectClaudeCli must take the first.
  const fakeRunner = () => ({
    status: 0,
    stdout: Buffer.from('C:\\Users\\u\\bin\\claude.exe\r\nC:\\Other\\claude.exe\r\n'),
  });
  const path = detectClaudeCli({ env: {}, runner: fakeRunner, platform: 'win32' });
  assert.equal(path, 'C:\\Users\\u\\bin\\claude.exe');
});

// --- Original npm-pack contents test (unchanged below) ------------------

test('npm pack --dry-run includes the bundled .tex template', () => {
  // Verify the wheel-equivalent contents include critical files. This
  // is the npm-side analogue of the Python wheel-packaging check we did
  // manually in Sprint-7-c4.
  const result = spawnSync(
    'npm',
    ['pack', '--dry-run', '--json', '--silent'],
    { cwd: REPO_ROOT, encoding: 'utf8' },
  );
  if (result.status !== 0) {
    // If npm is unavailable in the test environment, skip gracefully.
    test.skip(`npm pack returned ${result.status}: ${result.stderr || result.stdout}`);
    return;
  }
  // --silent suppresses npm script output (prepack), but to be safe,
  // we extract the JSON array from anywhere in stdout — the JSON is
  // always the last balanced [...] block.
  const stdout = result.stdout;
  const jsonStart = stdout.indexOf('[');
  const jsonEnd = stdout.lastIndexOf(']');
  if (jsonStart < 0 || jsonEnd < 0) {
    throw new Error(`npm pack stdout did not contain JSON: ${stdout}`);
  }
  const out = JSON.parse(stdout.slice(jsonStart, jsonEnd + 1));
  const files = (out[0]?.files || []).map((f) => f.path);
  assert.ok(files.includes('SKILL.md'), 'SKILL.md must be in the package');
  assert.ok(
    files.includes('phd_matcher/cv/templates/default.tex'),
    'CV template must be in the package',
  );
  assert.ok(
    files.includes('.claude-plugin/plugin.json'),
    'plugin manifest must be in the package',
  );
  assert.ok(
    files.includes('.claude-plugin/marketplace.json'),
    'marketplace manifest must be in the package',
  );
  assert.ok(files.includes('AGENTS.md'), 'AGENTS.md must be in the package');
  assert.ok(files.includes('bin/phdtake.js'), 'bin must be in the package');
  assert.ok(files.includes('lib/installer.js'), 'lib must be in the package');
  // Negative: things that must NOT ship.
  for (const f of files) {
    assert.ok(!f.startsWith('.git/'), `npm pack must not include .git/: ${f}`);
    assert.ok(!f.includes('__pycache__'), `npm pack must not include __pycache__: ${f}`);
    assert.ok(!f.startsWith('node_modules/'), `npm pack must not include node_modules/: ${f}`);
  }
});
