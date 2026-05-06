"""Template-based match explanation. LLM upgrade is optional / future work."""

from phd_matcher.models import CandidateAdvisor, StudentProfile


_GENEALOGY_LABEL = {
    "same_advisor": "academic siblings (same PhD advisor)",
    "uncle_nephew": "advisor's PhD sibling / 师叔关系",
    "two_hop":      "two-hop genealogy connection",
}


def explain_match(student: StudentProfile, candidate: CandidateAdvisor) -> str:
    parts: list[str] = []

    # Connection paths to student's current advisors
    if candidate.paths_to_advisors:
        for adv_id, edges in candidate.paths_to_advisors.items():
            adv_name = next(
                (a.name for a in student.current_advisors if a.id == adv_id),
                "your advisor",
            )

            if "coauthor_papers_5y" in edges:
                n = edges["coauthor_papers_5y"]
                parts.append(f"co-authored {n} paper(s) with {adv_name} in last 5 years")

            if "genealogy_relation" in edges:
                rel = _GENEALOGY_LABEL.get(
                    edges["genealogy_relation"], edges["genealogy_relation"]
                )
                parts.append(f"{rel} with {adv_name}")

            if "collaboration_overlap_years" in edges:
                yrs = edges["collaboration_overlap_years"]
                parts.append(
                    f"shared collaboration membership with {adv_name} for ~{yrs:.0f} years"
                )

            if edges.get("committee_co_member"):
                parts.append(f"editorial / committee co-membership with {adv_name}")

    # Research areas
    if candidate.research_areas:
        parts.append("research: " + ", ".join(candidate.research_areas[:3]))

    # Field-level signals
    if candidate.collab_with_nas:
        parts.append("collaborates with NAS / HHMI member(s)")

    if not parts:
        return "No direct connection signals; ranking driven by candidate's field-level network strength."

    return " · ".join(parts)
