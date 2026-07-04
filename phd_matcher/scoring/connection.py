"""Connection score (C) — Sprint-2 v2 expanded network model.

C is the core differentiator of this skill: PhD admissions hinge on
real advisor-network signals, not pretty CV numbers. Connection v2
expands `PathEdge` from a handful of edge types into a richer network
graph (co-mentored students, shared grants, committee/exam overlap,
shared institute, prior-institution overlap, conference sessions),
adds a small **secondary bonus** so multiple verified edges combine,
and applies a **recency multiplier** so old connections decay.

Aggregation (post-Sprint-2-c1):

  edge_raw  = strongest_edge + 0.10 · second_strongest_edge   (cap 1.0)
  edge_raw *= recency_multiplier(most_recent_connection_year)
  C         = raw_to_4_0(edge_raw)

Recency multiplier:

  gap (current_year − most_recent_connection_year)
    0–2y    → 1.00
    3–5y    → 0.85
    6–10y   → 0.60
    10y+    → 0.35
  None      → 0.75   (agent didn't capture the year)

Calibration shifts vs Sprint-1 (recalibrated to fit the v2 secondary-
bonus + recency aggregation; see Sprint-2-c1 for rationale):

  same_working_group:          0.70 → 0.75
  analysis_contact_overlap:    0.95 → 0.70
  genealogy same_advisor:      1.00 → 0.65
  genealogy uncle_nephew:      0.70 → 0.50
  big_collab_papers_5y cap:    0.40 → 0.10
  small_team_coauthor:         unchanged (min(1.0, n/5))
  collaboration_overlap_years: unchanged
  committee_co_member:         unchanged

A v2 "small_team coauthor 5y" still saturates at 1.0 (the strongest
direct working-relationship signal). Genealogy, big-collab, and
analysis-contact were over-weighted under v1 — under v2 they fit
into a coherent ladder where verified active collaboration tops
out and historical / structural signals contribute below.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.** The recency cutoffs and edge values are educated
> guesses, not load-bearing magnitudes.
"""

from __future__ import annotations

import datetime
from typing import Literal

from phd_matcher.models import FieldProfile, PathEdge

# ---- Field-aware coauthorship classifier (P2) ----------------------------

DEFAULT_BIG_COLLAB_THRESHOLD = 10


def classify_coauthorship(
    author_count: int,
    field_profile: FieldProfile | None = None,
) -> Literal["small_team", "big_collab"]:
    """Bucket a paper by total author count, using the field profile's
    threshold (or 10 as cross-field default).

    Use this when the agent has the per-paper author count and wants to
    deterministically assign it to `small_team_coauthor_5y` vs
    `big_collab_papers_5y` per the active discipline's convention.
    """
    if author_count < 1:
        raise ValueError(f"author_count must be ≥ 1, got {author_count}")
    threshold = (
        field_profile.big_collab_threshold
        if field_profile is not None
        else DEFAULT_BIG_COLLAB_THRESHOLD
    )
    return "big_collab" if author_count > threshold else "small_team"


# ---- v1 + recalibrated edge strengths (each on 0–1) ----------------------

def small_team_coauthor_strength(paper_count_5y: int) -> float:
    """Co-authored papers with ≤threshold authors — the strongest direct
    working-relationship signal in v2 (max 1.0 at n=5+)."""
    return min(1.0, paper_count_5y / 5)


def big_collab_paper_strength(paper_count_5y: int) -> float:
    """v2 recalibration: cap reduced from 0.40 to 0.10. Alphabetical
    author-list overlap alone is a very weak signal; rescue via
    `same_working_group` or `analysis_contact_overlap` for big-collab
    fields (the matcher's max-of-edges aggregation handles this)."""
    return min(0.10, paper_count_5y / 100)


def working_group_strength() -> float:
    """v2: 0.75 (was 0.70). Verified subgroup / convener overlap within
    a larger collaboration — strong evidence of direct working contact
    even when the headline papers are big-collab."""
    return 0.75


def analysis_contact_strength() -> float:
    """v2: 0.70 (was 0.95). Both listed as analysis contacts on a
    specific paper / internal note. Recalibrated so it composes with
    other edges via secondary bonus instead of saturating alone."""
    return 0.70


