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
}

const MAX_RUNS = 20;

export function loadRuns(): StoredRun[] {
  return read<StoredRun[]>("runs", []);
}

export function getRun(id: string): StoredRun | null {
  return loadRuns().find((r) => r.id === id) || null;
}

export function upsertRun(run: StoredRun) {
  const runs = loadRuns().filter((r) => r.id !== run.id);
  runs.unshift(run);
  // Cap storage; drop oldest results first if quota is hit.
  let trimmed = runs.slice(0, MAX_RUNS);
  for (;;) {
    try {
      write("runs", trimmed);
      break;
    } catch {
      if (trimmed.length <= 1) break; // give up quietly
      trimmed = trimmed.slice(0, trimmed.length - 1);
    }
  }
  notifyRuns();
}

export function deleteRun(id: string) {
  write("runs", loadRuns().filter((r) => r.id !== id));
  notifyRuns();
}

// Simple subscription so pages re-render when a background run progresses.
const runListeners = new Set<() => void>();

export function onRunsChanged(fn: () => void): () => void {
  runListeners.add(fn);
  return () => runListeners.delete(fn);
}

function notifyRuns() {
  runListeners.forEach((fn) => fn());
}

export function newRunId(): string {
  return `run_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}
