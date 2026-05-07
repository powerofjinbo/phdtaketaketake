"""Match explanation. Surfaces evidence coverage with **per-claim** source
attribution — each rendered claim cites only the URLs whose
`supports_fields` includes that claim's field name.

This is the fourth-pass-review fix: previously `_src_suffix(edge)` rendered
the first 2 URLs from `edge.items` for every claim, which conflated edges.
Now each claim only shows its own supporting evidence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from phd_matcher.models import CandidateAdvisor, EvidenceEntry, PathEdge, StudentProfile

if TYPE_CHECKING:
    from phd_matcher.matching.ranker import EvidenceCoverage


_GENEALOGY_LABEL = {
    "same_advisor": "academic siblings (same PhD advisor)",
    "uncle_nephew": "advisor's PhD sibling / 师叔关系",
    "two_hop":      "two-hop genealogy connection",
}


def _items_for_field(items_list, field_name: str):
    return [it for it in items_list if field_name in it.supports_fields]


def _render_items(items_list) -> str:
    if not items_list:
        return ""
    shown = [f"{it.url} · {it.source_type}" for it in items_list[:2]]
    return f" [{'; '.join(shown)}]"


def _src_suffix_for_path_field(edge: PathEdge, field_name: str) -> str:
    """Render up to 2 URLs from `edge.items` whose `supports_fields` includes
    the field. Falls back to the legacy bare `sources` list (default mode
    only) if no structured items match."""
    relevant = _items_for_field(edge.items, field_name)
    if relevant:
        return _render_items(relevant)
    if edge.sources:
        shown = [str(s) for s in edge.sources[:2]]
        return f" [{'; '.join(shown)} (legacy bare URL)]"
    return ""


def _src_suffix_for_entry(entry: EvidenceEntry | None, field_name: str) -> str:
    if entry is None:
        return ""
    relevant = _items_for_field(entry.items, field_name)
    if relevant:
        return _render_items(relevant)
    if entry.sources:
        shown = [str(s) for s in entry.sources[:1]]
        return f" [{shown[0]} (legacy bare URL)]"
    return ""


def _evidence_summary_line(cov: EvidenceCoverage) -> str:
    """One-line audit: '7/7 verified' or '4/7 verified · 1 missing · 2 unsourced'."""
    if cov.unverified == 0:
        return f"Evidence coverage: {cov.verified}/{cov.total} signals verified ✓"
    parts = [f"{cov.verified}/{cov.total} verified"]
    if cov.missing:
        parts.append(f"{cov.missing} missing ({', '.join(cov.missing_names[:3])})")
    if cov.unsourced:
        parts.append(
            f"{cov.unsourced} unsourced ({', '.join(cov.unsourced_names[:3])})"
        )
    return "Evidence coverage: " + " · ".join(parts)


def explain_match(
    student: StudentProfile,
    candidate: CandidateAdvisor,
    coverage: EvidenceCoverage | None = None,
) -> str:
    """Render the match explanation. Each claim cites only the URLs whose
    `supports_fields` lists the claim's field — so a Math Genealogy URL
    can't get pasted onto a co-authorship claim by accident."""
    parts: list[str] = []

    # Top: evidence coverage line
    if coverage is not None:
        parts.append(_evidence_summary_line(coverage))

    # Connection paths to student's current advisors
    if candidate.paths_to_advisors:
        for adv_id, edge in candidate.paths_to_advisors.items():
            adv_name = next(
                (a.name for a in student.current_advisors if a.id == adv_id),
                "your advisor",
            )

            if edge.small_team_coauthor_5y is not None:
                n = edge.small_team_coauthor_5y
                sfx = _src_suffix_for_path_field(edge, "small_team_coauthor_5y")
                parts.append(
                    f"co-authored {n} small-team paper(s) with {adv_name} in last 5y{sfx}"
                )

            if edge.big_collab_papers_5y is not None:
                n = edge.big_collab_papers_5y
                sfx = _src_suffix_for_path_field(edge, "big_collab_papers_5y")
                parts.append(
                    f"shared {n} big-collab paper(s) with {adv_name} "
                    f"(alphabetical author list){sfx}"
                )

            if edge.same_working_group:
                sfx = _src_suffix_for_path_field(edge, "same_working_group")
                parts.append(
                    f"same working group / convener overlap with {adv_name}{sfx}"
                )

            if edge.analysis_contact_overlap:
                sfx = _src_suffix_for_path_field(edge, "analysis_contact_overlap")
                parts.append(
                    f"shared analysis-contact role with {adv_name}{sfx}"
                )

            if edge.genealogy_relation is not None:
                rel = _GENEALOGY_LABEL.get(
                    edge.genealogy_relation, edge.genealogy_relation
                )
                sfx = _src_suffix_for_path_field(edge, "genealogy_relation")
                parts.append(f"{rel} with {adv_name}{sfx}")

            if edge.collaboration_overlap_years is not None:
                yrs = edge.collaboration_overlap_years
                sfx = _src_suffix_for_path_field(edge, "collaboration_overlap_years")
                parts.append(
                    f"shared collaboration membership with {adv_name} "
                    f"for ~{yrs:.0f} years{sfx}"
                )

            if edge.committee_co_member:
                sfx = _src_suffix_for_path_field(edge, "committee_co_member")
                parts.append(
                    f"editorial / committee co-membership with {adv_name}{sfx}"
                )

    # Research areas — cite per-claim
    if candidate.research_areas:
        ra_entry = candidate.evidence.get("research_areas") if candidate.evidence else None
        sfx = _src_suffix_for_entry(ra_entry, "research_areas")
        parts.append("research: " + ", ".join(candidate.research_areas[:3]) + sfx)

    # NAS signal — cite per-claim
    if candidate.collab_with_nas is True:
        nas_entry = candidate.evidence.get("collab_with_nas") if candidate.evidence else None
        sfx = _src_suffix_for_entry(nas_entry, "collab_with_nas")
        parts.append(f"collaborates with NAS / HHMI member(s){sfx}")

    if not parts or (len(parts) == 1 and parts[0].startswith("Evidence coverage")):
        if not candidate.paths_to_advisors and candidate.research_areas:
            return _evidence_summary_line(coverage) if coverage else (
                "No connection signals found via search; ranking driven by "
                "candidate's field-level network strength only."
            )

    return " · ".join(parts)
