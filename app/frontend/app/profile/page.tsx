"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type {
  Advisor,
  Experience,
  GpaScale,
  LabTier,
  OutputType,
  Paper,
  PaperStatus,
  StudentProfile,
} from "@/lib/types";
import { loadProfile, loadSettings, saveProfile } from "@/lib/store";
import { validateProfile } from "@/lib/engine";
import { completion } from "@/lib/llm";
import { CV_PARSE_SYSTEM, extractCvProfile, normalizeProfile } from "@/lib/research";
import PageHeader from "@/components/PageHeader";
import {
  IconBook,
  IconCheck,
  IconFlask,
  IconNetwork,
  IconPlus,
  IconTrash,
  IconUpload,
  IconUser,
} from "@/components/Icons";

/** Extract text from the first pages of a PDF, entirely in-browser. */
async function pdfToText(file: File, maxPages = 10): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url
  ).toString();
  const doc = await pdfjs.getDocument({ data: await file.arrayBuffer() })
    .promise;
  const pages = Math.min(doc.numPages, maxPages);
  let text = "";
  for (let i = 1; i <= pages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    text +=
      content.items
        .map((it) => ("str" in it ? (it as { str: string }).str : ""))
        .join(" ") + "\n";
  }
  return text;
}

const inputCls = "field";
const labelCls = "field-label";
const removeBtnCls =
  "inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs text-zinc-400 transition-colors hover:border-rose-400/40 hover:bg-rose-500/10 hover:text-rose-200";
const addBtnCls =
  "group flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-indigo-300/30 px-4 py-3 text-sm text-indigo-200 transition-all hover:border-indigo-300/60 hover:bg-indigo-500/[0.08]";
const itemCls =
  "animate-fade-up rounded-xl border border-white/[0.08] bg-black/20 p-4 transition-colors hover:border-white/[0.14]";

const GPA_SCALES: { value: GpaScale; label: string }[] = [
  { value: "4.0", label: "4.0 scale" },
  { value: "4.3", label: "4.3 scale" },
  { value: "4.5", label: "4.5 scale" },
  { value: "100", label: "100-point scale" },
  { value: "uk", label: "UK honours" },
];
const PAPER_STATUSES: PaperStatus[] = [
  "published",
  "accepted",
  "in_press",
  "submitted",
  "preprint",
  "in_prep",
];
const LAB_TIERS: { value: LabTier; label: string }[] = [
  { value: "world_class", label: "World-class" },
  { value: "top_us", label: "Top US" },
  { value: "strong_us_or_top_cn", label: "Strong US / Top China" },
  { value: "good_us_or_985", label: "Good US / 985" },
  { value: "211_or_overseas", label: "211 / Overseas" },
  { value: "other", label: "Other" },
];
const OUTPUT_TYPES: { value: OutputType; label: string }[] = [
  { value: "paper", label: "Paper" },
  { value: "conference_oral", label: "Conference talk" },
  { value: "conference_poster", label: "Conference poster" },
  { value: "honors_thesis", label: "Honors thesis" },
  { value: "participation_only", label: "Participation only" },
];

const emptyProfile: StudentProfile = {
  name: "",
  field: "",
  undergrad_institution: "",
  gpa_raw: 0,
  gpa_scale: "4.0",
  research_direction: "",
  current_advisors: [],
  papers: [],
  experiences: [],
};