# v2 genealogy values: same_advisor 0.65 (was 1.0), uncle_nephew 0.50
# (was 0.7), two_hop unchanged at 0.40.
GENEALOGY_RELATIONS: dict[str, float] = {
    "same_advisor":   0.65,
    "uncle_nephew":   0.50,
    "two_hop":        0.40,
}


def genealogy_strength(relation: str) -> float:
    return GENEALOGY_RELATIONS.get(relation, 0.0)


def collaboration_strength(overlap_years: float) -> float:
    """Generic shared-collaboration overlap window (when finer signals
    aren't available). Unchanged from v1."""
    if overlap_years >= 5: return 1.0
    if overlap_years >= 1: return 0.6
    if overlap_years > 0:  return 0.3
    return 0.0


def committee_strength(same_period: bool = False) -> float:
    """Documented editorial board / NSF panel / PC overlap. Unchanged
    from v1. (See `committee_or_exam_overlap_strength` for the v2
    PhD-committee / qualifying-exam variant.)"""
    return 0.8 if same_period else 0.3


# ---- v2 new edge strengths -----------------------------------------------

def shared_grant_strength(grant_count_5y: int) -> float:
    """Shared NSF/NIH/DOE grants in last 5y. v2: max 0.80 at n≥2.
    Strong indicator of active collaboration on funded work."""
    return min(0.80, grant_count_5y * 0.40)


def co_mentored_student_strength(student_count: int) -> float:
    """Students jointly mentored by both advisor and candidate
    (committee co-mentorship counts). v2: max 0.90 at n≥3 — near-direct
    collaboration, just below small_team_coauthor."""
    return min(0.90, student_count * 0.30)


def committee_or_exam_overlap_strength() -> float:
    """PhD committee / qualifying exam overlap. v2: 0.45. Distinct from
    `committee_co_member` (editorial / NSF panel — 0.3 / 0.8) — this
    one is dissertation-committee-level."""
    return 0.45


def same_center_or_institute_strength() -> float:
    """Both members of the same research center / institute (NSF
    Engineering Research Center, NIH center, DOE national lab,
    interdisciplinary institute). v2: 0.40."""
    return 0.40


def prior_institution_overlap_strength(years: int) -> float:
    """Years overlapped at the same institution before either's current
    role (e.g., both at Stanford 2008–2014). v2: max 0.35 at 10+ years."""
    return min(0.35, years / 10)


def conference_session_overlap_strength(count_5y: int) -> float:
    """Conferences in last 5y where both presented at the same session
    or track. v2: max 0.20 at 2+ — weak signal (proximity ≠ working
    relationship), but non-zero (suggests subfield overlap)."""
    return min(0.20, count_5y * 0.10)


# ---- Aggregation: secondary bonus + recency multiplier -------------------

SECONDARY_BONUS_FACTOR = 0.10


def recency_multiplier(
    most_recent_year: int | None,
    *,
    current_year: int | None = None,
) -> float:
    """Map the gap between `most_recent_year` and `current_year` to a
    multiplier. None → 0.60 (the agent didn't capture the year of last
    contact; treated as the 6–10y known-gap level so that omitting the year
    never point-estimates *above* a cited-but-old connection). Future years
    (most_recent_year > current_year) clamp to 1.00 (treat as recent).
    """
    if most_recent_year is None:
        return 0.60
    if current_year is None:
        current_year = datetime.datetime.now().year
    gap = current_year - most_recent_year
    if gap <= 2: return 1.00
    if gap <= 5: return 0.85
    if gap <= 10: return 0.60
    return 0.35


def aggregate_edge_strengths(strengths: list[float]) -> float:
    """v2 aggregation: strongest single edge + 0.10 × second-strongest,
    capped at 1.0. No further stacking — many weak signals must not
    beat one strong verified direct edge.
    """
    if not strengths:
        return 0.0
    sorted_desc = sorted(strengths, reverse=True)
    primary = sorted_desc[0]
    secondary = sorted_desc[1] if len(sorted_desc) >= 2 else 0.0
    return min(1.0, primary + SECONDARY_BONUS_FACTOR * secondary)


