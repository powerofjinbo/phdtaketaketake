// The in-browser research → score pipeline. Mirrors the phdtaketaketake
// skill's data-integrity contract: real sources only, missing beats guessed.

import { agentTurn, hasWebSearch, type LlmSettings } from "./llm";
import { rankCandidates, onEngineStatus } from "./engine";
import {
  newRunId,
  upsertRun,
  type StoredRun,
  type StudentProfileJson,
} from "./store";

export const RESEARCH_SYSTEM = `You are the research agent for PhDTake, a truth-based PhD advisor matcher.

CARDINAL RULE — REAL DATA ONLY. Every value you set on a candidate MUST trace
to a web search result you actually saw in this conversation. If you searched
and found nothing, leave the field at its default and record a verified-empty
evidence item describing what you searched. NEVER guess from prior knowledge,
name patterns, or plausibility. Missing data widens the confidence band —
that is the correct, honest outcome. Fabricated data is forbidden.

Your job: given a student profile and a target (school tier or list), use web
search to (1) find active PIs whose research matches the student's direction,
(2) verify connection edges between each PI and the student's current
advisors (co-authorship — distinguish small-team vs big-collaboration by the
field's author-count threshold; shared genealogy; working groups), and
(3) capture recruiting/funding signals ONLY when a page you fetched states
them.

Evidence format: every non-default field needs an entry in the candidate's
evidence maps with structured items:
  {"url": "...", "source_type": "google_scholar|openalex|inspire|pubmed|lab_page|us_news|other",
   "claim": "specific fact seen at that URL", "supports_fields": ["<field name>"]}

Connection paths go in paths_to_advisors keyed by the advisor id given in the
profile, with the same items structure (supports_fields naming the PathEdge
subfields, or ["path:<advisor_id>"] for a verified-empty search).

When you are done researching, output your final answer as a single fenced
JSON code block (\`\`\`json ... \`\`\`) containing an array of candidate objects
with this shape (omit fields you could not verify):

{
  "id": "cand_001",
  "name": "...", "institution": "...",
  "school_tier": "top_10|top_11_30|top_31_60|top_60_plus",
  "field": "<same as student field>",
  "research_areas": ["...", "..."],
  "pi_signal": "strong|normal|shrinking|missing|not_recruiting",
  "normalized_collab_top20pct": 0.0-1.0 or omit,
  "grad_placement_quality": 0.0-1.0 or omit,
  "paths_to_advisors": { "<advisor_id>": { "small_team_coauthor_5y": N,
      "big_collab_papers_5y": N, "items": [ ...evidence... ], "note": "..." } },
  "evidence": { "school_tier": {"items": [...]}, "research_areas": {"items": [...]},
                "pi_signal": {"items": [...]} }
}

Quality bar: PI has ≥1 matching paper in the last 3 years; skip emeriti and
admin-only faculty. Aim for 8–15 candidates. Do not pad with unverified
candidates — fewer well-evidenced candidates beat many guessed ones.`;

export const NO_WEB_SEARCH_ADDENDUM = `

NOTE: this provider has NO web-search tool. You therefore CANNOT verify new
facts. Per the cardinal rule you must NOT fill values from memory. Emit
candidates ONLY as name/institution/field/research_areas suggestions with NO
connection paths, NO tier evidence, and pi_signal "missing" — the user will
see them ranked with maximally wide confidence bands, which is the honest
outcome. State this limitation in your reply.`;

export function extractJsonArray(text: string): unknown[] {
  const blocks = [...text.matchAll(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/g)];
  for (let i = blocks.length - 1; i >= 0; i--) {
    try {
      const data = JSON.parse(blocks[i][1]);
      if (Array.isArray(data)) return data;
    } catch {
      /* try next */
    }
  }
  const start = text.indexOf("[");
  const end = text.lastIndexOf("]");
  if (start !== -1 && end > start) {
    try {
      const data = JSON.parse(text.slice(start, end + 1));
      if (Array.isArray(data)) return data;
    } catch {
      /* fall through */
    }
  }
  throw new Error(
    "The research agent returned no parseable JSON candidate list. Try again, or try a different model."
  );
}

export interface StartRunInput {
  profile: StudentProfileJson;
  target: string;
  topK: number;
  strict: boolean;
  settings: LlmSettings;
}

