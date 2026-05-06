"""Connection score (C) — per Scoring Design v0.3 §5.

Computed per (student, candidate_advisor) pair. The scoring IP of this project.
"""


# ---- Edge strengths (each on 0–1) ----------------------------------------

def coauthor_strength(paper_count_5y: int) -> float:
    """Co-author edge: papers in last 5 years between student-advisor and candidate."""
    return min(1.0, paper_count_5y / 5)


GENEALOGY_RELATIONS: dict[str, float] = {
    "same_advisor":   1.0,    # academic siblings (same PhD advisor)
    "uncle_nephew":   0.7,    # candidate is advisor's PhD sibling, etc.
    "two_hop":        0.4,    # any 2-hop genealogy relation
}


def genealogy_strength(relation: str) -> float:
    return GENEALOGY_RELATIONS.get(relation, 0.0)


def collaboration_strength(overlap_years: float) -> float:
    """Common large-collab membership (e.g., ATLAS/CMS) overlap window."""
    if overlap_years >= 5: return 1.0
    if overlap_years >= 1: return 0.6
    if overlap_years > 0:  return 0.3
    return 0.0


def committee_strength(same_period: bool = False) -> float:
    """Editorial board / NSF panel / PC co-membership."""
    return 0.8 if same_period else 0.3


# ---- Path strength (max over edge types — no stacking) -------------------

def path_strength(edges: dict) -> float:
    """Max of all edge-type strengths between one student-advisor and the candidate.

    edges may include any subset of:
      - coauthor_papers_5y: int
      - genealogy_relation: str
      - collaboration_overlap_years: float
      - committee_co_member: bool, same_period: bool (optional)
    """
    strengths: list[float] = []

    if "coauthor_papers_5y" in edges:
        strengths.append(coauthor_strength(int(edges["coauthor_papers_5y"])))
    if "genealogy_relation" in edges:
        strengths.append(genealogy_strength(str(edges["genealogy_relation"])))
    if "collaboration_overlap_years" in edges:
        strengths.append(collaboration_strength(float(edges["collaboration_overlap_years"])))
    if edges.get("committee_co_member"):
        strengths.append(committee_strength(bool(edges.get("same_period", False))))

    return max(strengths) if strengths else 0.0


# ---- Field strength (candidate's own network) ----------------------------

def field_strength(candidate: dict) -> float:
    """Candidate's own academic network strength (independent of student) on 0–1."""
    collab_top20 = float(candidate.get("normalized_collab_top20pct", 0.0))
    nas = 1.0 if candidate.get("collab_with_nas") else 0.0
    placement = float(candidate.get("grad_placement_quality", 0.0))
    return 0.4 * collab_top20 + 0.3 * nas + 0.3 * placement


# ---- Final composite + 4.0 mapping ---------------------------------------

def raw_to_4_0(raw: float) -> float:
    """0–1 raw → 4.0 mapping per v0.3 §5.6."""
    if raw >= 0.8: return 4.0
    if raw >= 0.6: return 3.7
    if raw >= 0.4: return 3.3
    if raw >= 0.2: return 2.8
    return 2.3


def connection_score(student_advisors: list[dict], candidate: dict) -> float:
    """Compute Connection Score (4.0).

    student_advisors: list of {"id": str, "name": str, ...}
    candidate: dict with paths_to_advisors {advisor_id: edges} and field-level signals
    """
    paths = candidate.get("paths_to_advisors", {})

    if not student_advisors:
        # No current advisor → only candidate's own field strength
        return raw_to_4_0(field_strength(candidate))

    # Path strength: max over all student advisors
    path_strengths: list[float] = []
    for adv in student_advisors:
        adv_id = adv.get("id")
        if adv_id and adv_id in paths:
            path_strengths.append(path_strength(paths[adv_id]))

    c_path = max(path_strengths) if path_strengths else 0.0
    c_field = field_strength(candidate)
    c_raw = 0.6 * c_path + 0.4 * c_field
    return raw_to_4_0(c_raw)