function Section({
  title,
  subtitle,
  icon,
  count,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section className="glass spotlight rounded-2xl p-6 sm:p-7">
      <div className="flex items-start gap-3.5">
        <span className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-indigo-200">
          {icon}
        </span>
        <div className="flex-1">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
            {title}
            {count !== undefined && count > 0 && (
              <span className="rounded-full bg-white/[0.07] px-2 py-0.5 font-mono text-xs font-normal text-zinc-400">
                {count}
              </span>
            )}
          </h2>
          {subtitle && <p className="mt-0.5 text-sm text-zinc-500">{subtitle}</p>}
        </div>
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}

/** How filled-in the profile is — tighter inputs mean tighter bands. */
function completeness(p: StudentProfile): number {
  const checks = [
    !!p.field,
    !!p.undergrad_institution,
    !!p.gpa_raw,
    !!p.research_direction && p.research_direction.length > 12,
    p.current_advisors.length > 0,
    p.papers.length > 0,
    p.experiences.length > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function CompletionRing({ value }: { value: number }) {
  const r = 22;
  const c = 2 * Math.PI * r;
  return (
    <div className="glass flex items-center gap-3 rounded-2xl py-2.5 pl-2.5 pr-4">
      <div className="relative h-14 w-14">
        <svg viewBox="0 0 56 56" className="h-full w-full -rotate-90">
          <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="5" />
          <circle
            cx="28"
            cy="28"
            r={r}
            fill="none"
            stroke={value === 100 ? "#6ee7b7" : "#a5b4fc"}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - value / 100)}
            style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.22,1,0.36,1), stroke 0.4s" }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-mono text-xs text-white">
          {value}%
        </span>
      </div>
      <div className="text-xs leading-relaxed">
        <p className="font-medium text-zinc-200">{value === 100 ? "Looking complete" : "Profile strength"}</p>
        <p className="text-zinc-500">{value === 100 ? "Tightest bands possible" : "More detail, tighter bands"}</p>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<StudentProfile>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    kind: "ok" | "err";
    text: string;
  } | null>(null);

  // CV import state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [parsing, setParsing] = useState(false);
  const [cvError, setCvError] = useState<{
    needsSettings: boolean;
    text: string;
  } | null>(null);
  const [cvImported, setCvImported] = useState(false);
  const [cvWarnings, setCvWarnings] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      const stored = loadProfile();
      if (stored) {
        // Coerce any legacy/invalid values saved by an earlier version so a
        // previously-broken profile loads cleanly and can be re-saved.
        const p = normalizeProfile(stored) as Partial<StudentProfile>;
        setProfile({
          ...emptyProfile,
          ...p,
          current_advisors: p.current_advisors ?? [],
          papers: p.papers ?? [],
          experiences: p.experiences ?? [],
        });
      }
      setLoading(false);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  function set<K extends keyof StudentProfile>(
    key: K,
    value: StudentProfile[K]
  ) {
    setProfile((p) => ({ ...p, [key]: value }));
  }

  function updateAt<T>(list: T[], i: number, patch: Partial<T>): T[] {
    return list.map((item, idx) => (idx === i ? { ...item, ...patch } : item));
  }

  async function importCv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await importCvFile(file);
  }

  async function importCvFile(file: File) {
    setParsing(true);
    setCvError(null);
    setCvImported(false);
    setCvWarnings([]);
    try {
      const settings = loadSettings();
      if (!settings?.apiKey?.trim()) {
        setCvError({
          needsSettings: true,
          text: "CV parsing uses your own LLM key, and none is configured yet.",
        });
        return;
      }
      const text = await pdfToText(file);
      if (!text.trim()) {
        throw new Error(
          "Could not extract any text from this PDF (is it a scanned image?). Fill the form manually instead."
        );
      }
      const reply = await completion(
        settings,
        CV_PARSE_SYSTEM,
        "CV text:\n\n" + text.slice(0, 40000)
      );
      const { profile: parsedRaw, warnings } = extractCvProfile(reply);
      const parsed = parsedRaw as Partial<StudentProfile>;
      setProfile({
        ...emptyProfile,
        ...parsed,
        name: parsed.name ?? "",
        current_advisors: parsed.current_advisors ?? [],
        papers: parsed.papers ?? [],
        experiences: parsed.experiences ?? [],
      });
      setCvImported(true);
      setCvWarnings(warnings ?? []);
      setMessage(null);
    } catch (err) {
      setCvError({
        needsSettings: false,
        text: err instanceof Error ? err.message : "Failed to parse CV",
      });
    } finally {
      setParsing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      // Lightweight, instant required-field check — no engine needed.
      const missing: string[] = [];
      const p = profile as unknown as Record<string, unknown>;
      if (!p.field) missing.push("field");
      if (!p.undergrad_institution) missing.push("undergrad institution");
      if (p.gpa_raw === "" || p.gpa_raw === undefined || p.gpa_raw === null)
        missing.push("GPA");
      if (!p.research_direction) missing.push("research direction");
      if (missing.length) {
        setMessage({
          kind: "err",
          text: `Please fill in: ${missing.join(", ")}.`,
        });
        return;
      }
      // Strict engine validation is a best-effort bonus: the first run loads
      // ~13 MB of Pyodide, which can be slow or blocked. Never let that gate
      // saving — race it against a short timeout and save regardless (the
      // engine re-validates at run time anyway).
      try {
        const check = await Promise.race([
          validateProfile(profile),
          new Promise<{ ok: boolean; error?: string }>((res) =>
            setTimeout(() => res({ ok: true }), 4000)
          ),
        ]);
        if (!check.ok) {
          setMessage({
            kind: "err",
            text: check.error || "The engine rejected this profile.",
          });
          return;
        }
      } catch {
        /* engine unavailable — required-field check already passed; save on */
      }
      saveProfile(profile as unknown as Record<string, unknown>);
      setMessage({ kind: "ok", text: "Profile saved (in this browser)." });
    } catch (err) {
      setMessage({
        kind: "err",
        text: err instanceof Error ? err.message : "Failed to save profile",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-zinc-500">
        Loading profile…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <PageHeader
        eyebrow="Step 2 · Profile"
        title={
          <>
            Tell us your{" "}
            <span className="font-display italic font-normal text-[1.1em] ember-text">story</span>
          </>
        }
        aside={<CompletionRing value={completeness(profile)} />}
      >
        Everything here feeds the scoring engine. The more precise you are, the
        tighter your confidence bands.
      </PageHeader>

      <section className="animate-fade-up delay-100 mt-8">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            if (!parsing) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (f && !parsing) void importCvFile(f);
          }}
          className={`glass group relative flex cursor-pointer flex-col items-center overflow-hidden rounded-2xl border-dashed px-6 py-9 text-center transition-all duration-300 sm:flex-row sm:gap-6 sm:text-left ${
            dragging
              ? "border-indigo-300/70 bg-indigo-500/10 shadow-[0_0_0_4px_rgba(99,102,241,0.15)]"
              : "hover:border-indigo-300/40"
          } ${parsing ? "pointer-events-none" : ""}`}
        >
          {parsing && (
            <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-white/5">
              <div className="animate-scan absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-cyan-300 to-transparent" />
            </div>
          )}
          <span
            className={`metal-fill flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-white shadow-[0_0_30px_rgba(99,102,241,0.45)] transition-transform duration-500 ${
              dragging ? "scale-110 -rotate-6" : "group-hover:-translate-y-1"
            }`}
          >
            {parsing ? (
              <span className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <IconUpload />
            )}
          </span>
          <span className="mt-4 flex-1 sm:mt-0">
            <span className="block text-base font-semibold text-white">
              {parsing ? "Reading your CV…" : dragging ? "Drop it here" : "Import from your CV"}
            </span>
            <span className="mt-1 block text-sm text-zinc-400">
              {parsing
                ? "Usually about 30 seconds. Keep this page open."
                : "Drop a PDF or click to browse. Your configured LLM prefills the form; you review before saving."}
            </span>
          </span>
          <span className="btn-ghost mt-5 shrink-0 rounded-xl px-4 py-2 text-sm sm:mt-0">
            {parsing ? "Parsing…" : "Choose PDF"}
          </span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="sr-only"
            disabled={parsing}
            onChange={importCv}
          />
        </label>


        {cvError && (
          <p className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {cvError.text}{" "}
            {cvError.needsSettings ? (
              <>
                Add your API key in{" "}
                <Link
                  href="/settings"
                  className="text-indigo-300 underline hover:text-indigo-200"
                >
                  Settings
                </Link>{" "}
                first, then retry.
              </>
            ) : (
              <>
                You can also check your key in{" "}
                <Link
                  href="/settings"
                  className="text-indigo-300 underline hover:text-indigo-200"
                >
                  Settings
                </Link>{" "}
                or fill the form manually below.
              </>
            )}
          </p>
        )}

        {cvImported && (
          <div className="mt-4 rounded-xl border border-emerald-400/30 bg-emerald-500/[0.07] px-4 py-3.5 text-sm text-emerald-100">
            <p className="flex items-center gap-2 font-medium text-emerald-300">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-xs">
                ✓
              </span>
              CV imported — the form below is filled in for you
            </p>
            <p className="mt-1.5 text-emerald-100/70">
              Nothing is saved yet. Review each field and click{" "}
              <span className="font-medium text-emerald-200">Save profile</span>{" "}
              when it looks right.
            </p>
            {cvWarnings.length > 0 && (
              <details className="mt-3 text-emerald-100/70">
                <summary className="cursor-pointer text-xs font-medium text-emerald-300/90 hover:text-emerald-200">
                  {cvWarnings.length} field
                  {cvWarnings.length > 1 ? "s" : ""} we couldn&apos;t read
                  directly — worth a look
                </summary>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs">
                  {cvWarnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </section>

      <form onSubmit={save} className="animate-fade-up delay-200 mt-6 space-y-6">
        <Section title="Basics" icon={<IconUser />}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Name (optional)</label>
              <input
                className={inputCls}
                value={profile.name ?? ""}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Jane Doe"
              />
            </div>
            <div>
              <label className={labelCls}>Field</label>
              <input
                className={inputCls}
                required
                value={profile.field}
                onChange={(e) => set("field", e.target.value)}
                placeholder="e.g. physics, materials science"
              />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Undergraduate institution</label>
              <input
                className={inputCls}
                required
                value={profile.undergrad_institution}
                onChange={(e) => set("undergrad_institution", e.target.value)}
                placeholder="e.g. MIT"
              />
            </div>
            <div>
              <label className={labelCls}>GPA</label>
              <input
                className={inputCls}
                type="number"
                step="0.01"
                min="0"
                required
                value={profile.gpa_raw || ""}
                onChange={(e) => set("gpa_raw", parseFloat(e.target.value) || 0)}
                placeholder="3.85"
              />
            </div>
            <div>
              <label className={labelCls}>GPA scale</label>
              <select
                className={inputCls}
                value={profile.gpa_scale}
                onChange={(e) => set("gpa_scale", e.target.value as GpaScale)}
              >
                {GPA_SCALES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Research direction</label>
              <textarea
                className={`${inputCls} min-h-20`}
                required
                value={profile.research_direction}
                onChange={(e) => set("research_direction", e.target.value)}
                placeholder="e.g. topological quantum materials, 2D heterostructures…"
              />
            </div>
          </div>
        </Section>

        <Section
          title="Current advisors"
          subtitle="PIs you currently work with. Their network is the heart of connection-first scoring."
          icon={<IconNetwork />}
          count={profile.current_advisors.length}
        >
          <div className="space-y-3">
            {profile.current_advisors.map((a, i) => (
              <div
                key={i}
                className={`${itemCls} flex flex-col gap-3 sm:flex-row sm:items-end`}
              >
                <div className="flex-1">
                  <label className={labelCls}>Name</label>
                  <input
                    className={inputCls}
                    required
                    value={a.name}
                    onChange={(e) =>
                      set(
                        "current_advisors",
                        updateAt(profile.current_advisors, i, {
                          name: e.target.value,
                        })
                      )
                    }
                    placeholder="Prof. Ada Lovelace"
                  />
                </div>
                <div className="flex-1">
                  <label className={labelCls}>Institution</label>
                  <input
                    className={inputCls}
                    required
                    value={a.institution}
                    onChange={(e) =>
                      set(
                        "current_advisors",
                        updateAt(profile.current_advisors, i, {
                          institution: e.target.value,
                        })
                      )
                    }
                    placeholder="MIT"
                  />
                </div>
                <button
                  type="button"
                  className={removeBtnCls}
                  onClick={() =>
                    set(
                      "current_advisors",
                      profile.current_advisors.filter((_, idx) => idx !== i)
                    )
                  }
                  aria-label="Remove advisor"
                >
                  <IconTrash className="h-3.5 w-3.5" />
                  <span className="sm:hidden">Remove</span>
                </button>
              </div>
            ))}
            <button
              type="button"
              className={addBtnCls}
              onClick={() =>
                set("current_advisors", [
                  ...profile.current_advisors,
                  {
                    id: crypto.randomUUID(),
                    name: "",
                    institution: "",
                  } satisfies Advisor,
                ])
              }
            >
              <IconPlus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
              Add advisor
            </button>
          </div>
        </Section>

        <Section
          title="Papers"
          subtitle="Publications, preprints, and manuscripts in preparation."
          icon={<IconBook />}
          count={profile.papers.length}
        >
          <div className="space-y-3">
            {profile.papers.map((p, i) => (
              <div
                key={i}
                className={itemCls}
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label className={labelCls}>Title</label>
                    <input
                      className={inputCls}
                      required
                      value={p.title}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, { title: e.target.value })
                        )
                      }
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Journal / venue</label>
                    <input
                      className={inputCls}
                      value={p.journal}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, {
                            journal: e.target.value,
                          })
                        )
                      }
                      placeholder="Nature Physics"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Journal tier</label>
                    <select
                      className={inputCls}
                      value={p.journal_tier}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, {
                            journal_tier: Number(e.target.value),
                          })
                        )
                      }
                    >
                      {[1, 2, 3, 4, 5].map((t) => (
                        <option key={t} value={t}>
                          Tier {t}
                          {t === 1 ? " (top)" : t === 5 ? " (lowest)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Author position</label>
                    <input
                      className={inputCls}
                      type="number"
                      min="1"
                      required
                      value={p.author_position || ""}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, {
                            author_position: Number(e.target.value) || 1,
                          })
                        )
                      }
                      placeholder="1"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Status</label>
                    <select
                      className={inputCls}
                      value={p.status}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, {
                            status: e.target.value as PaperStatus,
                          })
                        )
                      }
                    >
                      {PAPER_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Year (optional)</label>
                    <input
                      className={inputCls}
                      type="number"
                      min="1990"
                      max="2100"
                      value={p.year || ""}
                      onChange={(e) =>
                        set(
                          "papers",
                          updateAt(profile.papers, i, {
                            year: Number(e.target.value) || new Date().getFullYear(),
                          })
                        )
                      }
                    />
                  </div>
                </div>
                <div className="mt-3 text-right">
                  <button
                    type="button"
                    className={removeBtnCls}
                    onClick={() =>
                      set(
                        "papers",
                        profile.papers.filter((_, idx) => idx !== i)
                      )
                    }
                  >
                    <IconTrash className="h-3.5 w-3.5" />
                    Remove paper
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              className={addBtnCls}
              onClick={() =>
                set("papers", [
                  ...profile.papers,
                  {
                    title: "",
                    journal: "",
                    journal_tier: 3,
                    author_position: 1,
                    status: "in_prep",
                    year: new Date().getFullYear(),
                  } satisfies Paper,
                ])
              }
            >
              <IconPlus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
              Add paper
            </button>
          </div>
        </Section>

        <Section
          title="Research experiences"
          subtitle="Lab stints, REUs, internships, and what each produced."
          icon={<IconFlask />}
          count={profile.experiences.length}
        >
          <div className="space-y-3">
            {profile.experiences.map((x, i) => (
              <div
                key={i}
                className={itemCls}
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className={labelCls}>Lab PI name</label>
                    <input
                      className={inputCls}
                      required
                      value={x.lab_pi_name}
                      onChange={(e) =>
                        set(
                          "experiences",
                          updateAt(profile.experiences, i, {
                            lab_pi_name: e.target.value,
                          })
                        )
                      }
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Lab tier</label>
                    <select
                      className={inputCls}
                      value={x.lab_tier}
                      onChange={(e) =>
                        set(
                          "experiences",
                          updateAt(profile.experiences, i, {
                            lab_tier: e.target.value as LabTier,
                          })
                        )
                      }
                    >
                      {LAB_TIERS.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Duration (months)</label>
                    <input
                      className={inputCls}
                      type="number"
                      min="0"
                      required
                      value={x.duration_months || ""}
                      onChange={(e) =>
                        set(
                          "experiences",
                          updateAt(profile.experiences, i, {
                            duration_months: Number(e.target.value) || 0,
                          })
                        )
                      }
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Output</label>
                    <select
                      className={inputCls}
                      value={x.output_type}
                      onChange={(e) =>
                        set(
                          "experiences",
                          updateAt(profile.experiences, i, {
                            output_type: e.target.value as OutputType,
                          })
                        )
                      }
                    >
                      {OUTPUT_TYPES.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="mt-3 text-right">
                  <button
                    type="button"
                    className={removeBtnCls}
                    onClick={() =>
                      set(
                        "experiences",
                        profile.experiences.filter((_, idx) => idx !== i)
                      )
                    }
                  >
                    <IconTrash className="h-3.5 w-3.5" />
                    Remove experience
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              className={addBtnCls}
              onClick={() =>
                set("experiences", [
                  ...profile.experiences,
                  {
                    lab_pi_name: "",
                    lab_tier: "good_us_or_985",
                    duration_months: 6,
                    output_type: "participation_only",
                  } satisfies Experience,
                ])
              }
            >
              <IconPlus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
              Add experience
            </button>
          </div>
        </Section>

        <div className="glass sticky bottom-4 z-20 flex flex-wrap items-center gap-4 rounded-2xl px-4 py-3">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary rounded-xl px-6 py-2.5 font-medium disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
          {message ? (
            <span
              className={`animate-fade-up flex items-center gap-1.5 text-sm ${
                message.kind === "ok" ? "text-emerald-300" : "text-rose-300"
              }`}
            >
              {message.kind === "ok" && <IconCheck />}
              {message.text}
            </span>
          ) : (
            <span className="text-xs text-zinc-500">Saved only in this browser.</span>
          )}
          {message?.kind === "ok" && (
            <Link href="/dashboard" className="animate-fade-up ml-auto text-sm text-indigo-300 hover:text-white">
              Next: run a match →
            </Link>
          )}
        </div>
      </form>
    </div>
  );
}
