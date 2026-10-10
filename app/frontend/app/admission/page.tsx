"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import PageHeader from "@/components/PageHeader";
import { IconBook, IconChart, IconDoc, IconPlus, IconTrash, IconUpload, IconUser } from "@/components/Icons";
import { loadProfile, loadSettings } from "@/lib/store";
import { fileToText } from "@/lib/pdf";
import { normalizeProfile } from "@/lib/research";
import type { Advisor, GpaScale, Paper, PaperStatus } from "@/lib/types";
import {
  type AdmissionDraft,
  type AdmissionEstimate,
  type ContactStatus,
  type Fellowship,
  type LetterWriter,
  type Prominence,
  type SchoolTier,
  type Stage,
  type StoredAdmissionResult,
  type TargetDraft,
  type UndergradTier,
  emptyDraft,
  loadAdmissionResult,
  loadDraft,
  missingRequired,
  newTarget,
  parseCv,
  parseTranscript,
  readSop,
  runAdmission,
  saveDraft,
} from "@/lib/admission";

const labelCls = "field-label";
const removeBtnCls =
  "inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs text-zinc-400 transition-colors hover:border-rose-400/40 hover:bg-rose-500/10 hover:text-rose-200";
const addBtnCls =
  "group flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-indigo-300/30 px-4 py-3 text-sm text-indigo-200 transition-all hover:border-indigo-300/60 hover:bg-indigo-500/[0.08]";
const itemCls = "rounded-xl border border-white/[0.08] bg-black/20 p-4";

const GPA_SCALES: { value: GpaScale; label: string }[] = [
  { value: "4.0", label: "4.0 scale" },
  { value: "4.3", label: "4.3 scale" },
  { value: "4.5", label: "4.5 scale" },
  { value: "100", label: "100-point scale" },
  { value: "uk", label: "UK honours" },
];
const PAPER_STATUSES: PaperStatus[] = ["published", "accepted", "in_press", "submitted", "preprint", "in_prep"];
const TIERS: { value: "" | SchoolTier; label: string }[] = [
  { value: "", label: "Auto (from research)" },
  { value: "top_10", label: "Top 10" },
  { value: "top_11_30", label: "Top 11–30" },
  { value: "top_31_60", label: "Top 31–60" },
  { value: "top_60_plus", label: "Top 60+" },
];
const CONTACT: { value: ContactStatus; label: string }[] = [
  { value: "none", label: "No contact yet" },
  { value: "emailed_no_reply", label: "Emailed, no reply" },
  { value: "positive_reply", label: "Positive reply" },
  { value: "meeting_held", label: "Had a meeting" },
  { value: "pi_invited_application", label: "PI invited me to apply" },
];
const STAGES: { value: Stage; label: string }[] = [
  { value: "pre_application", label: "Before decisions" },
  { value: "interview", label: "Interview invited" },
  { value: "waitlist", label: "Waitlisted" },
];
const UG_TIERS: { value: UndergradTier; label: string }[] = [
  { value: "unknown", label: "Prefer not to say" },
  { value: "elite", label: "Elite (e.g. top-20 US, C9, Oxbridge)" },
  { value: "strong", label: "Strong (e.g. top-60 US, 985)" },
  { value: "regular", label: "Other" },
];
const PROMINENCE: { value: Prominence; label: string }[] = [
  { value: "field_leader", label: "Field leader" },
  { value: "established", label: "Established faculty" },
  { value: "junior_or_unknown", label: "Junior / less known" },
];
const VERDICT: Record<AdmissionEstimate["verdict"], { label: string; cls: string }> = {
  strong: { label: "Strong", cls: "bg-emerald-400/15 text-emerald-200 border-emerald-300/30" },
  competitive: { label: "Competitive", cls: "bg-cyan-400/15 text-cyan-200 border-cyan-300/30" },
  possible: { label: "Possible", cls: "bg-indigo-400/15 text-indigo-200 border-indigo-300/30" },
  reach: { label: "Reach", cls: "bg-amber-400/15 text-amber-200 border-amber-300/30" },
  long_shot: { label: "Long shot", cls: "bg-rose-400/15 text-rose-200 border-rose-300/30" },
};

