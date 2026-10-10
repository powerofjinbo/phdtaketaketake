// Admission-probability feature: document parsing (CV / SOP / transcript),
// per-target deep background research, and the call into the Python
// estimator (phd_matcher.admission) running in the Pyodide worker.
//
// Data-integrity contract (same as the matcher): documents are parsed for
// facts they actually state; research fills only what a fetched page says;
// anything missing widens the estimator's interval instead of being guessed.

import { agentTurn, completion, hasWebSearch, type LlmSettings } from "./llm";
import { estimateAdmission, onEngineStatus } from "./engine";
import { CV_PARSE_SYSTEM, extractCvProfile } from "./research";
import type { Advisor, Experience, GpaScale, Paper } from "./types";

// ---------------------------------------------------------------------------
// Types (mirror phd_matcher/admission/models.py)
// ---------------------------------------------------------------------------

export type SchoolTier = "top_10" | "top_11_30" | "top_31_60" | "top_60_plus";
export type ContactStatus =
  | "none"
  | "emailed_no_reply"
  | "positive_reply"
  | "meeting_held"
  | "pi_invited_application";
export type Stage = "pre_application" | "interview" | "waitlist";
export type UndergradTier = "elite" | "strong" | "regular" | "unknown";
export type Fellowship = "none" | "applying" | "secured";
export type Prominence = "field_leader" | "established" | "junior_or_unknown";

export interface Course {
  name: string;
  grade: string | number;
  credits?: number | null;
  level?: "undergrad" | "graduate";
  year?: number | null;
  is_core?: boolean | null;
}

export interface TranscriptJson {
  courses: Course[];
  grade_scale?: "letter" | "4.0" | "4.3" | "4.5" | "100" | null;
  class_rank_percentile?: number | null;
}

export interface SopReading {
  research_specificity: number;
  direction_coherence: number;
  named_faculty: string[];
  note: string;
}

export interface LetterWriter {
  name: string;
  prominence: Prominence;
  is_research_supervisor: boolean;
}

export interface TargetDraft {
  key: string;
  institution: string;
  program: string;
  professor: string;
  tier: "" | SchoolTier;
  contact_status: ContactStatus;
  stage: Stage;
}

export interface DocStatus {
  name: string;
  parsed_at: string;
}

export interface AdmissionDraft {
  field: string;
  undergrad_institution: string;
  undergrad_tier: UndergradTier;
  gpa_raw: string;
  gpa_scale: GpaScale;
  research_interests: string;
  application_direction: string;
  publications: Paper[];
  no_publications: boolean;
  transcript: TranscriptJson | null;
  gre_verbal: string;
  gre_quant: string;
  gre_writing: string;
  gre_subject_name: string;
  gre_subject_score: string;
  gre_subject_pct: string;
  is_international: "" | "yes" | "no";
  external_fellowship: Fellowship;
  fellowship_name: string;
  current_advisors: Advisor[];
  experiences: Experience[];
  letters: LetterWriter[];
  sop: SopReading | null;
  docs: { cv?: DocStatus; sop?: DocStatus; transcript?: DocStatus };
  targets: TargetDraft[];
}

export interface FactorContribution {
  key: string;
  label: string;
  label_zh: string;
  state: "known" | "uncertain" | "missing";
  z: number;
  weight: number;
  delta_pp: number;
  note: string | null;
}

export interface Lever {
  key: string;
  label: string;
  label_zh: string;
  probability: number;
  delta_pp: number;
}

export interface AdmissionEstimate {
  target_id: string;
  institution: string;
  program: string | null;
  pi_name: string | null;
  stage: Stage;
  probability: number;
  interval_80: [number, number];
  probability_with_pi: number | null;
  interval_80_with_pi: [number, number] | null;
  verdict: "long_shot" | "reach" | "possible" | "competitive" | "strong";
  confidence: "A" | "B" | "C" | "D";
  base_rate: number;
  base_rate_source: "verified_program_stat" | "unverified_program_stat" | "field_tier_prior";
  p_pi_decides: number;
  applicant_index: number;
  pool_percentile: number;
  factors: FactorContribution[];
  adjustments: string[];
  levers: Lever[];
  missing_inputs: string[];
  warnings: string[];
}

