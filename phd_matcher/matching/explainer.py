"""Template-based match explanation. Surfaces sources from edges + evidence."""

from phd_matcher.models import CandidateAdvisor, StudentProfile

_GENEALOGY_LABEL = {
    "same_advisor": "academic siblings (same PhD advisor)",
    "uncle_nephew": "advisor's PhD sibling / 师叔关系",
    "two_hop":      "two-hop genealogy connection",
}


def _src_suffix(d: dict | None) -> str:
    """Render up to 2 source URLs from a dict-like with a 'sources' list."""
    if not d:
        return ""
    sources = d.get("sources") if isinstance(d, dict) else getattr(d, "sources", None)
    if not sources:
        return ""
    shown = [str(s) for s in sources[:2]]
    return f" [{'; '.join(shown)}]"


def explain_match(student: StudentProfile, candidate: CandidateAdvisor) -> str:
    parts: list[str] = []

    # Connection paths to student's current advisors
    if candidate.paths_to_advisors:
        for adv_id, edges in candidate.paths_to_advisors.items():
            adv_name = next(
                (a.name for a in student.current_advisors if a.id == adv_id),
                "your advisor",
            )

            sfx = _src_suffix(edges)

            if "small_team_coauthor_5y" in edges:
                n = edges["small_team_coauthor_5y"]
                parts.append(
                    f"co-authored {n} small-team paper(s) with {adv_name} in last 5y{sfx}"
                )
            elif "coauthor_papers_5y" in edges:
                # Legacy field name
                n = edges["coauthor_papers_5y"]
                parts.append(
                    f"co-authored {n} paper(s) with {adv_name} in last 5y{sfx}"
                )

            if "big_collab_papers_5y" in edges:
                n = edges["big_collab_papers_5y"]
                parts.append(
                    f"shared {n} big-collab paper(s) with {adv_name} "
                    f"(alphabetical author list){sfx}"
                )

            if edges.get("same_working_group"):
                parts.append(f"same working group / convener overlap with {adv_name}{sfx}")

            if edges.get("analysis_contact_overlap"):
                parts.append(f"shared analysis-contact role with {adv_name}{sfx}")

            if "genealogy_relation" in edges:
                rel = _GENEALOGY_LABEL.get(
                    edges["genealogy_relation"], edges["genealogy_relation"]
                )
                parts.append(f"{rel} with {adv_name}{sfx}")

            if "collaboration_overlap_years" in edges:
                yrs = edges["collaboration_overlap_years"]
                parts.append(
                    f"shared collaboration membership with {adv_name} for ~{yrs:.0f} years{sfx}"
                )

            if edges.get("committee_co_member"):
                parts.append(f"editorial / committee co-membership with {adv_name}{sfx}")

    # Research areas
    if candidate.research_areas:
        parts.append("research: " + ", ".join(candidate.research_areas[:3]))

    # Field-level signals — surface NAS evidence if present
    if candidate.collab_with_nas:
        nas_entry = candidate.evidence.get("collab_with_nas") if candidate.evidence else None
        nas_sfx = ""
        if nas_entry:
            srcs = (
                getattr(nas_entry, "sources", None)
                if not isinstance(nas_entry, dict)
                else nas_entry.get("sources")
            )
            if srcs:
                nas_sfx = f" [{srcs[0]}]"
        parts.append(f"collaborates with NAS / HHMI member(s){nas_sfx}")

    if not parts:
        return (
            "No connection signals found via search; ranking driven by candidate's "
            "field-level network strength only."
        )

    return " · ".join(parts)
