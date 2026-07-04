"""Claude-powered deep-research pipeline for a match run.

Runs in a background thread. Steps:
  1. researching — a Claude agent with the web_search server tool discovers
     candidate PIs and collects evidence-cited connection/opportunity signals,
     following the phdtaketaketake data-integrity contract (real sources only;
     missing beats guessed).
  2. scoring — candidates are validated against the strict Pydantic schema and
     ranked by the deterministic phd_matcher engine (CAPEG → application
     strength → risk/difficulty adjustment → strategy buckets).
"""

import json
import re
import threading
import traceback

from . import engine as eng
from .db import SessionLocal
from .models import Run
from .providers import LLMConfig, run_agent_turn

RESEARCH_SYSTEM = """\
You are the research agent for PhDTake, a truth-based PhD advisor matcher.

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
JSON code block (```json ... ```) containing an array of candidate objects
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
candidates — fewer well-evidenced candidates beat many guessed ones.
"""


def _update(run_id: int, **fields):
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        for k, v in fields.items():
            setattr(run, k, v)
        db.commit()
    finally:
        db.close()


def _extract_json_array(text: str) -> list:
    blocks = re.findall(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            continue
    # fallback: largest bracketed span
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    raise ValueError("research agent returned no parseable JSON candidate array")


NO_WEB_SEARCH_ADDENDUM = """

NOTE: this provider has NO web-search tool. You therefore CANNOT verify new
facts. Per the cardinal rule you must NOT fill values from memory. Emit
candidates ONLY as name/institution/field/research_areas suggestions with NO
connection paths, NO tier evidence, and pi_signal "missing" — the user will
see them ranked with maximally wide confidence bands, which is the honest
outcome. State this limitation in your reply.
"""


def _run_research_agent(
    run_id: int, profile: dict, target: str, cfg: LLMConfig
) -> list[dict]:
    system = RESEARCH_SYSTEM + ("" if cfg.has_web_search else NO_WEB_SEARCH_ADDENDUM)
    user_msg = (
        "Student profile (JSON):\n"
        + json.dumps(profile, ensure_ascii=False, indent=2)
        + f"\n\nTarget programs: {target}\n\n"
        "Research candidate PIs now. Use web search extensively. Then output "
        "the final candidates JSON array in a single ```json fenced block."
    )
    text = run_agent_turn(
        cfg,
        system,
        user_msg,
        on_progress=lambda note: _update(run_id, progress_note=note),
    )
    return _extract_json_array(text)


def _score(run_id: int, profile: dict, raw_candidates: list[dict], top_k: int, strict: bool):
    student = eng.StudentProfile(**profile)
    field_profile = eng.resolve_field_profile(student.field)
    if field_profile and student.field != field_profile.id:
        student.field = field_profile.id

    candidates, dropped = [], []
    for raw in raw_candidates:
        try:
            cand = eng.CandidateAdvisor(**raw)
            if field_profile and cand.field != field_profile.id:
                cand_fp = eng.resolve_field_profile(cand.field)
                if cand_fp and cand_fp.id == field_profile.id:
                    cand.field = field_profile.id
            candidates.append(cand)
        except Exception as e:
            dropped.append(f"{raw.get('name', raw.get('id', '?'))}: {e}")

    strict_errors = []
    if strict:
        for cand in candidates:
            strict_errors += eng.strict_validate(student, cand)
        if strict_errors:
            # keep only candidates with zero unsourced claims
            bad_ids = {e.split("candidate=")[1].split(" ")[0] for e in strict_errors}
            candidates = [c for c in candidates if c.id not in bad_ids]

    if not candidates:
        raise ValueError(
            "no valid candidates survived validation"
            + (f" (strict rejections: {strict_errors[:5]})" if strict_errors else "")
            + (f" (schema drops: {dropped[:5]})" if dropped else "")
        )

    results = eng.rank_advisors(
        student, candidates, top_k=top_k, field_profile=field_profile
    )
    for r in results:
        if r.strategy is None:
            r.strategy = eng.recommend_strategy(r)
    summary = eng.summarize_portfolio(results)
    notes = " ".join(summary.portfolio_notes) if summary.portfolio_notes else ""
    if dropped:
        notes += f" ({len(dropped)} discovered candidates dropped for schema errors.)"
    if strict_errors:
        notes += f" ({len(strict_errors)} unsourced claims rejected by strict mode.)"
    return [json.loads(r.model_dump_json()) for r in results], notes


def _pipeline(
    run_id: int, profile: dict, target: str, top_k: int, strict: bool, cfg: LLMConfig
):
    try:
        note = "launching research agent"
        if not cfg.has_web_search:
            note += " (custom provider: NO web search — evidence will be thin)"
        _update(run_id, status="researching", progress_note=note)
        raw = _run_research_agent(run_id, profile, target, cfg)
        _update(
            run_id,
            status="scoring",
            progress_note=f"{len(raw)} candidates discovered; scoring",
        )
        results, summary = _score(run_id, profile, raw, top_k, strict)
        _update(
            run_id,
            status="done",
            results=results,
            portfolio_summary=summary,
            progress_note=f"done — {len(results)} ranked candidates",
        )
    except Exception as e:
        traceback.print_exc()
        _update(run_id, status="error", error=str(e))


def start_run(
    run_id: int, profile: dict, target: str, top_k: int, strict: bool, cfg: LLMConfig
):
    t = threading.Thread(
        target=_pipeline,
        args=(run_id, profile, target, top_k, strict, cfg),
        daemon=True,
    )
    t.start()
