"""End-to-end match pipeline + ranker."""

from phd_matcher.matching.direction import direction_relevance
from phd_matcher.matching.explainer import explain_match
from phd_matcher.models import CandidateAdvisor, MatchResult, StudentProfile
from phd_matcher.scoring import admit, connection, experience, gpa, pub

# Field-strength signals that carry their own EvidenceEntry — count as
# "unverified" if at default value without sources.
_FIELD_STRENGTH_SIGNALS = (
    "normalized_collab_top20pct",
    "collab_with_nas",
    "grad_placement_quality",
)


def _signal_is_at_default(candidate: CandidateAdvisor, field: str) -> bool:
    val = getattr(candidate, field)
    if field == "normalized_collab_top20pct":
        return val == 0.0
    if field == "collab_with_nas":
        return val is False
    if field == "grad_placement_quality":
        return val == 0.0
    return False


def _signal_has_sources(candidate: CandidateAdvisor, field: str) -> bool:
    entry = candidate.evidence.get(field) if candidate.evidence else None
    if not entry:
        return False
    sources = getattr(entry, "sources", None)
    if sources is None and isinstance(entry, dict):
        sources = entry.get("sources")
    return bool(sources)


def count_unverified_signals(
    student: StudentProfile, candidate: CandidateAdvisor
) -> int:
    """Count signals that are missing OR at default values without source
    citations. Drives confidence_band — see admit.confidence_band_from_unverified."""
    n = 0

    # Connection paths to advisors
    if student.current_advisors:
        for adv in student.current_advisors:
            edges = candidate.paths_to_advisors.get(adv.id) or {}
            if not edges:
                n += 1                       # no edge found at all
            elif not edges.get("sources"):
                n += 1                       # claimed edges without source URLs

    # Field-strength signals — unverified if default value AND no sources
    for sig in _FIELD_STRENGTH_SIGNALS:
        if _signal_is_at_default(candidate, sig) and not _signal_has_sources(candidate, sig):
            n += 1

    # PI signal
    if candidate.pi_signal == "missing":
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
