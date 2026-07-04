// Local persistence — everything lives in this browser. No accounts, no
// server. localStorage keys are namespaced under "phdtake:".

import type { LlmSettings } from "./llm";

const NS = "phdtake:";

function read<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(NS + key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  localStorage.setItem(NS + key, JSON.stringify(value));
}

// ---- LLM settings ----------------------------------------------------------

export function loadSettings(): LlmSettings | null {
  return read<LlmSettings | null>("settings", null);
}

export function saveSettings(s: LlmSettings) {
  write("settings", s);
}

// ---- Student profile -------------------------------------------------------

export type StudentProfileJson = Record<string, unknown>;

export function loadProfile(): StudentProfileJson | null {
  return read<StudentProfileJson | null>("profile", null);
}

export function saveProfile(p: StudentProfileJson) {
  write("profile", p);
}

// ---- Runs ------------------------------------------------------------------

export type RunStatus = "researching" | "scoring" | "done" | "error";

export interface StoredRun {
  id: string;
  created_at: string;
  target: string;
  top_k: number;
  strict: boolean;
  provider: string;
  status: RunStatus;
  progress_note: string;
  results: Record<string, unknown>[] | null;
  portfolio_summary: string | null;
  field_caveats: string[];
  error: string | null;
  // Heartbeat: bumped on every pipeline update. A run left "researching"/
  // "scoring" whose heartbeat has gone stale was orphaned by a reload/tab
  // close (the pipeline only lives in the tab that started it) — the reaper
  // flips it to "error" so it never hangs forever.
  updated_at?: number;
}

const MAX_RUNS = 20;
// A run is considered orphaned if it's still "active" but its heartbeat is
// older than this. Generous because the first-ever engine load downloads
// ~13 MB of Pyodide during the scoring phase; onEngineStatus keeps the
// heartbeat fresh during that window, but slow networks need slack.
const STALE_MS = 180_000;

function isActive(s: RunStatus): boolean {
  return s === "researching" || s === "scoring";
}

// Tombstones: ids the user deleted. A still-running pipeline in this tab
// would otherwise re-persist (resurrect) a deleted run on its next progress
// tick. upsertRun refuses to write a tombstoned id.
function tombstones(): string[] {
  return read<string[]>("run_tombstones", []);
}
function isTombstoned(id: string): boolean {
  return tombstones().includes(id);
}

// Reap orphaned runs on every read. A live pipeline keeps its own run's
// heartbeat fresh, so only truly-abandoned active runs get flipped.
function reap(runs: StoredRun[]): { runs: StoredRun[]; changed: boolean } {
  const now = Date.now();
  let changed = false;
  const out = runs.map((r) => {
    if (isActive(r.status) && now - (r.updated_at ?? 0) > STALE_MS) {
      changed = true;
      return {
        ...r,
        status: "error" as RunStatus,
        error:
          "This run was interrupted — the tab was closed or reloaded while it " +
          "was running. Runs execute in your browser, so they can't continue " +
          "in the background. Start a new run to try again.",
        progress_note: "interrupted",
      };
    }
    return r;
  });
  return { runs: out, changed };
}

export function loadRuns(): StoredRun[] {
  const raw = read<StoredRun[]>("runs", []);
  const { runs, changed } = reap(raw);
  if (changed) {
    try {
      write("runs", runs);
    } catch {
      /* reap is best-effort */
    }
  }
  return runs;
}

export function getRun(id: string): StoredRun | null {
  return loadRuns().find((r) => r.id === id) || null;
}

export function upsertRun(run: StoredRun) {
  if (isTombstoned(run.id)) return; // deleted — never resurrect
  run.updated_at = Date.now();
  const runs = read<StoredRun[]>("runs", []).filter((r) => r.id !== run.id);
  runs.unshift(run);
  // Cap storage; on quota errors, shed OLD runs' heavy results first, never
  // the run we're currently updating (which holds this run's fresh state).
  let trimmed = runs.slice(0, MAX_RUNS);
  for (;;) {
    try {
      write("runs", trimmed);
      break;
    } catch {
      const victim = [...trimmed]
        .reverse()
        .find((r) => r.id !== run.id && r.results !== null);
      if (victim) {
        victim.results = null;
        victim.portfolio_summary =
          "(results dropped to free browser storage — re-run to regenerate)";
        continue;
      }
      if (trimmed.length > 1) {
        trimmed = trimmed.filter((r, i) => r.id === run.id || i < trimmed.length - 1);
        continue;
      }
      break; // only this run left and still too big — give up
    }
  }
  notifyRuns();
}

export function deleteRun(id: string) {
  write("runs", read<StoredRun[]>("runs", []).filter((r) => r.id !== id));
  const t = tombstones();
  if (!t.includes(id)) write("run_tombstones", [...t, id].slice(-100));
  notifyRuns();
}

// Subscription so pages re-render when a background run progresses.
const runListeners = new Set<() => void>();
let storageBound = false;

export function onRunsChanged(fn: () => void): () => void {
  runListeners.add(fn);
  // Cross-tab: a run advancing in the tab that owns it writes localStorage;
  // other tabs get a "storage" event and re-render from the new state.
  if (!storageBound && typeof window !== "undefined") {
    storageBound = true;
    window.addEventListener("storage", (e) => {
      if (e.key === NS + "runs") notifyRuns();
    });
  }
  return () => runListeners.delete(fn);
}

function notifyRuns() {
  runListeners.forEach((fn) => fn());
}

export function newRunId(): string {
  return `run_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}
