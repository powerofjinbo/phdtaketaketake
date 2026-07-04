"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  deleteRun,
  loadProfile,
  loadRuns,
  loadSettings,
  onRunsChanged,
  type StoredRun,
} from "@/lib/store";
import { startRun } from "@/lib/research";
import { PROVIDERS } from "@/lib/llm";
import StatusChip, { ACTIVE_STATUSES } from "@/components/StatusChip";

const TIER_PRESETS = [
  { value: "top_10", label: "Top 10 programs" },
  { value: "top_20", label: "Top 20 programs" },
  { value: "top_50", label: "Top 50 programs" },
  { value: "custom", label: "Custom school list" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<StoredRun[] | null>(null);
  const [hasProfile, setHasProfile] = useState(true);
  const [hasKey, setHasKey] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [preset, setPreset] = useState("top_10");
  const [schools, setSchools] = useState("");
  const [topK, setTopK] = useState(10);
  const [strict, setStrict] = useState(false);

  useEffect(() => {
    const refresh = () => setRuns(loadRuns());
    const t = setTimeout(() => {
      refresh();
      setHasProfile(!!loadProfile());
      setHasKey(!!loadSettings()?.apiKey?.trim());
    }, 0);
    const unsub = onRunsChanged(refresh);
    return () => {
      clearTimeout(t);
      unsub();
    };
  }, []);

  const ready = hasProfile && hasKey;

  function onStartRun(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const profile = loadProfile();
    const settings = loadSettings();
    if (!profile || !settings?.apiKey?.trim()) {
      setHasProfile(!!profile);
      setHasKey(!!settings?.apiKey?.trim());
      return;
    }
    try {
      const target = preset === "custom" ? schools.trim() : preset;
      const id = startRun({
        profile,
        target,
        topK,
        strict,
        settings,
      });
      router.push(`/runs/view?id=${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run");
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-white">Dashboard</h1>
      <p className="mt-2 text-sm text-zinc-400">
        Start a new match run or revisit past results. Everything runs and
        stays in this browser.
      </p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,380px)_1fr]">
        {/* New run form */}
        <form
          onSubmit={onStartRun}
          className="h-fit rounded-2xl border border-white/10 bg-white/[0.03] p-6"
        >
          <h2 className="text-lg font-semibold text-white">New match run</h2>

          <div className="mt-5 space-y-5">
            {!hasProfile && (
              <p className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                No profile yet — fill your{" "}
                <Link href="/profile" className="text-indigo-300 underline">
                  profile
                </Link>{" "}
                (or import your CV) before running a match.
              </p>
            )}
            {!hasKey && (
              <p className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                No LLM API key configured — add one in{" "}
                <Link href="/settings" className="text-indigo-300 underline">
                  Settings
                </Link>
                .
              </p>
            )}

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
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={!ready}
              className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 py-2.5 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              Start match run
            </button>

            <p className="text-xs leading-relaxed text-zinc-500">
              Keep this tab open during a run — the research agent runs in your
              browser.
            </p>
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
                <li
                  key={r.id}
                  className="rounded-xl border border-white/10 bg-white/[0.03] transition-colors hover:border-indigo-400/40 hover:bg-indigo-500/[0.05]"
                >
                  <div className="flex items-center gap-3 p-4">
                    <Link
                      href={`/runs/view?id=${r.id}`}
                      className="min-w-0 flex-1"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-white">
                            {r.target}
                          </p>
                          <p className="mt-0.5 text-xs text-zinc-500">
                            {new Date(r.created_at).toLocaleString()} ·{" "}
                            {PROVIDERS[r.provider as keyof typeof PROVIDERS]
                              ?.label ?? r.provider}
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
                    <button
                      type="button"
                      title="Delete this run"
                      onClick={() => deleteRun(r.id)}
                      className="shrink-0 rounded-md border border-white/10 px-2.5 py-1.5 text-xs text-zinc-500 transition-colors hover:border-red-400/40 hover:text-red-300"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