const pct = (p: number) => `${Math.round(p * 100)}%`;

function Section({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="glass spotlight rounded-2xl p-6 sm:p-7">
      <div className="flex items-start gap-3.5">
        <span className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-indigo-200">{icon}</span>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-zinc-500">{subtitle}</p>}
        </div>
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function Req() {
  return <span className="ml-1 text-rose-300/80">*</span>;
}

type DocKind = "cv" | "sop" | "transcript";

function DocTile({
  title,
  hint,
  required,
  status,
  busy,
  onFile,
}: {
  title: string;
  hint: string;
  required?: boolean;
  status?: string;
  busy: boolean;
  onFile: (f: File) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        if (!busy) setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f && !busy) onFile(f);
      }}
      className={`glass group relative flex cursor-pointer flex-col items-center overflow-hidden rounded-2xl border-dashed px-4 py-6 text-center transition-all duration-300 ${
        drag ? "border-indigo-300/70 bg-indigo-500/10" : "hover:border-indigo-300/40"
      } ${busy ? "pointer-events-none" : ""}`}
    >
      {busy && (
        <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-white/5">
          <div className="animate-scan absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-cyan-300 to-transparent" />
        </div>
      )}
      <span
        className={`flex h-11 w-11 items-center justify-center rounded-xl text-white transition-transform duration-500 group-hover:-translate-y-0.5 ${
          status ? "bg-emerald-500/25" : "metal-fill shadow-[0_0_24px_rgba(99,102,241,0.4)]"
        }`}
      >
        {busy ? (
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        ) : status ? (
          <span className="text-emerald-200">✓</span>
        ) : (
          <IconUpload className="h-5 w-5" />
        )}
      </span>
      <span className="mt-3 text-sm font-semibold text-white">
        {title}
        {required && <Req />}
      </span>
      <span className="mt-1 text-xs text-zinc-500">{busy ? "Reading…" : status || hint}</span>
      <input
        ref={ref}
        type="file"
        accept=".pdf,.txt,.md,application/pdf,text/plain"
        className="sr-only"
        disabled={busy}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          if (ref.current) ref.current.value = "";
        }}
      />
    </label>
  );
}

function IntervalBar({ p, lo, hi }: { p: number; lo: number; hi: number }) {
  return (
    <div className="relative mt-3 h-2 rounded-full bg-white/[0.06]">
      <div
        className="absolute inset-y-0 rounded-full bg-indigo-400/30"
        style={{ left: `${lo * 100}%`, width: `${Math.max(1, (hi - lo) * 100)}%` }}
      />
      <div
        className="absolute -top-1 h-4 w-1 rounded-full bg-white shadow-[0_0_10px_rgba(165,180,252,0.9)]"
        style={{ left: `calc(${p * 100}% - 2px)` }}
      />
    </div>
  );
}

