"""Match explanation. Surfaces evidence coverage, source citations,
and the conservative lower bound — so a result card's text reflects the
strength of the claims, not just the numbers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from phd_matcher.models import CandidateAdvisor, PathEdge, StudentProfile

if TYPE_CHECKING:
    from phd_matcher.matching.ranker import EvidenceCoverage


_GENEALOGY_LABEL = {
    "same_advisor": "academic siblings (same PhD advisor)",
    "uncle_nephew": "advisor's PhD sibling / 师叔关系",
    "two_hop":      "two-hop genealogy connection",
}


def _src_suffix(edge: PathEdge) -> str:
    """Render up to 2 source URLs from a PathEdge.

    Prefers structured `items` (rendered as URL · claim), falls back to
    the legacy `sources` list of bare URLs.
    """
    if edge.items:
        shown = []
        for it in edge.items[:2]:
            shown.append(f"{it.url} · {it.source_type}")
        return f" [{'; '.join(shown)}]"
    if edge.sources:
        shown = [str(s) for s in edge.sources[:2]]
        return f" [{'; '.join(shown)}]"
    return ""


def _evidence_summary_line(cov: EvidenceCoverage) -> str:
    """One-line audit: '6/6 verified' or '4/6 verified (1 missing, 1 unsourced)'."""
    if cov.unverified == 0:
        return f"Evidence coverage: {cov.verified}/{cov.total} signals verified ✓"
    parts = [f"{cov.verified}/{cov.total} signals verified"]
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
    """Render the match explanation. Includes:

      - one evidence-coverage summary line at the top
      - per-edge connection narrative with cited sources
      - research areas
      - NAS signal with source if present
    """
    parts: list[str] = []

    # Top: evidence coverage line (so "why is the band wide" is upfront)
    if coverage is not None:
        parts.append(_evidence_summary_line(coverage))

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

    # NAS signal — surface the source URL when verified
    if candidate.collab_with_nas is True:
        nas_entry = candidate.evidence.get("collab_with_nas") if candidate.evidence else None
        nas_sfx = ""
        if nas_entry:
            if nas_entry.items:
                nas_sfx = f" [{nas_entry.items[0].url}]"
            elif nas_entry.sources:
                nas_sfx = f" [{nas_entry.sources[0]}]"
        parts.append(f"collaborates with NAS / HHMI member(s){nas_sfx}")

    if not parts or (len(parts) == 1 and parts[0].startswith("Evidence coverage")):
        # No connection signals; just coverage line + research areas if any
        if not candidate.paths_to_advisors and candidate.research_areas:
            return _evidence_summary_line(coverage) if coverage else (
                "No connection signals found via search; ranking driven by "
                "candidate's field-level network strength only."
            )

    return " · ".join(parts)
