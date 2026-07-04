"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  api,
  type ApplyBucket,
  type MatchResult,
  type RunDetail,
} from "@/lib/api";
import StatusChip, { ACTIVE_STATUSES } from "@/components/StatusChip";
import DisclaimerFooter from "@/components/DisclaimerFooter";

const BUCKET_STYLES: Record<ApplyBucket, string> = {
  priority: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  target: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  reach: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  only_if_space: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
  drop: "bg-red-500/15 text-red-300 border-red-500/30",
};

const BUCKET_LABELS: Record<ApplyBucket, string> = {
  priority: "Priority",
  target: "Target",
  reach: "Reach",
  only_if_space: "Only if space",
  drop: "Drop",
};

function StrengthBar({ result }: { result: MatchResult }) {
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / 4) * 100))}%`;
  const lo = Math.max(0, result.application_strength - result.confidence_band);
  const hi = Math.min(4, result.application_strength + result.confidence_band);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-zinc-500">
        <span>
          Application strength{" "}
          <span className="font-mono text-zinc-300">
            {result.application_strength.toFixed(2)}
          </span>{" "}
          <span className="text-zinc-500">
            ±{result.confidence_band.toFixed(2)}
          </span>
        </span>
        <span>
          Difficulty-adjusted{" "}
          <span className="font-mono text-indigo-300">
            {result.difficulty_adjusted_strength.toFixed(2)}
          </span>
        </span>
      </div>
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-white/5">
        {/* confidence band */}
        <div
          className="absolute inset-y-0 rounded-full bg-indigo-400/25"
          style={{ left: pct(lo), width: `calc(${pct(hi)} - ${pct(lo)})` }}
        />
        {/* point estimate */}
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
          style={{ width: pct(result.application_strength) }}
        />
        {/* point marker */}
        <div
          className="absolute top-1/2 h-3.5 w-1 -translate-y-1/2 rounded-full bg-white shadow"
          style={{ left: pct(result.application_strength) }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-zinc-600">
        <span>0</span>
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
      </div>
    </div>
  );
}

function RisksSection({ result }: { result: MatchResult }) {
  const [open, setOpen] = useState(false);
  const count =
    result.missing_signal_names.length + result.unsourced_signal_names.length;
  if (count === 0) return null;
  return (
    <div className="mt-4 rounded-lg border border-white/10 bg-black/20">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-zinc-300 hover:text-white"
      >
        <span>
          Main risks{" "}
          <span className="ml-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-300">
            {count}
          </span>
        </span>
        <span
          className={`text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-white/10 px-4 py-3 text-sm">
          {result.missing_signal_names.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Signals we could not find
              </p>
              <ul className="list-inside list-disc space-y-1 text-zinc-300">
                {result.missing_signal_names.map((s) => (
                  <li key={s}>
                    {s} — no evidence found, so this widened the confidence
                    band instead of being guessed.
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.unsourced_signal_names.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Signals without a verifiable source
              </p>
              <ul className="list-inside list-disc space-y-1 text-zinc-300">
                {result.unsourced_signal_names.map((s) => (
                  <li key={s}>
                    {s} — claimed but not backed by a citable source, so it is
                    treated as uncertain.
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result, rank }: { result: MatchResult; rank: number }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/25 to-violet-600/25 font-mono text-sm font-semibold text-indigo-300">
            #{rank}
          </span>
          <div>
            <h3 className="text-lg font-semibold text-white">
              {result.candidate.name}
            </h3>
            <p className="text-sm text-zinc-400">
              {result.candidate.institution}
              <span className="ml-2 text-xs text-zinc-600">
                School tier {result.candidate.school_tier}
              </span>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-violet-400/30 bg-violet-500/10 px-2.5 py-0.5 text-xs font-medium text-violet-300">
            {result.strength_label}
          </span>
          {result.strategy && (
            <span
              className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${BUCKET_STYLES[result.strategy.apply_bucket]}`}
            >
              {BUCKET_LABELS[result.strategy.apply_bucket]}
            </span>
          )}
        </div>
      </div>

      {result.candidate.research_areas.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.candidate.research_areas.map((a) => (
            <span
              key={a}
              className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-zinc-400"
            >
              {a}
            </span>
          ))}
        </div>
      )}

      <div className="mt-5">
        <StrengthBar result={result} />
      </div>

      <div className="mt-4 grid gap-1 text-xs text-zinc-500 sm:grid-cols-3">
        <span>
          Risk-adjusted:{" "}
          <span className="font-mono text-zinc-300">
            {result.risk_adjusted_strength.toFixed(2)}
          </span>
        </span>
        <span>
          Lower bound:{" "}
          <span className="font-mono text-zinc-300">
            {result.lower_bound.toFixed(2)}
          </span>
        </span>
        {result.research_fit_score != null && (
          <span>
            Research fit:{" "}
            <span className="font-mono text-zinc-300">
              {result.research_fit_score.toFixed(2)}
            </span>
          </span>
        )}
      </div>

      <div className="mt-4">
        <h4 className="mb-1 text-sm font-medium text-zinc-200">
          Why ranked here
        </h4>
        <p className="text-sm leading-relaxed text-zinc-400">
          {result.explanation}
        </p>
      </div>

      {result.research_fit_summary && (
        <div className="mt-4 rounded-lg border border-indigo-400/20 bg-indigo-500/[0.06] px-4 py-3">
          <h4 className="mb-1 text-sm font-medium text-indigo-300">
            Research fit
          </h4>
          <p className="text-sm leading-relaxed text-zinc-300">
            {result.research_fit_summary}
          </p>
        </div>
      )}

      {result.strategy && (
        <div className="mt-4 text-sm text-zinc-400">
          <span className="font-medium text-zinc-200">Recommended:</span>{" "}
          {result.strategy.recommended_action}
          {result.strategy.outreach_angle && (
            <>
              {" "}
              <span className="font-medium text-zinc-200">
                Outreach angle:
              </span>{" "}
              {result.strategy.outreach_angle}
            </>
          )}
        </div>
      )}

      <RisksSection result={result} />
    </article>
  );
}

function RunView() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const detail = await api<RunDetail>(`/runs/${id}`);
        if (cancelled) return;
        setRun(detail);
        setError(null);
        if (ACTIVE_STATUSES.includes(detail.status)) {
          timer = setTimeout(poll, 3000);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load run");
      }
    }
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <Link
        href="/dashboard"
        className="text-sm text-zinc-500 transition-colors hover:text-indigo-300"
      >
        ← Back to dashboard
      </Link>

      {(error || !id) && (
        <p className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {id ? error : "No run id provided."}
        </p>
      )}

      {id && !run && !error && (
        <p className="mt-10 text-sm text-zinc-500">Loading run…</p>
      )}

      {run && (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-white">Match run</h1>
            <StatusChip status={run.status} />
          </div>

          {ACTIVE_STATUSES.includes(run.status) && (
            <div className="mt-8 rounded-2xl border border-indigo-400/20 bg-indigo-500/[0.06] p-8 text-center">
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-indigo-400/30 border-t-indigo-400" />
              <p className="text-sm text-zinc-300">
                {run.progress_note || "Working on your match run…"}
              </p>
              <p className="mt-2 text-xs text-zinc-500">
                Updates automatically every few seconds.
              </p>
            </div>
          )}

          {run.status === "error" && (
            <p className="mt-8 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {run.error || "This run failed. Please start a new one."}
            </p>
          )}

          {run.status === "done" && (
            <>
              {run.portfolio_summary && (
                <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                  <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-indigo-300">
                    Portfolio summary
                  </h2>
                  <p className="leading-relaxed text-zinc-300">
                    {run.portfolio_summary}
                  </p>
                </section>
              )}

              <div className="mt-8 space-y-6">
                {(run.results ?? []).map((r, i) => (
                  <ResultCard
                    key={`${r.candidate.name}-${r.candidate.institution}`}
                    result={r}
                    rank={i + 1}
                  />
                ))}
                {(run.results ?? []).length === 0 && (
                  <p className="text-sm text-zinc-500">
                    No results were produced for this run.
                  </p>
                )}
              </div>

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
      fallback={
        <div className="mx-auto max-w-4xl px-6 py-12 text-sm text-zinc-500">
          Loading run…
        </div>
      }
    >
      <RunView />
    </Suspense>
  );
}