function ResultCard({ e }: { e: AdmissionEstimate }) {
  const v = VERDICT[e.verdict];
  const maxDelta = Math.max(1, ...e.factors.map((f) => Math.abs(f.delta_pp)));
  const showWithPi =
    e.probability_with_pi !== null && Math.abs(e.probability_with_pi - e.probability) >= 0.005;
  return (
    <article className="glass rounded-2xl p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{e.institution}</h3>
          <p className="text-sm text-zinc-400">
            {[e.program, e.pi_name].filter(Boolean).join(" · ") || "Program-level estimate"}
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-4xl font-semibold text-white">{pct(e.probability)}</p>
          <p className="text-xs text-zinc-500">
            80% range {pct(e.interval_80[0])}–{pct(e.interval_80[1])}
          </p>
        </div>
      </div>
      <IntervalBar p={e.probability} lo={e.interval_80[0]} hi={e.interval_80[1]} />
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full border px-2.5 py-1 ${v.cls}`}>{v.label}</span>
        <span className="rounded-full border border-white/10 px-2.5 py-1 text-zinc-300">
          Confidence {e.confidence}
        </span>
        <span className="rounded-full border border-white/10 px-2.5 py-1 text-zinc-400">
          Base rate {pct(e.base_rate)}{" "}
          {e.base_rate_source === "verified_program_stat"
            ? "(cited)"
            : e.base_rate_source === "unverified_program_stat"
              ? "(uncited)"
              : "(prior)"}
        </span>
        <span className="rounded-full border border-white/10 px-2.5 py-1 text-zinc-400">
          Ahead of ~{pct(e.pool_percentile)} of applicants
        </span>
      </div>
      {showWithPi && e.probability_with_pi !== null && (
        <p className="mt-3 text-sm text-zinc-300">
          Offer <span className="text-zinc-500">and</span> joining {e.pi_name}&apos;s group:{" "}
          <span className="font-mono text-white">{pct(e.probability_with_pi)}</span>
          <span className="text-zinc-500"> (advisor is chosen after admission here)</span>
        </p>
      )}

      <div className="mt-5">
        <p className="eyebrow">What moves it</p>
        <ul className="mt-3 space-y-2">
          {e.factors.map((f) => (
            <li key={f.key} className="grid grid-cols-[11.5rem_1fr_3.5rem] items-center gap-3 text-sm">
              <span className="truncate text-zinc-300" title={f.note || undefined}>
                {f.label}
                <span className="block text-[11px] text-zinc-500">
                  {f.label_zh}
                  {f.state !== "known" && ` · ${f.state}`}
                </span>
              </span>
              <span className="relative h-1.5 rounded-full bg-white/[0.05]">
                <span
                  className={`absolute inset-y-0 rounded-full ${
                    f.delta_pp >= 0 ? "left-1/2 bg-emerald-400/70" : "right-1/2 bg-rose-400/70"
                  } ${f.state === "missing" ? "opacity-40" : ""}`}
                  style={{ width: `${(Math.abs(f.delta_pp) / maxDelta) * 50}%` }}
                />
              </span>
              <span className={`text-right font-mono text-xs ${f.delta_pp >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                {f.delta_pp >= 0 ? "+" : ""}
                {f.delta_pp.toFixed(1)}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11px] text-zinc-500">
          Percentage points vs. an average applicant on that factor. Missing factors are inferred
          from the rest of your file and shown faded.
        </p>
      </div>

      {e.levers.length > 0 && (
        <div className="mt-5">
          <p className="eyebrow">How to raise it</p>
          <ul className="mt-2 space-y-1.5 text-sm">
            {e.levers.map((l) => (
              <li key={l.key} className="flex justify-between gap-3 text-zinc-300">
                <span>
                  {l.label} <span className="text-zinc-500">· {l.label_zh}</span>
                </span>
                <span className="font-mono text-emerald-300">
                  +{l.delta_pp.toFixed(1)} → {pct(l.probability)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(e.missing_inputs.length > 0 || e.warnings.length > 0 || e.adjustments.length > 0) && (
        <details className="mt-5 text-sm text-zinc-400">
          <summary className="cursor-pointer text-xs font-medium text-indigo-200/90">
            Assumptions and what would sharpen this
          </summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs">
            {e.adjustments.map((a) => (
              <li key={a}>{a}</li>
            ))}
            {e.missing_inputs.map((m) => (
              <li key={m} className="text-amber-200/80">
                {m}
              </li>
            ))}
            {e.warnings.map((w) => (
              <li key={w} className="text-amber-200/80">
                {w}
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

export default function AdmissionPage() {
  const [draft, setDraft] = useState<AdmissionDraft>(emptyDraft);
  const [loaded, setLoaded] = useState(false);
  const [busyDoc, setBusyDoc] = useState<DocKind | null>(null);
  const [docError, setDocError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<StoredAdmissionResult | null>(null);
  const [hasKey, setHasKey] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setHasKey(!!loadSettings()?.apiKey?.trim());
      const stored = loadDraft();
      if (stored) {
        setDraft(stored.targets.length ? stored : { ...stored, targets: [newTarget()] });
      } else {
        // First visit: prefill from the matcher profile if there is one.
        const prof = loadProfile();
        const p = prof ? (normalizeProfile(prof) as Record<string, unknown>) : {};
        setDraft({
          ...emptyDraft,
          field: (p.field as string) || "",
          undergrad_institution: (p.undergrad_institution as string) || "",
          gpa_raw: p.gpa_raw ? String(p.gpa_raw) : "",
          gpa_scale: (p.gpa_scale as GpaScale) || "4.0",
          research_interests: (p.research_direction as string) || "",
          current_advisors: (p.current_advisors as Advisor[]) || [],
          publications: (p.papers as Paper[]) || [],
          experiences: (p.experiences as AdmissionDraft["experiences"]) || [],
          targets: [newTarget()],
        });
      }
      setResult(loadAdmissionResult());
      setLoaded(true);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (loaded) saveDraft(draft);
  }, [draft, loaded]);

  function set<K extends keyof AdmissionDraft>(key: K, value: AdmissionDraft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function updateAt<T>(list: T[], i: number, patch: Partial<T>): T[] {
    return list.map((item, idx) => (idx === i ? { ...item, ...patch } : item));
  }

  async function handleDoc(kind: DocKind, file: File) {
    const settings = loadSettings();
    if (!settings?.apiKey?.trim()) {
      setDocError("Reading documents uses your own LLM key. Add one in Settings first.");
      return;
    }
    setBusyDoc(kind);
    setDocError(null);
    try {
      const text = await fileToText(file);
      const stamp = { name: file.name, parsed_at: new Date().toISOString() };
      if (kind === "transcript") {
        const transcript = await parseTranscript(settings, text);
        setDraft((d) => ({ ...d, transcript, docs: { ...d.docs, transcript: stamp } }));
      } else if (kind === "sop") {
        const sop = await readSop(settings, text, draft.application_direction);
        setDraft((d) => ({ ...d, sop, docs: { ...d.docs, sop: stamp } }));
      } else {
        const { patch } = await parseCv(settings, text);
        setDraft((d) => ({
          ...d,
          ...Object.fromEntries(
            Object.entries(patch).filter(([k, v]) => {
              const cur = d[k as keyof AdmissionDraft];
              // Never overwrite something the user already typed.
              return Array.isArray(cur) ? cur.length === 0 : !cur && v !== undefined;
            })
          ),
          docs: { ...d.docs, cv: stamp },
        }));
      }
    } catch (e) {
      setDocError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyDoc(null);
    }
  }

  const missing = missingRequired(draft);

  async function run() {
    const settings = loadSettings();
    if (!settings?.apiKey?.trim()) {
      setRunError("Add your LLM key in Settings first — it powers the background research.");
      return;
    }
    if (missing.length) {
      setRunError(`Please complete: ${missing.join(", ")}.`);
      return;
    }
    setRunning(true);
    setRunError(null);
    setProgress([]);
    try {
      const stored = await runAdmission({
        settings,
        draft,
        onProgress: (line) => setProgress((p) => (p[p.length - 1] === line ? p : [...p, line].slice(-8))),
      });
      setResult(stored);
      setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  if (!loaded) {
    return <div className="mx-auto max-w-3xl px-6 py-16 text-zinc-500">Loading…</div>;
  }

  const t = draft.transcript;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <PageHeader
        eyebrow="Admission odds"
        title={
          <>
            What are my{" "}
            <span className="font-display italic font-normal text-[1.1em] ember-text">chances</span>?
          </>
        }
      >
        Name the schools and professors you care about. We research each one, read your documents,
        and estimate the probability of an offer — with an honest range, not a single magic number.
      </PageHeader>

      {!hasKey && (
        <p className="mt-6 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Document reading and background research use your own LLM key.{" "}
          <Link href="/settings" className="text-indigo-300 underline">
            Add one in Settings
          </Link>
          .
        </p>
      )}

      <section className="animate-fade-up delay-100 mt-8">
        <div className="grid gap-3 sm:grid-cols-3">
          <DocTile
            title="CV"
            hint="Prefills the form"
            status={draft.docs.cv && `Read ${draft.docs.cv.name}`}
            busy={busyDoc === "cv"}
            onFile={(f) => void handleDoc("cv", f)}
          />
          <DocTile
            title="Transcript"
            hint="Required · PDF or text"
            required
            status={t ? `${t.courses.length} courses read` : undefined}
            busy={busyDoc === "transcript"}
            onFile={(f) => void handleDoc("transcript", f)}
          />
          <DocTile
            title="SOP"
            hint="Optional · statement of purpose"
            status={draft.docs.sop && `Read ${draft.docs.sop.name}`}
            busy={busyDoc === "sop"}
            onFile={(f) => void handleDoc("sop", f)}
          />
        </div>
        {docError && (
          <p className="mt-3 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {docError}
          </p>
        )}
        <p className="mt-3 text-xs text-zinc-500">
          Files are read in your browser and sent only to your own LLM provider. Nothing is stored on a server.
        </p>
      </section>

      <div className="mt-6 space-y-6">
        <Section title="About you" subtitle="Fields marked * are required" icon={<IconUser />}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Field<Req /></label>
              <input className="field" value={draft.field} onChange={(e) => set("field", e.target.value)} placeholder="e.g. physics, cs, biology" />
            </div>
            <div>
              <label className={labelCls}>Undergraduate institution<Req /></label>
              <input className="field" value={draft.undergrad_institution} onChange={(e) => set("undergrad_institution", e.target.value)} placeholder="e.g. Tsinghua University" />
            </div>
            <div>
              <label className={labelCls}>GPA<Req /></label>
              <input className="field" value={draft.gpa_raw} onChange={(e) => set("gpa_raw", e.target.value)} placeholder={draft.gpa_scale === "uk" ? "first / 2_1 …" : "3.85"} />
            </div>
            <div>
              <label className={labelCls}>GPA scale</label>
              <select className="field" value={draft.gpa_scale} onChange={(e) => set("gpa_scale", e.target.value as GpaScale)}>
                {GPA_SCALES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Application direction<Req /></label>
              <input className="field" value={draft.application_direction} onChange={(e) => set("application_direction", e.target.value)} placeholder="e.g. experimental condensed matter physics" />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Research interests<Req /></label>
              <textarea className="field min-h-20" value={draft.research_interests} onChange={(e) => set("research_interests", e.target.value)} placeholder="The questions you want to work on, in a sentence or two" />
            </div>
          </div>
        </Section>

        <Section
          title="Transcript"
          subtitle="Upload it above. Core courses, graduate-level courses and your grade trend all count."
          icon={<IconDoc />}
        >
          {t ? (
            <div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelCls}>Class rank (top %, optional)</label>
                  <input
                    className="field"
                    value={t.class_rank_percentile ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      set("transcript", { ...t, class_rank_percentile: e.target.value && n > 0 && n <= 100 ? n : null });
                    }}
                    placeholder="e.g. 5"
                  />
                </div>
              </div>
              <div className="mt-4 max-h-72 overflow-auto rounded-xl border border-white/[0.08]">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-[#0b0b14] text-zinc-500">
                    <tr>
                      <th className="px-3 py-2 font-medium">Course</th>
                      <th className="px-3 py-2 font-medium">Grade</th>
                      <th className="px-3 py-2 font-medium">Year</th>
                      <th className="px-3 py-2 font-medium">Graduate</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {t.courses.map((c, i) => (
                      <tr key={`${c.name}-${i}`} className="border-t border-white/[0.05] text-zinc-300">
                        <td className="px-3 py-1.5">{c.name}</td>
                        <td className="px-3 py-1.5 font-mono">{String(c.grade)}</td>
                        <td className="px-3 py-1.5">{c.year ?? "–"}</td>
                        <td className="px-3 py-1.5">
                          <input
                            type="checkbox"
                            checked={c.level === "graduate"}
                            onChange={(e) =>
                              set("transcript", {
                                ...t,
                                courses: updateAt(t.courses, i, { level: e.target.checked ? "graduate" : "undergrad" }),
                              })
                            }
                          />
                        </td>
                        <td className="px-3 py-1.5 text-right">
                          <button
                            type="button"
                            className="text-zinc-500 hover:text-rose-300"
                            onClick={() => set("transcript", { ...t, courses: t.courses.filter((_, j) => j !== i) })}
                            aria-label={`Remove ${c.name}`}
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-zinc-500">Check what was read. Remove anything that isn&apos;t on your transcript.</p>
            </div>
          ) : (
            <p className="text-sm text-zinc-400">No transcript yet. Upload a PDF or text copy in the Transcript tile above.</p>
          )}
        </Section>

        <Section title="Publications" subtitle="Required — list them, or confirm you have none" icon={<IconBook />}>
          <div className="space-y-3">
            {draft.publications.map((p, i) => (
              <div key={i} className={itemCls}>
                <div className="grid gap-3 sm:grid-cols-6">
                  <input className="field sm:col-span-6" value={p.title} onChange={(e) => set("publications", updateAt(draft.publications, i, { title: e.target.value }))} placeholder="Title" />
                  <input className="field sm:col-span-3" value={p.journal} onChange={(e) => set("publications", updateAt(draft.publications, i, { journal: e.target.value }))} placeholder="Journal / venue" />
                  <select className="field" value={p.journal_tier} onChange={(e) => set("publications", updateAt(draft.publications, i, { journal_tier: Number(e.target.value) }))} title="Venue tier: 1 = top">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>Tier {n}</option>
                    ))}
                  </select>
                  <input className="field" type="number" min={1} value={p.author_position} onChange={(e) => set("publications", updateAt(draft.publications, i, { author_position: Math.max(1, Number(e.target.value) || 1) }))} title="Your author position" />
                  <select className="field" value={p.status} onChange={(e) => set("publications", updateAt(draft.publications, i, { status: e.target.value as PaperStatus }))}>
                    {PAPER_STATUSES.map((s) => (
                      <option key={s} value={s}>{s.replace("_", " ")}</option>
                    ))}
                  </select>
                </div>
                <div className="mt-3 flex justify-end">
                  <button type="button" className={removeBtnCls} onClick={() => set("publications", draft.publications.filter((_, j) => j !== i))}>
                    <IconTrash /> Remove
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              className={addBtnCls}
              onClick={() => {
                set("no_publications", false);
                set("publications", [
                  ...draft.publications,
                  { title: "", journal: "", journal_tier: 3, author_position: 1, status: "published", year: new Date().getFullYear() },
                ]);
              }}
            >
              <IconPlus /> Add publication
            </button>
            {draft.publications.length === 0 && (
              <label className="flex items-center gap-2 text-sm text-zinc-300">
                <input type="checkbox" checked={draft.no_publications} onChange={(e) => set("no_publications", e.target.checked)} />
                I have no publications yet
              </label>
            )}
          </div>
        </Section>

        <Section title="Target schools and professors" subtitle="Each one gets its own background research" icon={<IconChart />}>
          <div className="space-y-3">
            {draft.targets.map((tg, i) => {
              const up = (patch: Partial<TargetDraft>) => set("targets", updateAt(draft.targets, i, patch));
              return (
                <div key={tg.key} className={itemCls}>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className={labelCls}>School<Req /></label>
                      <input className="field" value={tg.institution} onChange={(e) => up({ institution: e.target.value })} placeholder="e.g. MIT" />
                    </div>
                    <div>
                      <label className={labelCls}>Professor (optional)</label>
                      <input className="field" value={tg.professor} onChange={(e) => up({ professor: e.target.value })} placeholder="e.g. Prof. Jane Doe" />
                    </div>
                    <div>
                      <label className={labelCls}>Program (optional)</label>
                      <input className="field" value={tg.program} onChange={(e) => up({ program: e.target.value })} placeholder="e.g. Physics PhD" />
                    </div>
                    <div>
                      <label className={labelCls}>Ranking tier</label>
                      <select className="field" value={tg.tier} onChange={(e) => up({ tier: e.target.value as TargetDraft["tier"] })}>
                        {TIERS.map((x) => (
                          <option key={x.value} value={x.value}>{x.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelCls}>Contact with professor</label>
                      <select className="field" value={tg.contact_status} disabled={!tg.professor.trim()} onChange={(e) => up({ contact_status: e.target.value as ContactStatus })}>
                        {CONTACT.map((x) => (
                          <option key={x.value} value={x.value}>{x.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelCls}>Stage</label>
                      <select className="field" value={tg.stage} onChange={(e) => up({ stage: e.target.value as Stage })}>
                        {STAGES.map((x) => (
                          <option key={x.value} value={x.value}>{x.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {draft.targets.length > 1 && (
                    <div className="mt-3 flex justify-end">
                      <button type="button" className={removeBtnCls} onClick={() => set("targets", draft.targets.filter((_, j) => j !== i))}>
                        <IconTrash /> Remove
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
            {draft.targets.length < 8 && (
              <button type="button" className={addBtnCls} onClick={() => set("targets", [...draft.targets, newTarget()])}>
                <IconPlus /> Add a school
              </button>
            )}
          </div>
        </Section>

        <details className="glass rounded-2xl p-6 sm:p-7">
          <summary className="cursor-pointer text-lg font-semibold text-white">
            Optional details <span className="text-sm font-normal text-zinc-500">· GRE, letters, advisors — each one narrows the range</span>
          </summary>
          <div className="mt-6 space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className={labelCls}>GRE Verbal</label>
                <input className="field" value={draft.gre_verbal} onChange={(e) => set("gre_verbal", e.target.value)} placeholder="130–170" />
              </div>
              <div>
                <label className={labelCls}>GRE Quant</label>
                <input className="field" value={draft.gre_quant} onChange={(e) => set("gre_quant", e.target.value)} placeholder="130–170" />
              </div>
              <div>
                <label className={labelCls}>GRE Writing</label>
                <input className="field" value={draft.gre_writing} onChange={(e) => set("gre_writing", e.target.value)} placeholder="0–6" />
              </div>
              <div>
                <label className={labelCls}>Subject GRE</label>
                <input className="field" value={draft.gre_subject_name} onChange={(e) => set("gre_subject_name", e.target.value)} placeholder="e.g. physics" />
              </div>
              <div>
                <label className={labelCls}>Score</label>
                <input className="field" value={draft.gre_subject_score} onChange={(e) => set("gre_subject_score", e.target.value)} placeholder="200–990" />
              </div>
              <div>
                <label className={labelCls}>Percentile</label>
                <input className="field" value={draft.gre_subject_pct} onChange={(e) => set("gre_subject_pct", e.target.value)} placeholder="0–100" />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>International applicant?</label>
                <select className="field" value={draft.is_international} onChange={(e) => set("is_international", e.target.value as AdmissionDraft["is_international"])}>
                  <option value="">Prefer not to say</option>
                  <option value="yes">Yes</option>
                  <option value="no">No (domestic)</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Undergraduate institution tier</label>
                <select className="field" value={draft.undergrad_tier} onChange={(e) => set("undergrad_tier", e.target.value as UndergradTier)}>
                  {UG_TIERS.map((x) => (
                    <option key={x.value} value={x.value}>{x.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelCls}>External fellowship</label>
                <select className="field" value={draft.external_fellowship} onChange={(e) => set("external_fellowship", e.target.value as Fellowship)}>
                  <option value="none">None</option>
                  <option value="applying">Applying</option>
                  <option value="secured">Secured</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Fellowship name</label>
                <input className="field" value={draft.fellowship_name} onChange={(e) => set("fellowship_name", e.target.value)} placeholder="e.g. NSF GRFP, CSC" />
              </div>
            </div>

            <div>
              <p className={labelCls}>Recommendation letters</p>
              <div className="space-y-2">
                {draft.letters.map((l, i) => (
                  <div key={i} className="grid items-center gap-2 sm:grid-cols-[1fr_12rem_auto_auto]">
                    <input className="field" value={l.name} onChange={(e) => set("letters", updateAt(draft.letters, i, { name: e.target.value }))} placeholder="Letter writer" />
                    <select className="field" value={l.prominence} onChange={(e) => set("letters", updateAt(draft.letters, i, { prominence: e.target.value as Prominence }))}>
                      {PROMINENCE.map((x) => (
                        <option key={x.value} value={x.value}>{x.label}</option>
                      ))}
                    </select>
                    <label className="flex items-center gap-1.5 text-xs text-zinc-400">
                      <input type="checkbox" checked={l.is_research_supervisor} onChange={(e) => set("letters", updateAt(draft.letters, i, { is_research_supervisor: e.target.checked }))} />
                      Supervised my research
                    </label>
                    <button type="button" className={removeBtnCls} onClick={() => set("letters", draft.letters.filter((_, j) => j !== i))}>
                      <IconTrash />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className={addBtnCls}
                  onClick={() =>
                    set("letters", [...draft.letters, { name: "", prominence: "established", is_research_supervisor: true } as LetterWriter])
                  }
                >
                  <IconPlus /> Add letter writer
                </button>
              </div>
            </div>

            <div>
              <p className={labelCls}>Current research advisors (used to find connections to each professor)</p>
              <div className="space-y-2">
                {draft.current_advisors.map((a, i) => (
                  <div key={a.id || i} className="grid items-center gap-2 sm:grid-cols-[1fr_1fr_auto]">
                    <input className="field" value={a.name} onChange={(e) => set("current_advisors", updateAt(draft.current_advisors, i, { name: e.target.value }))} placeholder="Advisor name" />
                    <input className="field" value={a.institution} onChange={(e) => set("current_advisors", updateAt(draft.current_advisors, i, { institution: e.target.value }))} placeholder="Institution" />
                    <button type="button" className={removeBtnCls} onClick={() => set("current_advisors", draft.current_advisors.filter((_, j) => j !== i))}>
                      <IconTrash />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className={addBtnCls}
                  onClick={() =>
                    set("current_advisors", [
                      ...draft.current_advisors,
                      { id: `adv_${Math.random().toString(36).slice(2, 7)}`, name: "", institution: "" },
                    ])
                  }
                >
                  <IconPlus /> Add advisor
                </button>
              </div>
            </div>
          </div>
        </details>

        <div className="glass rounded-2xl p-6 sm:p-7">
          {missing.length > 0 && (
            <p className="mb-4 text-sm text-zinc-400">
              Still needed: <span className="text-amber-200/90">{missing.join(" · ")}</span>
            </p>
          )}
          <button type="button" className="btn-primary w-full rounded-xl px-5 py-3 text-sm" disabled={running || missing.length > 0} onClick={() => void run()}>
            {running ? "Researching and estimating…" : "Estimate my chances"}
          </button>
          {running && (
            <ul className="mt-4 space-y-1 font-mono text-xs text-zinc-400">
              {progress.map((p, i) => (
                <li key={`${i}-${p}`} className={i === progress.length - 1 ? "text-indigo-200" : ""}>
                  {p}
                </li>
              ))}
            </ul>
          )}
          {running && <p className="mt-3 text-xs text-zinc-500">Keep this page open. Each school takes about a minute of web research.</p>}
          {runError && (
            <p className="mt-4 whitespace-pre-line rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {runError}
            </p>
          )}
        </div>
      </div>

      {result && (
        <section id="results" className="mt-10 space-y-5">
          <div className="glass-strong rounded-2xl p-6">
            <p className="eyebrow">Across your list</p>
            <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="font-mono text-4xl font-semibold text-white">{pct(result.result.p_at_least_one)}</p>
                <p className="text-sm text-zinc-400">chance of at least one offer</p>
              </div>
              <div className="text-right text-sm text-zinc-400">
                <p>Expected offers: <span className="font-mono text-white">{result.result.expected_offers.toFixed(1)}</span></p>
                <p className="text-xs text-zinc-500">
                  {pct(result.result.p_at_least_one_if_independent)} if the schools were independent — they aren&apos;t, the same file goes everywhere.
                </p>
              </div>
            </div>
            {!result.web_search && (
              <p className="mt-4 text-xs text-amber-200/80">
                This provider has no web search, so programs and professors were not researched. Estimates use priors and have wide ranges.
              </p>
            )}
          </div>
          {result.result.estimates.map((e) => (
            <ResultCard key={e.target_id} e={e} />
          ))}
          <p className="text-xs leading-relaxed text-zinc-500">
            This is a model estimate with an 80% range, anchored on program admit rates — not a guarantee. Missing or
            unverified information widens the range instead of being guessed. 这是基于录取率基准的模型估计（附 80% 区间），不是保证。
          </p>
        </section>
      )}
    </div>
  );
}
