"""Connection score (C) — per Scoring Design v0.3 §5, with big-collab fix.

Co-authorship is now differentiated:
  - small_team_coauthor_5y (papers with ≤10 authors) — strong signal of
    actual working relationship
  - big_collab_papers_5y (papers with >10 authors) — alphabetical author
    list bulk; same membership but doesn't imply the PIs know each other.
    Significantly discounted.

Per the cardinal rule, every edge an agent records should be backed by
sources in the edges["sources"] list — but the scoring math only sees
the values.
"""

# ---- Edge strengths (each on 0–1) ----------------------------------------

def small_team_coauthor_strength(paper_count_5y: int) -> float:
    """Co-authored papers with ≤10 authors — strong working-relationship signal."""
    return min(1.0, paper_count_5y / 5)


def big_collab_paper_strength(paper_count_5y: int) -> float:
    """Co-membership in a big collab (e.g., ATLAS / CMS / LIGO) where both
    names appear in an alphabetical author list of 11+ people. Doesn't imply
    the PIs know each other; capped low."""
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
    """Generic shared-collaboration overlap window (when small_team_coauthor /
    working_group / analysis_contact data isn't available)."""
    if overlap_years >= 5: return 1.0
    if overlap_years >= 1: return 0.6
    if overlap_years > 0:  return 0.3
    return 0.0


def committee_strength(same_period: bool = False) -> float:
    return 0.8 if same_period else 0.3


# ---- Path strength (max over edge types — no stacking) -------------------

def path_strength(edges: dict) -> float:
    """Max of all edge-type strengths between one student-advisor and the
    candidate. Edges is a dict that may include any subset of:
      - small_team_coauthor_5y       (int, preferred)
      - big_collab_papers_5y         (int)
      - same_working_group           (bool)
      - analysis_contact_overlap     (bool)
      - genealogy_relation           (str)
      - collaboration_overlap_years  (float)
      - committee_co_member          (bool), same_period (bool)
      - sources                      (list[str], not used in scoring but
                                      required by data-integrity policy)
      - note                         (str, freeform)

    Backward compat: also accepts legacy `coauthor_papers_5y` (treated as
    small_team_coauthor_5y).
    """
    strengths: list[float] = []

    if "small_team_coauthor_5y" in edges:
        strengths.append(small_team_coauthor_strength(int(edges["small_team_coauthor_5y"])))
    elif "coauthor_papers_5y" in edges:  # legacy name
        strengths.append(small_team_coauthor_strength(int(edges["coauthor_papers_5y"])))

    if "big_collab_papers_5y" in edges:
        strengths.append(big_collab_paper_strength(int(edges["big_collab_papers_5y"])))

    if edges.get("same_working_group"):
        strengths.append(working_group_strength())

    if edges.get("analysis_contact_overlap"):
        strengths.append(analysis_contact_strength())

    if "genealogy_relation" in edges:
        strengths.append(genealogy_strength(str(edges["genealogy_relation"])))

    if "collaboration_overlap_years" in edges:
        strengths.append(collaboration_strength(float(edges["collaboration_overlap_years"])))

    if edges.get("committee_co_member"):
        strengths.append(committee_strength(bool(edges.get("same_period", False))))

    return max(strengths) if strengths else 0.0


# ---- Field strength (candidate's own network) ----------------------------

def field_strength(candidate: dict) -> float:
    collab_top20 = float(candidate.get("normalized_collab_top20pct", 0.0))
    nas = 1.0 if candidate.get("collab_with_nas") else 0.0
    placement = float(candidate.get("grad_placement_quality", 0.0))
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