export interface PortfolioEstimate {
  estimates: AdmissionEstimate[];
  p_at_least_one: number;
  p_at_least_one_if_independent: number;
  expected_offers: number;
  note: string;
}

export interface StoredAdmissionResult {
  created_at: string;
  provider: string;
  web_search: boolean;
  result: PortfolioEstimate;
}

// ---------------------------------------------------------------------------
// Draft persistence (this browser only)
// ---------------------------------------------------------------------------

const DRAFT_KEY = "phdtake:admission-draft";
const RESULT_KEY = "phdtake:admission-result";

export function newTarget(): TargetDraft {
  return {
    key: Math.random().toString(36).slice(2, 9),
    institution: "",
    program: "",
    professor: "",
    tier: "",
    contact_status: "none",
    stage: "pre_application",
  };
}

export const emptyDraft: AdmissionDraft = {
  field: "",
  undergrad_institution: "",
  undergrad_tier: "unknown",
  gpa_raw: "",
  gpa_scale: "4.0",
  research_interests: "",
  application_direction: "",
  publications: [],
  no_publications: false,
  transcript: null,
  gre_verbal: "",
  gre_quant: "",
  gre_writing: "",
  gre_subject_name: "",
  gre_subject_score: "",
  gre_subject_pct: "",
  is_international: "",
  external_fellowship: "none",
  fellowship_name: "",
  current_advisors: [],
  experiences: [],
  letters: [],
  sop: null,
  docs: {},
  targets: [],
};

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked — the page still works for this session */
  }
}

export function loadDraft(): AdmissionDraft | null {
  const d = readJson<Partial<AdmissionDraft>>(DRAFT_KEY);
  return d ? { ...emptyDraft, ...d, docs: d.docs ?? {} } : null;
}

export function saveDraft(d: AdmissionDraft) {
  writeJson(DRAFT_KEY, d);
}

export function loadAdmissionResult(): StoredAdmissionResult | null {
  return readJson<StoredAdmissionResult>(RESULT_KEY);
}

function saveAdmissionResult(r: StoredAdmissionResult) {
  writeJson(RESULT_KEY, r);
}

// ---------------------------------------------------------------------------
// JSON extraction
// ---------------------------------------------------------------------------

export function extractJsonObject(text: string): Record<string, unknown> {
  const blocks = [...text.matchAll(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/g)];
  for (let i = blocks.length - 1; i >= 0; i--) {
    try {
      const v = JSON.parse(blocks[i][1]);
      if (v && typeof v === "object" && !Array.isArray(v)) return v;
    } catch {
      /* try next */
    }
  }
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end > start) {
    try {
      const v = JSON.parse(text.slice(start, end + 1));
      if (v && typeof v === "object" && !Array.isArray(v)) return v;
    } catch {
      /* fall through */
    }
  }
  throw new Error("The model returned no parseable JSON. Try again or switch models in Settings.");
}

// ---------------------------------------------------------------------------
// Document parsing
// ---------------------------------------------------------------------------

export const TRANSCRIPT_PARSE_SYSTEM = `You parse an academic transcript into strict JSON. Copy ONLY what the
transcript states — never invent courses, grades or ranks. Output a single
\`\`\`json fenced block:

{
  "grade_scale": "letter" | "4.0" | "4.3" | "4.5" | "100" | null,
  "class_rank_percentile": number or null   (top X percent, only if the transcript states a rank, e.g. "3/120" → 2.5),
  "courses": [
    {"name": str (as printed, keep the original language),
     "grade": str or number exactly as printed (e.g. "A-", "93", 3.7, "优秀", "P"),
     "credits": number or null,
     "level": "undergrad" | "graduate"  (graduate only if the transcript marks it as a graduate / 研究生 course or uses a graduate course number),
     "year": integer year of study 1-8 or null (derive from the term order: the first academic year on the transcript is 1)}
  ]
}

Include every graded course. Skip transfer-credit and withdrawal lines.`;

