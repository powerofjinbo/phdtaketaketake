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
  onSetupChanged,
  type StoredRun,
} from "@/lib/store";
import { startRun } from "@/lib/research";
import { PROVIDERS } from "@/lib/llm";
import StatusChip, { ACTIVE_STATUSES } from "@/components/StatusChip";
import PageHeader from "@/components/PageHeader";
import {
  IconArrow,
  IconCheck,
  IconCompass,
  IconKey,
  IconTrash,
  IconUser,
} from "@/components/Icons";

const TIER_PRESETS = [
  { value: "top_10", label: "Top 10", hint: "Most selective" },
  { value: "top_20", label: "Top 20", hint: "Broad elite" },
  { value: "top_50", label: "Top 50", hint: "Wide net" },
  { value: "custom", label: "Custom", hint: "Your own list" },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Still up";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return new Date(iso).toLocaleDateString();
}

function targetLabel(t: string): string {
  const p = TIER_PRESETS.find((x) => x.value === t && x.value !== "custom");
  return p ? `${p.label} programs` : t;
}

type TopResult = {
  candidate?: { name?: string; institution?: string };
  difficulty_adjusted_strength?: number;
};

export default function DashboardPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<StoredRun[] | null>(null);
  const [hasProfile, setHasProfile] = useState(true);
  const [hasKey, setHasKey] = useState(true);
  const [name, setName] = useState<string>("");
  const [hello, setHello] = useState("Welcome back");
  const [error, setError] = useState<string | null>(null);

  const [preset, setPreset] = useState("top_10");
  const [schools, setSchools] = useState("");
  const [topK, setTopK] = useState(10);
  const [strict, setStrict] = useState(false);

  useEffect(() => {
    const refresh = () => setRuns(loadRuns());
    const checkSetup = () => {
      const p = loadProfile();
      setHasProfile(!!p);
      setHasKey(!!loadSettings()?.apiKey?.trim());
      const n = typeof p?.name === "string" ? p.name.trim().split(/\s+/)[0] : "";
      setName(n);
    };
    const t = setTimeout(() => {
      refresh();
      checkSetup();
      setHello(greeting());
    }, 0);
    const unsubRuns = onRunsChanged(refresh);
    const unsubSetup = onSetupChanged(checkSetup);
    return () => {
      clearTimeout(t);
      unsubRuns();
      unsubSetup();
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

  const checklist = [
    { done: hasKey, label: "Add an API key", href: "/settings", Icon: IconKey },
    { done: hasProfile, label: "Fill your profile", href: "/profile", Icon: IconUser },
    { done: false, label: "Run your first match", href: null, Icon: IconCompass },
  ];

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <PageHeader
        eyebrow="Dashboard"
        title={
          <>
            {hello}
            {name ? (
              <>
                , <span className="font-display italic font-normal text-[1.1em] ember-text">{name}</span>
              </>
            ) : null}
            .
          </>
        }
      >
        Start a new match run or revisit past results. Everything runs and stays
        in this browser.
      </PageHeader>

      {!ready && (
        <div className="animate-fade-up delay-100 glass mt-8 rounded-2xl p-5">
          <p className="text-sm text-zinc-300">
            Two quick steps before your first run:
          </p>
          <ol className="mt-4 grid gap-3 sm:grid-cols-3">
            {checklist.map((c, i) => {
              const inner = (
                <>
                  <span
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      c.done
                        ? "bg-emerald-400/20 text-emerald-300"
                        : "bg-white/[0.06] text-zinc-400"
                    }`}
                  >
                    {c.done ? <IconCheck className="h-3.5 w-3.5" /> : i + 1}
                  </span>
                  <span className={`flex-1 text-sm ${c.done ? "text-zinc-500 line-through decoration-zinc-600" : "text-zinc-200"}`}>
                    {c.label}
                  </span>
                  {!c.done && c.href && <IconArrow className="h-4 w-4 text-indigo-300" />}
                </>
              );
              return (
                <li key={c.label}>
                  {c.href && !c.done ? (
                    <Link
                      href={c.href}
                      className="flex items-center gap-3 rounded-xl border border-indigo-400/30 bg-indigo-500/[0.08] px-4 py-3 transition-colors hover:border-indigo-300/60 hover:bg-indigo-500/[0.14]"
                    >
                      {inner}
                    </Link>
                  ) : (
                    <div className="flex items-center gap-3 rounded-xl border border-white/[0.07] bg-black/10 px-4 py-3">
                      {inner}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,400px)_1fr]">
        {/* New run form */}
        <form
          onSubmit={onStartRun}
          className="animate-fade-up delay-200 glass relative h-fit overflow-hidden rounded-2xl p-6"
        >
          <div aria-hidden="true" className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-indigo-500/20 blur-3xl" />
          <div className="relative flex items-center gap-3">
            <span className="metal-fill rounded-xl p-2 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)]">
              <IconCompass className="h-5 w-5" />
            </span>
            <h2 className="text-lg font-semibold text-white">New match run</h2>
          </div>

          <div className="relative mt-6 space-y-6">
            <div>
              <span className="field-label">Where are you aiming?</span>
              <div role="radiogroup" className="grid grid-cols-2 gap-2">
                {TIER_PRESETS.map((t) => {
                  const on = preset === t.value;
                  return (
                    <button
                      key={t.value}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      onClick={() => setPreset(t.value)}
                      className={`rounded-xl border px-3.5 py-2.5 text-left transition-all duration-300 ${
                        on
                          ? "border-indigo-300/60 bg-indigo-500/15 shadow-[0_0_0_3px_rgba(99,102,241,0.15)]"
                          : "border-white/[0.08] bg-black/20 hover:border-white/20"
                      }`}
                    >
                      <span className={`block text-sm font-medium ${on ? "text-white" : "text-zinc-300"}`}>
                        {t.label}
                      </span>
                      <span className="block text-xs text-zinc-500">{t.hint}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {preset === "custom" && (
              <div className="animate-fade-up">
                <label className="field-label" htmlFor="schools">
                  School list
                </label>
                <textarea
                  id="schools"
                  value={schools}
                  onChange={(e) => setSchools(e.target.value)}
                  required
                  className="field min-h-20"
                  placeholder="MIT, Stanford, Berkeley…"
                />
              </div>
            )}

            <div>
              <label className="field-label flex items-center justify-between" htmlFor="topk">
                <span>Advisors to rank</span>
                <span className="rounded-md bg-white/[0.06] px-2 py-0.5 font-mono text-sm text-indigo-200">
                  {topK}
                </span>
              </label>
              <input
                id="topk"
                type="range"
                min={3}
                max={30}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="range mt-2"
                style={{ "--fill": `${((topK - 3) / 27) * 100}%` } as React.CSSProperties}
              />
              <div className="mt-1.5 flex justify-between text-[11px] text-zinc-600">
                <span>3 · focused</span>
                <span>30 · exhaustive</span>
              </div>
            </div>

            <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-white/[0.08] bg-black/20 px-4 py-3.5 transition-colors hover:border-white/15">
              <span>
                <span className="block text-sm text-zinc-200">Strict evidence mode</span>
                <span className="block text-xs leading-relaxed text-zinc-500">
                  Only fully sourced signals count toward scores.
                </span>
              </span>
              <input
                type="checkbox"
                checked={strict}
                onChange={(e) => setStrict(e.target.checked)}
                className="toggle"
              />
            </label>

            {error && (
              <p className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={!ready}
              className="btn-primary group w-full rounded-xl py-3 font-medium"
            >
              {ready ? "Start match run" : "Finish setup to start"}
              {ready && (
                <IconArrow className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
              )}
            </button>

            <p className="text-center text-xs leading-relaxed text-zinc-500">
              Keep this tab open during a run. The research agent lives in your
              browser.
            </p>
          </div>
        </form>

        {/* Runs list */}
        <div className="animate-fade-up delay-300">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-lg font-semibold text-white">Your runs</h2>
            {runs && runs.length > 0 && (
              <span className="text-xs text-zinc-500">
                {runs.length} saved in this browser
              </span>
            )}
          </div>
          {runs === null ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="glass relative h-[84px] overflow-hidden rounded-2xl">
                  <div className="animate-scan absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
                </div>
              ))}
            </div>
          ) : runs.length === 0 ? (
            <div className="relative flex flex-col items-center overflow-hidden rounded-2xl border border-dashed border-white/[0.12] px-8 py-16 text-center">
              <svg viewBox="0 0 120 80" className="h-20 w-32 text-indigo-300/60" aria-hidden="true">
                <path d="M20 60 Q45 20 60 40 T100 22" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="3 5" className="flow-dash" />
                <circle cx="20" cy="60" r="5" fill="#fbbf77" />
                <circle cx="60" cy="40" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
                <circle cx="100" cy="22" r="4.5" fill="none" stroke="#67e8f9" strokeWidth="1.4" />
              </svg>
              <p className="font-display mt-4 text-xl italic text-zinc-200">
                Every map starts with a single point.
              </p>
              <p className="mt-2 max-w-xs text-sm text-zinc-500">
                Your runs will appear here. Start your first one on the left.
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {runs.map((r) => {
                const top = (r.results?.[0] ?? null) as TopResult | null;
                const active = ACTIVE_STATUSES.includes(r.status);
                return (
                  <li key={r.id} className="glass-card spotlight group rounded-2xl">
                    <div className="flex items-center gap-4 p-4 sm:p-5">
                      <Link href={`/runs/view?id=${r.id}`} className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate font-medium text-white">
                              {targetLabel(r.target)}
                              <span className="ml-2 text-xs font-normal text-zinc-500">
                                top {r.top_k}
                                {r.strict ? " · strict" : ""}
                              </span>
                            </p>
                            <p className="mt-1 text-xs text-zinc-500">
                              {relativeTime(r.created_at)} ·{" "}
                              {PROVIDERS[r.provider as keyof typeof PROVIDERS]?.label ?? r.provider}
                            </p>
                          </div>
                          <StatusChip status={r.status} />
                        </div>
                        {active && r.progress_note && (
                          <div className="mt-3">
                            <div className="relative h-1 overflow-hidden rounded-full bg-white/[0.06]">
                              <div className="animate-scan absolute inset-y-0 w-1/3 rounded-full bg-gradient-to-r from-transparent via-indigo-300/80 to-transparent" />
                            </div>
                            <p className="mt-2 truncate text-xs text-indigo-200/80">{r.progress_note}</p>
                          </div>
                        )}
                        {r.status === "done" && top?.candidate?.name && (
                          <p className="mt-3 flex items-center gap-2 text-xs text-zinc-400">
                            <span className="rounded-md bg-emerald-400/10 px-1.5 py-0.5 font-mono text-emerald-300">
                              #1
                            </span>
                            <span className="truncate">
                              {top.candidate.name}
                              {top.candidate.institution ? ` · ${top.candidate.institution}` : ""}
                            </span>
                            {typeof top.difficulty_adjusted_strength === "number" && (
                              <span className="ml-auto shrink-0 font-mono text-indigo-200">
                                {top.difficulty_adjusted_strength.toFixed(2)}
                              </span>
                            )}
                          </p>
                        )}
                      </Link>
                      <button
                        type="button"
                        title="Delete this run"
                        aria-label="Delete this run"
                        onClick={() => deleteRun(r.id)}
                        className="shrink-0 rounded-lg border border-transparent p-2 text-zinc-600 opacity-60 transition-all hover:border-rose-400/30 hover:bg-rose-500/10 hover:text-rose-300 group-hover:opacity-100"
                      >
                        <IconTrash />
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