# ---- Path strength (v2: aggregation + recency) ---------------------------

def path_strength(
    edges: PathEdge | dict,
    *,
    current_year: int | None = None,
) -> float:
    """v2 path strength: strongest single edge + small secondary bonus,
    capped at 1.0, scaled by `recency_multiplier`. Accepts PathEdge or
    dict; dicts are validated via PathEdge construction (which forbids
    unknown keys per the strict schema).
    """
    if isinstance(edges, dict):
        edges = PathEdge.model_validate(edges)

    strengths: list[float] = []

    # ---- v1 edges --------------------------------------------------------
    if edges.small_team_coauthor_5y is not None:
        strengths.append(small_team_coauthor_strength(edges.small_team_coauthor_5y))

    if edges.big_collab_papers_5y is not None:
        strengths.append(big_collab_paper_strength(edges.big_collab_papers_5y))

    if edges.same_working_group:
        strengths.append(working_group_strength())

    if edges.analysis_contact_overlap:
        strengths.append(analysis_contact_strength())

    if edges.genealogy_relation is not None:
        strengths.append(genealogy_strength(edges.genealogy_relation))

    if edges.collaboration_overlap_years is not None:
        strengths.append(collaboration_strength(edges.collaboration_overlap_years))

    if edges.committee_co_member:
        strengths.append(committee_strength(edges.same_period))

    # ---- v2 edges --------------------------------------------------------
    if edges.shared_grant_count_5y is not None:
        strengths.append(shared_grant_strength(edges.shared_grant_count_5y))

    if edges.co_mentored_student_count is not None:
        strengths.append(co_mentored_student_strength(edges.co_mentored_student_count))

    if edges.committee_or_exam_overlap:
        strengths.append(committee_or_exam_overlap_strength())

    if edges.same_center_or_institute:
        strengths.append(same_center_or_institute_strength())

    if edges.prior_institution_overlap_years is not None:
        strengths.append(
            prior_institution_overlap_strength(edges.prior_institution_overlap_years)
        )

    if edges.conference_session_overlap_5y is not None:
        strengths.append(
            conference_session_overlap_strength(edges.conference_session_overlap_5y)
        )

    raw = aggregate_edge_strengths(strengths)
    return raw * recency_multiplier(
        edges.most_recent_connection_year, current_year=current_year,
    )


# ---- Final composite + 4.0 mapping ---------------------------------------

def raw_to_4_0(raw: float) -> float:
    if raw >= 0.8: return 4.0
    if raw >= 0.6: return 3.7
    if raw >= 0.4: return 3.3
    if raw >= 0.2: return 2.8
    return 2.3


def connection_score(
    student_advisors: list[dict],
    candidate: dict,
    *,
    current_year: int | None = None,
) -> float:
    """Path-based connection score on the 4.0 scale (post-Sprint-2-c1
    Connection v2).

    Roadmap #3 split: this used to mix path strength with the candidate's
    own network signals (`normalized_collab_top20pct`, `collab_with_nas`,
    `grad_placement_quality`) — but those describe the PI's own standing,
    not the connection to the student's advisor. Now they live in the A
    dimension (`scoring.advisor.advisor_strength`).

    Sprint-2-c1: edges go through v2 aggregation (strongest + 0.10·second,
    cap 1.0, then recency multiplier) and the new edge types (shared
    grants, co-mentored students, committee/exam overlap, etc.) are
    folded into the same path_strength formula.

    No advisor → C = bucketed-from-0 = 2.3 (lowest bucket). The student
    profile honestly has no path-style signal to evaluate; the candidate's
    intrinsic strength is captured in A separately.
    """
    if not student_advisors:
        return raw_to_4_0(0.0)

    paths = candidate.get("paths_to_advisors", {})
    path_strengths: list[float] = []
    for adv in student_advisors:
        adv_id = adv.get("id")
        if adv_id and adv_id in paths:
            path_strengths.append(
                path_strength(paths[adv_id], current_year=current_year)
            )

    c_path = max(path_strengths) if path_strengths else 0.0
    return raw_to_4_0(c_path)