export async function parseTranscript(
  settings: LlmSettings,
  text: string
): Promise<TranscriptJson> {
  const reply = await completion(
    settings,
    TRANSCRIPT_PARSE_SYSTEM,
    "Transcript text:\n\n" + text.slice(0, 45000)
  );
  const raw = extractJsonObject(reply);
  const courses = Array.isArray(raw.courses) ? raw.courses : [];
  const clean: Course[] = [];
  for (const c of courses as Record<string, unknown>[]) {
    if (!c || typeof c.name !== "string" || c.grade === undefined || c.grade === null) continue;
    const grade = typeof c.grade === "number" ? c.grade : String(c.grade).trim();
    if (grade === "") continue;
    const year = Number(c.year);
    const credits = Number(c.credits);
    clean.push({
      name: c.name,
      grade,
      credits: Number.isFinite(credits) && credits > 0 ? credits : null,
      level: c.level === "graduate" ? "graduate" : "undergrad",
      year: Number.isInteger(year) && year >= 1 && year <= 8 ? year : null,
    });
  }
  if (!clean.length) throw new Error("No graded courses were found in this transcript.");
  const scale = raw.grade_scale as TranscriptJson["grade_scale"];
  const rank = Number(raw.class_rank_percentile);
  return {
    courses: clean,
    grade_scale: ["letter", "4.0", "4.3", "4.5", "100"].includes(String(scale)) ? scale : null,
    class_rank_percentile: Number.isFinite(rank) && rank > 0 && rank <= 100 ? rank : null,
  };
}

export const SOP_READ_SYSTEM = `You are a PhD admissions reader assessing a statement of purpose. Judge
ONLY what the text shows. Output a single \`\`\`json fenced block:

{
  "research_specificity": 0-1  (0.2 = generic enthusiasm; 0.5 = names a topic and some past work;
                                0.8 = concrete questions, methods and the applicant's own results;
                                1.0 = a research plan a faculty member could evaluate),
  "direction_coherence": 0-1   (do past experiences → stated interests → the program form one
                                believable story? 0.5 = loosely connected),
  "named_faculty": [str]       (professors the SOP names, exactly as written; [] if none),
  "note": str                  (one sentence: the main strength or gap a reader would notice)
}`;

export async function readSop(
  settings: LlmSettings,
  text: string,
  direction: string
): Promise<SopReading> {
  const reply = await completion(
    settings,
    SOP_READ_SYSTEM,
    `Applicant's stated application direction: ${direction || "(not given)"}\n\nSOP text:\n\n` +
      text.slice(0, 30000)
  );
  const raw = extractJsonObject(reply);
  const clamp = (v: unknown) => {
    const n = Number(v);
    return Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 0.5;
  };
  return {
    research_specificity: clamp(raw.research_specificity),
    direction_coherence: clamp(raw.direction_coherence),
    named_faculty: Array.isArray(raw.named_faculty)
      ? (raw.named_faculty as unknown[]).filter((x): x is string => typeof x === "string")
      : [],
    note: typeof raw.note === "string" ? raw.note : "",
  };
}

/** CV → the applicant fields it can prefill (reuses the profile CV parser). */
export async function parseCv(
  settings: LlmSettings,
  text: string
): Promise<{ patch: Partial<AdmissionDraft>; warnings: string[] }> {
  const reply = await completion(settings, CV_PARSE_SYSTEM, "CV text:\n\n" + text.slice(0, 40000));
  const { profile, warnings } = extractCvProfile(reply);
  const p = profile as Record<string, unknown>;
  const patch: Partial<AdmissionDraft> = {};
  if (typeof p.field === "string" && p.field) patch.field = p.field;
  if (typeof p.undergrad_institution === "string" && p.undergrad_institution)
    patch.undergrad_institution = p.undergrad_institution;
  if (p.gpa_raw !== undefined && p.gpa_raw !== null && p.gpa_raw !== "")
    patch.gpa_raw = String(p.gpa_raw);
  if (typeof p.gpa_scale === "string") patch.gpa_scale = p.gpa_scale as GpaScale;
  if (typeof p.research_direction === "string" && p.research_direction)
    patch.research_interests = p.research_direction;
  if (Array.isArray(p.papers)) patch.publications = p.papers as Paper[];
  if (Array.isArray(p.current_advisors)) patch.current_advisors = p.current_advisors as Advisor[];
  if (Array.isArray(p.experiences)) patch.experiences = p.experiences as Experience[];
  return { patch, warnings };
}

