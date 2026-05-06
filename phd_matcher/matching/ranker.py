"""End-to-end match pipeline + ranker."""

from phd_matcher.matching.direction import direction_relevance
from phd_matcher.matching.explainer import explain_match
from phd_matcher.models import CandidateAdvisor, MatchResult, StudentProfile
from phd_matcher.scoring import admit, connection, experience, gpa, pub


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

    # Count missing data signals to widen confidence band
    missing = 0
    if not student.papers:
        missing += 1
    if not student.current_advisors:
        missing += 1
    if not candidate.paths_to_advisors:
        missing += 1

    likelihood, band = admit.admit_likelihood(
        m, candidate.school_tier, candidate.pi_signal, missing_signals=missing
    )
    label = admit.likelihood_label(likelihood)

    explanation = explain_match(student, candidate)

    return MatchResult(
        candidate=candidate,
        c_score=round(c, 2),
        p_score=round(p, 2),
        e_score=round(e, 2),
        g_score=round(g, 2),
        match_score=round(m, 2),
        admit_likelihood=round(likelihood, 2),
        confidence_band=round(band, 2),
        likelihood_label=label,
        explanation=explanation,
    )


def rank_advisors(
    student: StudentProfile,
    candidates: list[CandidateAdvisor],
    top_k: int = 20,
    field_filter: bool = True,
) -> list[MatchResult]:
    """Rank candidates for a student, sorted by admission likelihood
    (with research-direction relevance as tiebreaker)."""
    if field_filter:
        candidates = [c for c in candidates if c.field == student.field]

    results = [compute_match(student, c) for c in candidates]

    def sort_key(r: MatchResult):
        rel = direction_relevance(student.research_direction, r.candidate.research_areas)
        return (r.admit_likelihood, rel, r.match_score)

    results.sort(key=sort_key, reverse=True)
    return results[:top_k]
