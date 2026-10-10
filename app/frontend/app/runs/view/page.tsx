"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import type { ApplyBucket, MatchResult } from "@/lib/types";
import { getRun, onRunsChanged, type StoredRun } from "@/lib/store";
import { onEngineStatus } from "@/lib/engine";
import StatusChip, { ACTIVE_STATUSES } from "@/components/StatusChip";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import { IconArrow, IconCheck, IconChart, IconDoc, IconHeart, IconSpark } from "@/components/Icons";

const BUCKETS: ApplyBucket[] = ["priority", "target", "reach", "only_if_space", "drop"];

const BUCKET_STYLES: Record<ApplyBucket, string> = {
  priority: "bg-emerald-500/12 text-emerald-200 border-emerald-400/35",
  target: "bg-sky-500/12 text-sky-200 border-sky-400/35",
  reach: "bg-amber-500/12 text-amber-200 border-amber-400/35",
  only_if_space: "bg-zinc-500/12 text-zinc-300 border-zinc-400/30",
  drop: "bg-rose-500/12 text-rose-200 border-rose-400/35",
};

const BUCKET_FILL: Record<ApplyBucket, string> = {
  priority: "bg-emerald-400",
  target: "bg-sky-400",
  reach: "bg-amber-300",
  only_if_space: "bg-zinc-500",
  drop: "bg-rose-400",
};

const BUCKET_LABELS: Record<ApplyBucket, string> = {
  priority: "Priority",
  target: "Target",
  reach: "Reach",
  only_if_space: "Only if space",
  drop: "Drop",
};

const pct = (v: number) => `${Math.min(100, Math.max(0, (v / 4) * 100))}%`;

/** Ring gauge for the primary sort key (difficulty-adjusted strength, 0–4). */
function ScoreRing({ value, size = 84 }: { value: number; size?: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const frac = Math.min(1, Math.max(0, value / 4));
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <defs>
          <linearGradient id="ring-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#818cf8" />
            <stop offset="0.6" stopColor="#a78bfa" />
            <stop offset="1" stopColor="#67e8f9" />
          </linearGradient>
        </defs>
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="6" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="url(#ring-g)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - frac)}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-lg font-semibold leading-none text-white">
          {value.toFixed(2)}
        </span>
        <span className="mt-0.5 text-[9px] uppercase tracking-wider text-zinc-500">of 4.0</span>
      </div>
    </div>
  );
}

