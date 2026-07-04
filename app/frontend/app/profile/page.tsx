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

const inputCls =
  "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none backdrop-blur transition-colors placeholder:text-zinc-600 focus:border-indigo-400/60";
const labelCls = "mb-1.5 block text-sm text-zinc-300";
const removeBtnCls =
  "rounded-md border border-white/10 px-2.5 py-1.5 text-xs text-zinc-400 transition-colors hover:border-red-400/40 hover:text-red-300";
const addBtnCls =
  "rounded-lg border border-dashed border-indigo-400/40 px-4 py-2 text-sm text-indigo-300 transition-colors hover:bg-indigo-500/10";

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
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="glass rounded-2xl p-6">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </section>
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
      <h1 className="text-3xl font-semibold text-white">Your profile</h1>
      <p className="mt-2 text-sm text-zinc-300/90">
        Everything here feeds the scoring engine. The more precise, the tighter
        your confidence bands.
      </p>

      <section className="glass mt-8 rounded-2xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Import from CV (PDF)
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              We parse your CV with your configured LLM and prefill the form
              below. Takes about 30 seconds.
            </p>
          </div>
          <label
            className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border border-indigo-400/40 px-4 py-2 text-sm text-indigo-300 transition-colors hover:bg-indigo-500/10 ${
              parsing ? "pointer-events-none opacity-60" : ""
            }`}
          >
            {parsing && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-400/30 border-t-indigo-400" />
            )}
            {parsing ? "Parsing CV…" : "Upload PDF"}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              disabled={parsing}
              onChange={importCv}
            />
          </label>
        </div>

        {parsing && (
          <p className="mt-4 text-sm text-zinc-400">
            Reading your CV with the research model — this usually takes around
            30 seconds. Keep this page open.
          </p>
        )}

        {cvError && (
          <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
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

      <form onSubmit={save} className="mt-6 space-y-6">
        <Section title="Basics">
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
          subtitle="PIs you currently work with — the core of connection-first scoring."
        >
          <div className="space-y-3">
            {profile.current_advisors.map((a, i) => (
              <div
                key={i}
                className="flex flex-col gap-3 rounded-xl border border-white/10 bg-black/20 p-4 sm:flex-row sm:items-end"
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
                >
                  Remove
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
              + Add advisor
            </button>
          </div>
        </Section>

        <Section
          title="Papers"
          subtitle="Publications, preprints, and manuscripts in preparation."
        >
          <div className="space-y-3">
            {profile.papers.map((p, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/10 bg-black/20 p-4"
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
              + Add paper
            </button>
          </div>
        </Section>

        <Section
          title="Research experiences"
          subtitle="Lab stints, REUs, internships — with what they produced."
        >
          <div className="space-y-3">
            {profile.experiences.map((x, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/10 bg-black/20 p-4"
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
              + Add experience
            </button>
          </div>
        </Section>

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary rounded-lg px-6 py-2.5 font-medium disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
          {message && (
            <span
              className={
                message.kind === "ok" ? "text-sm text-emerald-400" : "text-sm text-red-400"
              }
            >
              {message.text}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
