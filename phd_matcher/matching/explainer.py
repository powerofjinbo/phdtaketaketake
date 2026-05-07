"""Template-based match explanation. Surfaces sources from PathEdge + evidence."""

from phd_matcher.models import CandidateAdvisor, PathEdge, StudentProfile

_GENEALOGY_LABEL = {
    "same_advisor": "academic siblings (same PhD advisor)",
    "uncle_nephew": "advisor's PhD sibling / 师叔关系",
    "two_hop":      "two-hop genealogy connection",
}


def _src_suffix(edge: PathEdge) -> str:
    """Render up to 2 source URLs from a PathEdge."""
    if not edge.sources:
        return ""
    shown = [str(s) for s in edge.sources[:2]]
    return f" [{'; '.join(shown)}]"


def explain_match(student: StudentProfile, candidate: CandidateAdvisor) -> str:
    parts: list[str] = []

    # Connection paths to student's current advisors
    if candidate.paths_to_advisors:
        for adv_id, edge in candidate.paths_to_advisors.items():
            adv_name = next(
                (a.name for a in student.current_advisors if a.id == adv_id),
                "your advisor",
            )

            sfx = _src_suffix(edge)

            if edge.small_team_coauthor_5y is not None:
                n = edge.small_team_coauthor_5y
                parts.append(
                    f"co-authored {n} small-team paper(s) with {adv_name} in last 5y{sfx}"
                )

            if edge.big_collab_papers_5y is not None:
                n = edge.big_collab_papers_5y
                parts.append(
                    f"shared {n} big-collab paper(s) with {adv_name} "
                    f"(alphabetical author list){sfx}"
                )

            if edge.same_working_group:
                parts.append(
                    f"same working group / convener overlap with {adv_name}{sfx}"
                )

            if edge.analysis_contact_overlap:
                parts.append(
                    f"shared analysis-contact role with {adv_name}{sfx}"
                )

            if edge.genealogy_relation is not None:
                rel = _GENEALOGY_LABEL.get(
                    edge.genealogy_relation, edge.genealogy_relation
                )
                parts.append(f"{rel} with {adv_name}{sfx}")

            if edge.collaboration_overlap_years is not None:
                yrs = edge.collaboration_overlap_years
                parts.append(
                    f"shared collaboration membership with {adv_name} "
                    f"for ~{yrs:.0f} years{sfx}"
                )

            if edge.committee_co_member:
                parts.append(
                    f"editorial / committee co-membership with {adv_name}{sfx}"
                )

    # Research areas
    if candidate.research_areas:
        parts.append("research: " + ", ".join(candidate.research_areas[:3]))

    # Field-level signals — surface NAS evidence if present
    if candidate.collab_with_nas:
        nas_entry = candidate.evidence.get("collab_with_nas") if candidate.evidence else None
        nas_sfx = ""
        if nas_entry and nas_entry.sources:
            nas_sfx = f" [{nas_entry.sources[0]}]"
        parts.append(f"collaborates with NAS / HHMI member(s){nas_sfx}")

    if not parts:
        return (
            "No connection signals found via search; ranking driven by candidate's "
            "field-level network strength only."
        )

    return " · ".join(parts)