// Starts the pipeline in the page (async, fire-and-forget). Progress is
// persisted to localStorage so the dashboard and results pages can follow.
export function startRun(input: StartRunInput): string {
  const id = newRunId();
  const run: StoredRun = {
    id,
    created_at: new Date().toISOString(),
    target: input.target,
    top_k: input.topK,
    strict: input.strict,
    provider: input.settings.provider,
    status: "researching",
    progress_note: hasWebSearch(input.settings.provider)
      ? "launching research agent (live web search)"
      : "launching research agent (no web search on this provider — evidence will be thin)",
    results: null,
    portfolio_summary: null,
    field_caveats: [],
    error: null,
  };
  upsertRun(run);
  void pipeline(run, input);
  return id;
}

async function pipeline(run: StoredRun, input: StartRunInput) {
  const update = (patch: Partial<StoredRun>) => {
    Object.assign(run, patch);
    upsertRun(run);
  };
  try {
    const system =
      RESEARCH_SYSTEM +
      (hasWebSearch(input.settings.provider) ? "" : NO_WEB_SEARCH_ADDENDUM);
    const userMsg =
      "Student profile (JSON):\n" +
      JSON.stringify(input.profile, null, 2) +
      `\n\nTarget programs: ${input.target}\n\n` +
      "Research candidate PIs now. Use web search extensively. Then output " +
      "the final candidates JSON array in a single ```json fenced block.";
    const text = await agentTurn(input.settings, system, userMsg, (note) =>
      update({ progress_note: note })
    );
    const rawCandidates = extractJsonArray(text);
    update({
      status: "scoring",
      progress_note: `${rawCandidates.length} candidates discovered; scoring in-browser`,
    });
    // First-ever run downloads ~13 MB of Pyodide here — keep the run's
    // heartbeat fresh (and show progress) via the engine's status notes, so
    // the stale-run reaper doesn't mistake a slow download for an orphan.
    const unsubscribe = onEngineStatus((note) => update({ progress_note: note }));
    let out;
    try {
      out = await rankCandidates(
        input.profile,
        rawCandidates,
        input.topK,
        input.strict
      );
    } finally {
      unsubscribe();
    }
    if (out.error) {
      update({
        status: "error",
        error:
          out.error +
          (out.strict_errors?.length
            ? ` — strict rejections: ${out.strict_errors.join("; ")}`
            : "") +
          (out.dropped?.length ? ` — schema drops: ${out.dropped.join("; ")}` : ""),
      });
      return;
    }
    update({
      status: "done",
      results: out.results || [],
      portfolio_summary: out.portfolio_summary || null,
      field_caveats: out.field_caveats || [],
      progress_note: `done — ${out.results?.length ?? 0} ranked candidates`,
    });
  } catch (e) {
    let msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("Failed to fetch")) {
      msg =
        "Could not reach the LLM provider from your browser. Check your network and API key in Settings — or switch to Claude / OpenAI / Gemini, which are verified browser-compatible.";
    }
    update({ status: "error", error: msg });
  }
}

export const CV_PARSE_SYSTEM = `You parse a PhD applicant's CV text into a strict JSON profile. Extract ONLY
facts explicitly present in the CV — never infer or embellish. Output a
single \`\`\`json fenced block:

{
  "name": str or omit,
  "field": str (e.g. "physics", "biology", "cs") — infer only from explicit CV content,
  "undergrad_institution": str,
  "gpa_raw": number, "gpa_scale": "4.0"|"4.3"|"4.5"|"100"|"uk_honours",
  "research_direction": 1-2 sentence summary built strictly from the CV's stated research topics,
  "current_advisors": [{"id": "adv_001", "name": str, "institution": str}],
  "papers": [{"title": str, "journal": str, "journal_tier": 1-5 (4 if unsure),
              "author_position": int, "status": "published"|"accepted"|"submitted"|"preprint"|"in_prep",
              "year": int}],
  "experiences": [{"lab_pi_name": str, "lab_tier": 1-4 (3 if unsure),
                   "duration_months": int, "output_type": "paper"|"poster"|"thesis"|"none"}]
}

Omit any field the CV does not state. After the JSON block, list one warning
line per field you omitted or were unsure about, prefixed "WARN: ".`;

export function extractCvProfile(text: string): {
  profile: StudentProfileJson;
  warnings: string[];
} {
  const m = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (!m) throw new Error("The CV parser returned no JSON — try again.");
  const profile = JSON.parse(m[1]) as StudentProfileJson;
  const warnings = text
    .split("\n")
    .filter((l) => l.trim().startsWith("WARN:"))
    .map((l) => l.trim().slice(5).trim());
  return { profile, warnings };
}
