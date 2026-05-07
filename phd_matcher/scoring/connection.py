"""Connection score (C) — per Scoring Design v0.3, with big-collab fix
and strict PathEdge schema (post-review #5 + edge refactor).

Co-authorship is differentiated:
  - small_team_coauthor_5y (papers with ≤threshold authors) — strong working signal
  - big_collab_papers_5y (papers with >threshold authors) — alphabetical author bulk;
    significantly discounted

The `threshold` is field-specific via `FieldProfile.big_collab_threshold`
(physics 10, mse/cs 8, biology/chemistry 6, math 4). Use
`classify_coauthorship()` as a deterministic helper.
"""

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

# ---- Edge strengths (each on 0–1) ----------------------------------------

def small_team_coauthor_strength(paper_count_5y: int) -> float:
    """Co-authored papers with ≤10 authors — strong working-relationship signal."""
    return min(1.0, paper_count_5y / 5)


def big_collab_paper_strength(paper_count_5y: int) -> float:
    """Co-membership in a big collab (e.g., ATLAS / CMS / LIGO) where both
    names appear in an alphabetical 11+-author list. Doesn't imply the PIs
    know each other; capped low."""
    return min(0.4, paper_count_5y / 25)


def working_group_strength() -> float:
    """Both verifiably members of the same subgroup / convener / analysis
    team within a larger collaboration."""
    return 0.7


def analysis_contact_strength() -> float:
    """Both listed as analysis contacts on a specific paper / note —
    strongest evidence of direct working relationship in big-collab fields."""
    return 0.95


GENEALOGY_RELATIONS: dict[str, float] = {
    "same_advisor":   1.0,
    "uncle_nephew":   0.7,
    "two_hop":        0.4,
}


def genealogy_strength(relation: str) -> float:
    return GENEALOGY_RELATIONS.get(relation, 0.0)


def collaboration_strength(overlap_years: float) -> float:
    """Generic shared-collaboration overlap window (when finer signals
    aren't available)."""
    if overlap_years >= 5: return 1.0
    if overlap_years >= 1: return 0.6
    if overlap_years > 0:  return 0.3
    return 0.0


def committee_strength(same_period: bool = False) -> float:
    return 0.8 if same_period else 0.3


# ---- Path strength (max over edge types — no stacking) -------------------

def path_strength(edges: PathEdge | dict) -> float:
    """Max of all edge-type strengths between one student-advisor and the
    candidate. Accepts PathEdge or dict; dicts are validated via PathEdge
    construction (which forbids unknown keys per the strict schema)."""
    if isinstance(edges, dict):
        edges = PathEdge.model_validate(edges)

    strengths: list[float] = []

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

    return max(strengths) if strengths else 0.0


# ---- Field strength (candidate's own network) ----------------------------

def field_strength(candidate: dict) -> float:
    """Compute candidate's field-level network signal on 0–1.

    Three-state semantics per code review: each input field can be `None`
    (not checked), a verified value (with sources), or False/0 (verified
    weak). For scoring, `None` contributes 0 (conservative — pushes the
    agent to actually verify rather than guess a neutral default)."""
    collab_top20_raw = candidate.get("normalized_collab_top20pct")
    collab_top20 = 0.0 if collab_top20_raw is None else float(collab_top20_raw)

    nas = 1.0 if candidate.get("collab_with_nas") is True else 0.0

    placement_raw = candidate.get("grad_placement_quality")
    placement = 0.0 if placement_raw is None else float(placement_raw)

    return 0.4 * collab_top20 + 0.3 * nas + 0.3 * placement


# ---- Final composite + 4.0 mapping ---------------------------------------

def raw_to_4_0(raw: float) -> float:
    if raw >= 0.8: return 4.0
    if raw >= 0.6: return 3.7
    if raw >= 0.4: return 3.3
    if raw >= 0.2: return 2.8
    return 2.3


def connection_score(student_advisors: list[dict], candidate: dict) -> float:
    paths = candidate.get("paths_to_advisors", {})

    if not student_advisors:
        return raw_to_4_0(field_strength(candidate))

    path_strengths: list[float] = []
    for adv in student_advisors:
        adv_id = adv.get("id")
        if adv_id and adv_id in paths:
            path_strengths.append(path_strength(paths[adv_id]))

    c_path = max(path_strengths) if path_strengths else 0.0
    c_field = field_strength(candidate)
    c_raw = 0.6 * c_path + 0.4 * c_field
    return raw_to_4_0(c_raw)
