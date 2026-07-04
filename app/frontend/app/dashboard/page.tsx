"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type RunSummary } from "@/lib/api";
import StatusChip, { ACTIVE_STATUSES } from "@/components/StatusChip";

const TIER_PRESETS = [
  { value: "top_10", label: "Top 10 programs" },
  { value: "top_20", label: "Top 20 programs" },
  { value: "top_50", label: "Top 50 programs" },
  { value: "custom", label: "Custom school list" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [preset, setPreset] = useState("top_10");
  const [schools, setSchools] = useState("");
  const [topK, setTopK] = useState(10);
  const [strict, setStrict] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const list = await api<RunSummary[]>("/runs");
      setRuns(list);
      setError(null);
      return list;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
      return [];
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(fetchRuns, 0);
    return () => clearTimeout(t);
  }, [fetchRuns]);

  // poll every 3s while any run is active
  useEffect(() => {
    const anyActive = (runs ?? []).some((r) =>
      ACTIVE_STATUSES.includes(r.status)
    );
    if (anyActive && !timerRef.current) {
      timerRef.current = setInterval(fetchRuns, 3000);
    } else if (!anyActive && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [runs, fetchRuns]);

  async function startRun(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const target = preset === "custom" ? schools.trim() : preset;
      const { id } = await api<{ id: string }>("/runs", {
        method: "POST",
        body: JSON.stringify({ target, top_k: topK, strict }),
      });
      await fetchRuns();
      router.push(`/runs/view?id=${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-white">Dashboard</h1>
      <p className="mt-2 text-sm text-zinc-400">
        Start a new match run or revisit past results.
      </p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,380px)_1fr]">
        {/* New run form */}
        <form
          onSubmit={startRun}
          className="h-fit rounded-2xl border border-white/10 bg-white/[0.03] p-6"
        >
          <h2 className="text-lg font-semibold text-white">New match run</h2>

          <div className="mt-5 space-y-5">
            <div>
              <label className="mb-1.5 block text-sm text-zinc-300">
                Target
              </label>
              <select
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400/60"
              >
                {TIER_PRESETS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {preset === "custom" && (
              <div>
                <label className="mb-1.5 block text-sm text-zinc-300">
                  School list
                </label>
                <textarea
                  value={schools}
                  onChange={(e) => setSchools(e.target.value)}
                  required
                  className="min-h-20 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-indigo-400/60"
                  placeholder="MIT, Stanford, Berkeley…"
                />
              </div>
            )}

            <div>
              <label className="mb-1.5 flex items-center justify-between text-sm text-zinc-300">
                <span>Candidates to rank (top_k)</span>
                <span className="font-mono text-indigo-300">{topK}</span>
              </label>
              <input
                type="range"
                min={3}
                max={30}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </div>

            <label className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/20 px-4 py-3">
              <span>
                <span className="block text-sm text-zinc-200">
                  Strict evidence mode
                </span>
                <span className="block text-xs text-zinc-500">
                  Only fully sourced signals count toward scores.
                </span>
              </span>
              <input
                type="checkbox"
                checked={strict}
                onChange={(e) => setStrict(e.target.checked)}
                className="h-5 w-5 accent-indigo-500"
              />
            </label>

            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                <p>{error}</p>
                <p className="mt-1.5 text-xs text-red-200/80">
                  {/(profile|cv)/i.test(error) ? (
                    <>
                      Complete your{" "}
                      <Link href="/profile" className="text-indigo-300 underline">
                        profile
                      </Link>{" "}
                      first.
                    </>
                  ) : /(key|provider|settings|llm)/i.test(error) ? (
                    <>
                      Add an API key in{" "}
                      <Link href="/settings" className="text-indigo-300 underline">
                        Settings
                      </Link>
                      .
                    </>
                  ) : (
                    <>
                      Check your{" "}
                      <Link href="/profile" className="text-indigo-300 underline">
                        profile
                      </Link>{" "}
                      and{" "}
                      <Link href="/settings" className="text-indigo-300 underline">
                        settings
                      </Link>
                      .
                    </>
                  )}
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 py-2.5 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {submitting ? "Starting…" : "Start match run"}
            </button>
          </div>
        </form>

        {/* Runs list */}
        <div>
          <h2 className="mb-4 text-lg font-semibold text-white">Past runs</h2>
          {runs === null ? (
            <p className="text-sm text-zinc-500">Loading runs…</p>
          ) : runs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
              No runs yet. Start your first match run on the left.
            </div>
          ) : (
            <ul className="space-y-3">
              {runs.map((r) => (
                <li key={r.id}>
                  <Link
                    href={`/runs/view?id=${r.id}`}
                    className="block rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-indigo-400/40 hover:bg-indigo-500/[0.05]"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">
                          {r.target}
                        </p>
                        <p className="mt-0.5 text-xs text-zinc-500">
                          {new Date(r.created_at).toLocaleString()}
                        </p>
                      </div>
                      <StatusChip status={r.status} />
                    </div>
                    {r.progress_note &&
                      ACTIVE_STATUSES.includes(r.status) && (
                        <p className="mt-2 text-xs text-indigo-300/80">
                          {r.progress_note}
                        </p>
                      )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
