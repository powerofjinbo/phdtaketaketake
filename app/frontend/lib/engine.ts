// Client wrapper around the Pyodide engine worker (public/engine-worker.js).
// The worker runs the exact phd_matcher Python engine in the browser.

export type EngineStatusListener = (note: string) => void;

let worker: Worker | null = null;
let seq = 0;
const pending = new Map<
  number,
  { resolve: (v: unknown) => void; reject: (e: Error) => void }
>();
const statusListeners = new Set<EngineStatusListener>();

export function onEngineStatus(fn: EngineStatusListener): () => void {
  statusListeners.add(fn);
  return () => statusListeners.delete(fn);
}

function getWorker(): Worker {
  if (worker) return worker;
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  worker = new Worker(`${base}/engine-worker.js`, { type: "module" });
  worker.onmessage = (ev) => {
    const data = ev.data;
    if (data.type === "status") {
      statusListeners.forEach((fn) => fn(data.note));
      return;
    }
    const p = pending.get(data.id);
    if (!p) return;
    pending.delete(data.id);
    if (data.ok) p.resolve(data.result);
    else p.reject(new Error(data.error));
  };
  worker.onerror = (e) => {
    const err = new Error(`engine worker failed: ${e.message}`);
    pending.forEach((p) => p.reject(err));
    pending.clear();
    worker?.terminate();
    worker = null;
  };
  return worker;
}

function call<T>(msg: Record<string, unknown>): Promise<T> {
  const id = ++seq;
  return new Promise<T>((resolve, reject) => {
    pending.set(id, { resolve: resolve as (v: unknown) => void, reject });
    getWorker().postMessage({ id, ...msg });
  });
}

export interface RankOutput {
  results?: Record<string, unknown>[];
  portfolio_summary?: string;
  field_caveats?: string[];
  error?: string;
  dropped?: string[];
  strict_errors?: string[];
}

export function warmupEngine(): Promise<{ ready: boolean }> {
  return call({ type: "warmup" });
}

export function rankCandidates(
  profile: unknown,
  candidates: unknown[],
  topK: number,
  strict: boolean
): Promise<RankOutput> {
  return call({ type: "rank", profile, candidates, topK, strict });
}

export function validateProfile(
  profile: unknown
): Promise<{ ok: boolean; error?: string }> {
  return call({ type: "validate-profile", profile });
}