// ---------------------------------------------------------------------------
// Applicant assembly + required-field check
// ---------------------------------------------------------------------------

export function missingRequired(d: AdmissionDraft): string[] {
  const missing: string[] = [];
  if (!d.field.trim()) missing.push("field");
  if (!d.undergrad_institution.trim()) missing.push("undergraduate institution");
  if (!d.gpa_raw.trim() || (d.gpa_scale !== "uk" && !Number.isFinite(Number(d.gpa_raw))))
    missing.push("GPA");
  if (!d.transcript || d.transcript.courses.length === 0) missing.push("transcript");
  if (d.publications.length === 0 && !d.no_publications)
    missing.push("publications (add them, or tick “I have no publications”)");
  if (!d.research_interests.trim()) missing.push("research interests");
  if (!d.application_direction.trim()) missing.push("application direction");
  if (!d.targets.some((t) => t.institution.trim())) missing.push("at least one target school");
  return missing;
}

function num(s: string): number | null {
  if (!s.trim()) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function buildApplicant(d: AdmissionDraft, targetProfessor?: string): Record<string, unknown> {
  const gre: Record<string, number> = {};
  const v = num(d.gre_verbal);
  const q = num(d.gre_quant);
  const w = num(d.gre_writing);
  if (v !== null) gre.verbal = v;
  if (q !== null) gre.quant = q;
  if (w !== null) gre.writing = w;
  const subPct = num(d.gre_subject_pct);
  const subScore = num(d.gre_subject_score);
  const sop = d.sop
    ? {
        research_specificity: d.sop.research_specificity,
        direction_coherence: d.sop.direction_coherence,
        names_target_faculty: targetProfessor
          ? d.sop.named_faculty.some((n) =>
              n.toLowerCase().includes(lastName(targetProfessor).toLowerCase())
            )
          : null,
        note: d.sop.note || null,
      }
    : null;
  return {
    field: d.field.trim(),
    undergrad_institution: d.undergrad_institution.trim(),
    undergrad_tier: d.undergrad_tier,
    gpa_raw: d.gpa_scale === "uk" ? d.gpa_raw.trim() : Number(d.gpa_raw),
    gpa_scale: d.gpa_scale,
    transcript: d.transcript,
    publications: d.no_publications ? [] : d.publications,
    research_interests: d.research_interests.trim(),
    application_direction: d.application_direction.trim(),
    gre_general: Object.keys(gre).length ? gre : null,
    gre_subject:
      subPct !== null && d.gre_subject_name.trim()
        ? { subject: d.gre_subject_name.trim(), percentile: subPct, score: subScore }
        : null,
    current_advisors: d.current_advisors.filter((a) => a.name.trim()),
    experiences: d.experiences,
    letters: d.letters.filter((l) => l.name.trim()),
    is_international: d.is_international === "" ? null : d.is_international === "yes",
    external_fellowship: d.external_fellowship,
    fellowship_name: d.fellowship_name.trim() || null,
    sop,
  };
}

function lastName(full: string): string {
  const parts = full.replace(/^(prof\.?|dr\.?)\s+/i, "").trim().split(/\s+/);
  return parts[parts.length - 1] || full;
}

// ---------------------------------------------------------------------------
// Deep background research — one agent turn per target
// ---------------------------------------------------------------------------

export const ADMISSION_RESEARCH_SYSTEM = `You are the admissions research agent for PhDTake.

CARDINAL RULE — REAL DATA ONLY. Every value you set MUST trace to a web page
you actually saw in this conversation, recorded as an evidence item:
  {"url": "...", "source_type": "lab_page|faculty_page|google_scholar|openalex|inspire|pubmed|us_news|other",
   "claim": "the specific fact seen at that URL", "supports_fields": ["<field>"]}
If you searched and found nothing, OMIT the field. Never fill from memory,
never estimate a number you did not read. Missing data is handled honestly
by the estimator (it widens the interval); invented data is forbidden.

For ONE target program (and optionally one professor) research:
1. Program admissions statistics — the department's own admissions/statistics
   page, graduate catalog, or official report: applicants and offers (or the
   stated admit rate) and the cycle year. Evidence supports_fields:
   ["admission:admit_rate"].
2. Program profile — admission model (direct_admit / rotation / centralized /
   mixed), typical cohort size, funding structure (guaranteed / pi_grant /
   fellowship_first / mixed), international friendliness (0-1, only from a
   stated share of international students). Evidence keys and
   supports_fields use "program:<field>".
3. School tier for this field: top_10 | top_11_30 | top_31_60 | top_60_plus,
   from a ranking page (evidence supports_fields ["school_tier"]).
4. If a professor is given, a full candidate record:
   - research_areas from their faculty/lab page and recent papers
   - pi_signal (strong | normal | shrinking | not_recruiting) only if a page
     says they are / are not taking students; else omit
   - paths_to_advisors: for EACH of the applicant's advisor ids, search for
     co-authored papers (small_team_coauthor_5y for ≤10 authors,
     big_collab_papers_5y otherwise), shared genealogy, shared working groups,
     shared grants. Record a verified-empty search as {"items": [{...,
     "supports_fields": ["path:<advisor_id>"]}]}.
   - research_fit: {"topic_fit", "method_fit", "system_or_dataset_fit",
     "temporal_fit", "grant_fit", "student_background_fit"} each 0-1, judged
     against the applicant's direction using the professor's recent papers,
     with evidence {"research_fit": {"items": [... supports_fields
     ["research_fit"]]}}.

Output ONE \`\`\`json fenced object:
{
  "institution": str, "program": str or omit,
  "school_tier": "top_10|top_11_30|top_31_60|top_60_plus",
  "stats": {"applicants": int, "offers": int, "reported_admit_rate": 0-1,
            "cycle_year": int, "evidence": {"items": [...]}}  (omit if not found),
  "program_profile": {"admission_model": ..., "cohort_size_estimate": int,
            "funding_structure": ..., "international_friendliness": 0-1,
            "evidence": {"<field>": {"items": [...]}}}  (omit fields not found),
  "pi": {"id": "pi", "name": str, "institution": str, "school_tier": same,
         "field": <applicant field>, "research_areas": [...], "pi_signal": ...,
         "paths_to_advisors": {...}, "research_fit": {...},
         "evidence": {"school_tier": {"items": [...]}, "research_areas": {"items": [...]},
                      "pi_signal": {"items": [...]}}}  (omit "pi" when no professor was given)
}`;

const NO_SEARCH_NOTE = `

NOTE: this provider has NO web-search tool, so you cannot verify anything.
Per the cardinal rule output only {"institution", "program", "school_tier"
(only if you are certain), and for a professor only "name", "institution",
"field", "research_areas"} — no stats, no program_profile, no paths, no
research_fit. The estimator will use its priors with wide intervals.`;

async function researchTarget(
  settings: LlmSettings,
  applicant: Record<string, unknown>,
  t: TargetDraft,
  onProgress: (line: string) => void
): Promise<Record<string, unknown>> {
  const web = hasWebSearch(settings.provider);
  const advisors = (applicant.current_advisors as Advisor[]) || [];
  const userMsg =
    `Target institution: ${t.institution}\n` +
    (t.program ? `Program: ${t.program}\n` : "") +
    (t.professor ? `Professor: ${t.professor}\n` : "No professor given — research the program only.\n") +
    `Applicant field: ${applicant.field}\n` +
    `Applicant application direction: ${applicant.application_direction}\n` +
    `Applicant research interests: ${applicant.research_interests}\n` +
    `Applicant's current advisors (use these ids in paths_to_advisors): ` +
    (advisors.length
      ? advisors.map((a) => `${a.id} = ${a.name} (${a.institution})`).join("; ")
      : "none listed") +
    "\n\nResearch now, then output the single JSON object.";
  const text = await agentTurn(
    settings,
    ADMISSION_RESEARCH_SYSTEM + (web ? "" : NO_SEARCH_NOTE),
    userMsg,
    onProgress
  );
  try {
    return extractJsonObject(text);
  } catch {
    const repaired = await completion(
      settings,
      "You reformat text into strict JSON. Output ONLY the JSON object (in a ```json fenced block) described, with no commentary.",
      text.slice(0, 40000)
    );
    return extractJsonObject(repaired);
  }
}

function assembleTarget(
  t: TargetDraft,
  researched: Record<string, unknown>,
  field: string
): Record<string, unknown> {
  const out: Record<string, unknown> = {
    id: t.key,
    institution: t.institution.trim(),
    program: t.program.trim() || (researched.program as string) || null,
    field,
    stage: t.stage,
    contact_status: t.contact_status,
  };
  const tier = t.tier || (researched.school_tier as string) || "";
  if (tier) out.school_tier = tier;
  if (researched.stats && typeof researched.stats === "object") out.stats = researched.stats;
  if (researched.program_profile && typeof researched.program_profile === "object")
    out.program_profile = researched.program_profile;
  if (t.professor.trim() && researched.pi && typeof researched.pi === "object") {
    const pi = { ...(researched.pi as Record<string, unknown>) };
    pi.id = pi.id || "pi";
    pi.name = pi.name || t.professor.trim();
    pi.institution = pi.institution || t.institution.trim();
    pi.field = field;
    if (!pi.school_tier && tier) pi.school_tier = tier;
    out.pi = pi;
  }
  return out;
}

export interface RunOptions {
  settings: LlmSettings;
  draft: AdmissionDraft;
  onProgress: (line: string) => void;
}

export async function runAdmission({ settings, draft, onProgress }: RunOptions): Promise<StoredAdmissionResult> {
  const targets = draft.targets.filter((t) => t.institution.trim());
  const baseApplicant = buildApplicant(draft);
  const assembled: Record<string, unknown>[] = [];
  for (const [i, t] of targets.entries()) {
    const label = t.professor ? `${t.professor} · ${t.institution}` : t.institution;
    onProgress(`Researching ${label} (${i + 1}/${targets.length})…`);
    let researched: Record<string, unknown> = {};
    try {
      researched = await researchTarget(settings, baseApplicant, t, (line) =>
        onProgress(`${label}: ${line}`)
      );
    } catch (e) {
      onProgress(`${label}: research failed (${e instanceof Error ? e.message : e}); using priors`);
    }
    assembled.push(assembleTarget(t, researched, String(baseApplicant.field)));
  }
  const unresolved = assembled.filter((t) => !t.school_tier);
  if (unresolved.length) {
    throw new Error(
      `Couldn't determine the ranking tier for ${unresolved
        .map((t) => t.institution)
        .join(", ")}. Pick a tier for that school and run again.`
    );
  }

  onProgress("Estimating probabilities in your browser…");
  const unsubscribe = onEngineStatus(onProgress);
  let out: PortfolioEstimate & { error?: string; details?: string[] };
  try {
    // SOP "names this professor" is per target, so the applicant JSON is
    // built per target when an SOP was uploaded; otherwise one call.
    if (draft.sop && targets.some((t) => t.professor.trim())) {
      const parts: PortfolioEstimate[] = [];
      for (const [i, t] of targets.entries()) {
        const r = await estimateAdmission<PortfolioEstimate & { error?: string; details?: string[] }>(
          buildApplicant(draft, t.professor),
          [assembled[i]]
        );
        if (r.error) throw new Error([r.error, ...(r.details || [])].join("\n"));
        parts.push(r);
      }
      // Combined portfolio numbers need the shared draws, so recompute them
      // in one call with the base applicant.
      const all = await estimateAdmission<PortfolioEstimate & { error?: string; details?: string[] }>(
        baseApplicant,
        assembled
      );
      if (all.error) throw new Error([all.error, ...(all.details || [])].join("\n"));
      out = { ...all, estimates: parts.map((p) => p.estimates[0]) };
    } else {
      out = await estimateAdmission(baseApplicant, assembled);
      if (out.error) throw new Error([out.error, ...(out.details || [])].join("\n"));
    }
  } finally {
    unsubscribe();
  }
  const stored: StoredAdmissionResult = {
    created_at: new Date().toISOString(),
    provider: settings.provider,
    web_search: hasWebSearch(settings.provider),
    result: out,
  };
  saveAdmissionResult(stored);
  return stored;
}
