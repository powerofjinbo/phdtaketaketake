"""End-to-end match pipeline + ranker."""

from phd_matcher.matching.direction import direction_relevance
from phd_matcher.matching.explainer import explain_match
from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    MatchResult,
    StudentProfile,
)
from phd_matcher.scoring import admit, connection, experience, gpa, pub

# Field-strength signals that should each have an EvidenceEntry with sources.
_FIELD_STRENGTH_SIGNALS = (
    "normalized_collab_top20pct",
    "collab_with_nas",
    "grad_placement_quality",
)


def _has_sources(entry: EvidenceEntry | None) -> bool:
    if entry is None:
        return False
    return bool(entry.sources)


def count_unverified_signals(
    student: StudentProfile, candidate: CandidateAdvisor
) -> int:
    """Count signals that lack source citations (per code-review #1).

    Strict rule: every claim — even a default value or "missing" — must have
    EvidenceEntry.sources to count as verified. Asserting non-default values
    without sources also counts as unverified.

    Counted:
      - paths_to_advisors[adv.id] missing entirely or PathEdge with empty sources
      - field-strength signals (normalized_collab_top20pct, collab_with_nas,
        grad_placement_quality) without an EvidenceEntry that has sources
      - pi_signal == "missing" (data point absent regardless)
      - pi_signal != "missing" without an EvidenceEntry that has sources
    """
    n = 0

    # Connection paths to each advisor
    if student.current_advisors:
        for adv in student.current_advisors:
            edges = candidate.paths_to_advisors.get(adv.id)
            if edges is None:
                n += 1                              # no path entry at all
            elif not edges.sources:
                n += 1                              # path entry without sources

    # Field-strength signals (each must have evidence sources)
    evidence = candidate.evidence or {}
    for sig in _FIELD_STRENGTH_SIGNALS:
        if not _has_sources(evidence.get(sig)):
            n += 1

    # PI signal — both "missing" and unsourced non-missing count
    if candidate.pi_signal == "missing":
        n += 1
    elif not _has_sources(evidence.get("pi_signal")):
        n += 1

    return n


def compute_match(student: StudentProfile, candidate: CandidateAdvisor) -> MatchResult:
    """Score one (student, candidate) pair across all dimensions."""
    p = pub.pub_score([pp.model_dump() for pp in student.papers])
    g = gpa.gpa_score(student.gpa_raw, student.gpa_scale)
    e = experience.experience_score([ee.model_dump() for ee in student.experiences])
    c = connection.connection_score(
        [a.model_dump() for a in student.current_advisors],
        candidate.model_dump(),
    )

    m = admit.match_score(c, p, e, g, candidate.school_tier)

    unverified = count_unverified_signals(student, candidate)

    strength, band = admit.application_strength(
        m, candidate.school_tier, candidate.pi_signal, unverified_count=unverified
    )
    label = admit.strength_label(strength)

    explanation = explain_match(student, candidate)

    return MatchResult(
        candidate=candidate,
        c_score=round(c, 2),
        p_score=round(p, 2),
        e_score=round(e, 2),
        g_score=round(g, 2),
        match_score=round(m, 2),
        application_strength=round(strength, 2),
        confidence_band=round(band, 2),
        strength_label=label,
        explanation=explanation,
        unverified_signals=unverified,
    )


def rank_advisors(
    student: StudentProfile,
    candidates: list[CandidateAdvisor],
    top_k: int = 20,
    field_filter: bool = True,
) -> list[MatchResult]:
    if field_filter:
        candidates = [c for c in candidates if c.field == student.field]

    results = [compute_match(student, c) for c in candidates]

    def sort_key(r: MatchResult):
        rel = direction_relevance(student.research_direction, r.candidate.research_areas)
        return (r.application_strength, rel, r.match_score)

    results.sort(key=sort_key, reverse=True)
    return results[:top_k]