/** The score cascade on one 0–4 track: band, strength, risk, difficulty. */
function StrengthTrack({ result }: { result: MatchResult }) {
  const lo = Math.max(0, result.application_strength - result.confidence_band);
  const hi = Math.min(4, result.application_strength + result.confidence_band);
  const marks = [
    { v: result.application_strength, label: "Strength", cls: "bg-white" },
    { v: result.risk_adjusted_strength, label: "Risk-adj.", cls: "bg-violet-300" },
    { v: result.difficulty_adjusted_strength, label: "Difficulty-adj.", cls: "bg-cyan-300" },
  ];
  return (
    <div>
      <div className="relative h-2.5 w-full rounded-full bg-white/[0.06]">
        <div
          className="absolute inset-y-0 rounded-full bg-indigo-400/20 ring-1 ring-inset ring-indigo-300/20"
          style={{ left: pct(lo), width: `calc(${pct(hi)} - ${pct(lo)})` }}
          title={`Confidence band ${lo.toFixed(2)}–${hi.toFixed(2)}`}
        />
        <div
          className="animate-bar-grow absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400 opacity-80"
          style={{ width: pct(result.difficulty_adjusted_strength) }}
        />
        {marks.map((m) => (
          <span
            key={m.label}
            title={`${m.label} ${m.v.toFixed(2)}`}
            className={`absolute top-1/2 h-4 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.4)] ${m.cls}`}
            style={{ left: pct(m.v) }}
          />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-zinc-600">
        {[0, 1, 2, 3, 4].map((n) => (
          <span key={n}>{n}</span>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-zinc-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-1 rounded-full bg-white" />
          Strength <span className="font-mono text-zinc-200">{result.application_strength.toFixed(2)}</span>
          <span className="text-zinc-600">±{result.confidence_band.toFixed(2)}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-1 rounded-full bg-violet-300" />
          Risk-adjusted <span className="font-mono text-zinc-200">{result.risk_adjusted_strength.toFixed(2)}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-1 rounded-full bg-cyan-300" />
          Difficulty-adjusted <span className="font-mono text-zinc-200">{result.difficulty_adjusted_strength.toFixed(2)}</span>
        </span>
        <span>
          Lower bound <span className="font-mono text-zinc-200">{result.lower_bound.toFixed(2)}</span>
        </span>
        {result.research_fit_score != null && (
          <span>
            Research fit <span className="font-mono text-zinc-200">{result.research_fit_score.toFixed(2)}</span>
          </span>
        )}
      </div>
    </div>
  );
}

function RisksSection({ result }: { result: MatchResult }) {
  const [open, setOpen] = useState(false);
  const count = result.missing_signal_names.length + result.unsourced_signal_names.length;
  if (count === 0) {
    return (
      <p className="mt-5 flex items-center gap-2 text-xs text-emerald-300/80">
        <IconCheck className="h-3.5 w-3.5" />
        Every signal for this advisor is backed by a source.
      </p>
    );
  }
  return (
    <div className="mt-5 overflow-hidden rounded-xl border border-white/[0.08] bg-black/20">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-sm text-zinc-300 transition-colors hover:bg-white/[0.03] hover:text-white"
      >
        <span className="flex items-center gap-2">
          What we couldn&apos;t verify
          <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-xs text-amber-200">{count}</span>
        </span>
        <span className={`text-zinc-500 transition-transform duration-300 ${open ? "rotate-180" : ""}`}>▾</span>
      </button>
      <div className={`grid transition-[grid-template-rows] duration-500 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className="overflow-hidden">
          <div className="space-y-4 border-t border-white/[0.08] px-4 py-4 text-sm">
            {result.missing_signal_names.length > 0 && (
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <span className="h-2 w-2 rounded-full border border-dashed border-zinc-400" />
                  Not found · widened the band instead of guessing
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.missing_signal_names.map((s) => (
                    <span key={s} className="rounded-md border border-dashed border-zinc-600 px-2 py-0.5 text-xs text-zinc-300">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {result.unsourced_signal_names.length > 0 && (
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <span className="h-2 w-2 rounded-full bg-amber-300" />
                  Claimed without a citable source · treated as uncertain
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.unsourced_signal_names.map((s) => (
                    <span key={s} className="rounded-md border border-amber-400/30 bg-amber-500/[0.06] px-2 py-0.5 text-xs text-amber-100/90">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultCard({ result, rank }: { result: MatchResult; rank: number }) {
  const top = rank === 1;
  return (
    <article
      className={`glass spotlight animate-fade-up rounded-2xl p-6 sm:p-7 ${top ? "aurora-border" : ""}`}
      style={{ animationDelay: `${Math.min(rank, 8) * 70}ms` }}
    >
      <div className="flex flex-wrap items-start gap-5">
        <ScoreRing value={result.difficulty_adjusted_strength} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`font-mono text-xs ${top ? "text-amber-200" : "text-zinc-500"}`}>
              #{rank}
              {top && " · best fit"}
            </span>
            {result.strategy && (
              <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${BUCKET_STYLES[result.strategy.apply_bucket]}`}>
                {BUCKET_LABELS[result.strategy.apply_bucket]}
              </span>
            )}
            <span className="rounded-full border border-violet-400/30 bg-violet-500/10 px-2.5 py-0.5 text-xs font-medium text-violet-200">
              {result.strength_label}
            </span>
          </div>
          <h3 className="mt-2 text-xl font-semibold tracking-tight text-white">{result.candidate.name}</h3>
          <p className="mt-0.5 text-sm text-zinc-400">
            {result.candidate.institution}
            <span className="ml-2 text-xs text-zinc-600">tier {result.candidate.school_tier}</span>
          </p>
          {result.candidate.research_areas.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {result.candidate.research_areas.map((a) => (
                <span key={a} className="rounded-md bg-white/[0.05] px-2 py-0.5 text-xs text-zinc-400">
                  {a}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6">
        <StrengthTrack result={result} />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div>
          <h4 className="mb-1.5 flex items-center gap-2 text-sm font-medium text-zinc-200">
            <IconChart className="h-4 w-4 text-indigo-300" />
            Why ranked here
          </h4>
          <p className="text-sm leading-relaxed text-zinc-400">{result.explanation}</p>
        </div>
        {result.research_fit_summary && (
          <div>
            <h4 className="mb-1.5 flex items-center gap-2 text-sm font-medium text-zinc-200">
              <IconDoc className="h-4 w-4 text-cyan-300" />
              Research fit
            </h4>
            <p className="text-sm leading-relaxed text-zinc-400">{result.research_fit_summary}</p>
          </div>
        )}
      </div>

      {result.strategy && (
        <div className="mt-5 rounded-xl border border-amber-300/20 bg-gradient-to-r from-amber-400/[0.07] to-transparent px-4 py-3.5 text-sm">
          <p className="flex items-center gap-2 font-medium text-amber-100">
            <IconSpark className="h-4 w-4 text-amber-300" />
            Your next move
          </p>
          <p className="mt-1.5 leading-relaxed text-zinc-300">{result.strategy.recommended_action}</p>
          {result.strategy.outreach_angle && (
            <p className="mt-2 leading-relaxed text-zinc-400">
              <span className="text-zinc-200">Outreach angle: </span>
              {result.strategy.outreach_angle}
            </p>
          )}
        </div>
      )}

      <RisksSection result={result} />
    </article>
  );
}

const STAGES = [
  { key: "researching", label: "Research", hint: "Reading primary sources" },
  { key: "scoring", label: "Score", hint: "Running the engine locally" },
  { key: "done", label: "Report", hint: "Your ranked map" },
];

function ProgressPanel({ run, engineNote }: { run: StoredRun; engineNote: string | null }) {
  const current = STAGES.findIndex((s) => s.key === run.status);
  const lines = run.activity?.slice(-7) ?? [];
  return (
    <div className="glass-strong mt-8 overflow-hidden rounded-2xl">
      <div className="relative h-0.5 overflow-hidden bg-white/[0.04]">
        <div className="animate-scan absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-cyan-300 to-transparent" />
      </div>
      <div className="p-6 sm:p-8">
        <ol className="flex items-center">
          {STAGES.map((s, i) => {
            const done = i < current;
            const now = i === current;
            return (
              <li key={s.key} className={`flex items-center ${i < STAGES.length - 1 ? "flex-1" : ""}`}>
                <div className="flex items-center gap-3">
                  <span
                    className={`relative flex h-9 w-9 items-center justify-center rounded-full border text-sm font-semibold transition-all duration-500 ${
                      done
                        ? "border-emerald-400/40 bg-emerald-400/15 text-emerald-300"
                        : now
                          ? "border-indigo-300/60 bg-indigo-500/20 text-white"
                          : "border-white/10 bg-white/[0.03] text-zinc-600"
                    }`}
                  >
                    {now && <span className="pulse-ring absolute inset-0 rounded-full border border-indigo-300/60" />}
                    {done ? <IconCheck /> : i + 1}
                  </span>
                  <span className="hidden sm:block">
                    <span className={`block text-sm font-medium ${now ? "text-white" : done ? "text-zinc-300" : "text-zinc-600"}`}>
                      {s.label}
                    </span>
                    <span className="block text-xs text-zinc-500">{s.hint}</span>
                  </span>
                </div>
                {i < STAGES.length - 1 && (
                  <span className="relative mx-3 h-px flex-1 overflow-hidden bg-white/10 sm:mx-5">
                    {done && <span className="absolute inset-0 bg-emerald-400/50" />}
                    {now && <span className="flow-dash absolute inset-0 border-t border-dashed border-indigo-300/70" />}
                  </span>
                )}
              </li>
            );
          })}
        </ol>

        <p className="mt-7 text-center text-[0.95rem] font-medium text-zinc-100">
          {run.progress_note || "Working on your match run…"}
        </p>
        {engineNote && <p className="mt-1.5 text-center text-xs text-violet-300/90">{engineNote}</p>}

        {lines.length > 0 && (
          <div className="mx-auto mt-6 max-w-xl rounded-xl border border-white/[0.07] bg-black/40 p-4 font-mono text-xs">
            <div className="mb-3 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-rose-400/60" />
              <span className="h-2 w-2 rounded-full bg-amber-300/60" />
              <span className="h-2 w-2 rounded-full bg-emerald-400/60" />
              <span className="ml-2 text-[10px] uppercase tracking-wider text-zinc-600">agent activity</span>
            </div>
            <ul className="space-y-1.5">
              {lines.map((line, i, arr) => {
                const last = i === arr.length - 1;
                return (
                  <li
                    key={`${i}-${line}`}
                    className={`flex items-start gap-2 ${last ? "text-cyan-100" : "text-zinc-500"}`}
                    style={{ opacity: last ? 1 : 0.45 + (i / arr.length) * 0.5 }}
                  >
                    <span className={last ? "text-cyan-300" : "text-zinc-700"}>{last ? "›" : "·"}</span>
                    <span className="break-words">
                      {line}
                      {last && <span className="caret text-cyan-300" aria-hidden="true" />}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <p className="mt-6 text-center text-xs text-zinc-500">
          Runs in this browser, so keep the tab open. Updates appear automatically.
          <span className="block pt-1 text-zinc-600">Good things take a minute. Maybe stretch, or refill your tea.</span>
        </p>
      </div>
    </div>
  );
}

function ResultsOverview({
  results,
  filter,
  setFilter,
}: {
  results: MatchResult[];
  filter: ApplyBucket | "all";
  setFilter: (f: ApplyBucket | "all") => void;
}) {
  const counts = useMemo(() => {
    const c: Record<ApplyBucket, number> = { priority: 0, target: 0, reach: 0, only_if_space: 0, drop: 0 };
    for (const r of results) if (r.strategy) c[r.strategy.apply_bucket]++;
    return c;
  }, [results]);
  const bucketed = BUCKETS.reduce((n, b) => n + counts[b], 0);
  const best = results.reduce((m, r) => Math.max(m, r.difficulty_adjusted_strength), 0);
  const fullySourced = results.filter(
    (r) => r.missing_signal_names.length + r.unsourced_signal_names.length === 0
  ).length;

  const stats = [
    { k: "Advisors ranked", v: String(results.length) },
    { k: "Best fit", v: best.toFixed(2) },
    { k: "Fully sourced", v: `${fullySourced}/${results.length}` },
  ];

  return (
    <section className="glass mt-8 rounded-2xl p-6">
      <div className="grid grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.k}>
            <p className="font-mono text-2xl font-semibold text-white sm:text-3xl">{s.v}</p>
            <p className="mt-1 text-xs text-zinc-500">{s.k}</p>
          </div>
        ))}
      </div>
      {bucketed > 0 && (
        <>
          <div className="mt-6 flex h-2 w-full gap-0.5 overflow-hidden rounded-full">
            {BUCKETS.filter((b) => counts[b] > 0).map((b) => (
              <span
                key={b}
                className={`animate-bar-grow h-full ${BUCKET_FILL[b]}`}
                style={{ width: `${(counts[b] / bucketed) * 100}%` }}
              />
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                filter === "all" ? "border-white/30 bg-white/10 text-white" : "border-white/10 text-zinc-400 hover:text-white"
              }`}
            >
              All · {results.length}
            </button>
            {BUCKETS.filter((b) => counts[b] > 0).map((b) => (
              <button
                key={b}
                type="button"
                onClick={() => setFilter(filter === b ? "all" : b)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors ${
                  filter === b ? BUCKET_STYLES[b] : "border-white/10 text-zinc-400 hover:text-white"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_FILL[b]}`} />
                {BUCKET_LABELS[b]} · {counts[b]}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function RunView() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  const [run, setRun] = useState<StoredRun | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [engineNote, setEngineNote] = useState<string | null>(null);
  const [filter, setFilter] = useState<ApplyBucket | "all">("all");

  useEffect(() => {
    const refresh = () => setRun(id ? getRun(id) : null);
    const t = setTimeout(() => {
      refresh();
      setLoaded(true);
    }, 0);
    if (!id) return () => clearTimeout(t);
    const unsubRuns = onRunsChanged(refresh);
    const unsubEngine = onEngineStatus((note) => setEngineNote(note));
    return () => {
      clearTimeout(t);
      unsubRuns();
      unsubEngine();
    };
  }, [id]);

  const notFound = loaded && (!id || !run);
  const results = ((run?.results ?? []) as unknown as MatchResult[]) || [];
  const ranked = results.map((r, i) => ({ r, rank: i + 1 }));
  const shown = filter === "all" ? ranked : ranked.filter(({ r }) => r.strategy?.apply_bucket === filter);

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <Link
        href="/dashboard"
        className="group inline-flex items-center gap-1.5 text-sm text-zinc-500 transition-colors hover:text-indigo-200"
      >
        <IconArrow className="h-3.5 w-3.5 rotate-180 transition-transform group-hover:-translate-x-0.5" />
        Dashboard
      </Link>

      {notFound && (
        <p className="mt-6 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {!id
            ? "No run id provided."
            : "This run was not found in this browser. Runs live in local storage on the device that started them."}{" "}
          <Link href="/dashboard" className="text-indigo-300 underline">
            Back to dashboard
          </Link>
        </p>
      )}

      {!loaded && <p className="mt-10 text-sm text-zinc-500">Loading run…</p>}

      {run && (
        <>
          <div className="animate-fade-up mt-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow">Match run</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {run.status === "done" ? (
                  <>
                    Your <span className="font-display italic font-normal text-[1.1em] metal-text">advisor map</span>
                  </>
                ) : run.status === "error" ? (
                  "This run stopped"
                ) : (
                  "Mapping your network…"
                )}
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                {new Date(run.created_at).toLocaleString()} · top {run.top_k}
                {run.strict ? " · strict evidence" : ""}
              </p>
            </div>
            <StatusChip status={run.status} />
          </div>

          {ACTIVE_STATUSES.includes(run.status) && <ProgressPanel run={run} engineNote={engineNote} />}

          {run.status === "error" && (
            <div className="mt-8 rounded-2xl border border-rose-400/30 bg-rose-500/[0.08] p-5 text-sm text-rose-100">
              <p>{run.error || "This run failed. Please start a new one."}</p>
              <p className="pt-3 text-rose-200/70">
                Check your key in{" "}
                <Link href="/settings" className="text-indigo-300 underline">
                  Settings
                </Link>{" "}
                or start a new run from the{" "}
                <Link href="/dashboard" className="text-indigo-300 underline">
                  Dashboard
                </Link>
                . Nothing you entered was lost.
              </p>
            </div>
          )}

          {run.status === "done" && (
            <>
              {run.notice && (
                <p className="mt-8 rounded-xl border border-amber-400/30 bg-amber-500/[0.08] px-5 py-4 text-sm text-amber-100/90">
                  <span className="font-medium text-amber-300">Heads up: </span>
                  {run.notice}
                </p>
              )}

              {results.length > 0 && <ResultsOverview results={results} filter={filter} setFilter={setFilter} />}

              {run.portfolio_summary && (
                <section className="glass-strong mt-6 rounded-2xl p-6">
                  <h2 className="eyebrow">Portfolio summary</h2>
                  <p className="mt-3 leading-relaxed text-zinc-200">{run.portfolio_summary}</p>
                </section>
              )}

              {run.field_caveats.length > 0 && (
                <section className="mt-6 rounded-2xl border border-violet-400/20 bg-violet-500/[0.06] px-6 py-5">
                  <h2 className="text-sm font-medium text-violet-200">Field notes</h2>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-zinc-400">
                    {run.field_caveats.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </section>
              )}

              <div className="mt-8 space-y-6">
                {shown.map(({ r, rank }) => (
                  <ResultCard key={`${r.candidate.name}-${r.candidate.institution}`} result={r} rank={rank} />
                ))}
                {results.length === 0 && (
                  <p className="text-sm text-zinc-500">No results were produced for this run.</p>
                )}
              </div>

              {results.length > 0 && (
                <div className="mt-12 text-center">
                  <IconHeart className="mx-auto h-5 w-5 text-rose-300/80" />
                  <p className="font-display mx-auto mt-3 max-w-lg text-xl italic leading-snug text-zinc-200">
                    A number can&apos;t capture who you are. Use this map to choose
                    where to knock, then let your work speak.
                  </p>
                  <p className="mt-2 text-sm text-zinc-500">分数只是地图，路要你自己走。祝你申请顺利。</p>
                </div>
              )}

              <DisclaimerFooter />
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function RunViewPage() {
  return (
    <Suspense
      fallback={<div className="mx-auto max-w-4xl px-6 py-12 text-sm text-zinc-500">Loading run…</div>}
    >
      <RunView />
    </Suspense>
  );
}
