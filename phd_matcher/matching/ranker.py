"""End-to-end match pipeline + ranker."""

from __future__ import annotations

from dataclasses import dataclass, field

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


def _has_evidence(entry: EvidenceEntry | None) -> bool:
    if entry is None:
        return False
    return entry.has_evidence


# ---------------------------------------------------------------------------
# Evidence coverage — split missing vs unsourced
# ---------------------------------------------------------------------------

@dataclass
class EvidenceCoverage:
    """Per-candidate audit of which signals are verified, missing, or
    asserted-without-proof. The split surfaces two distinct risks:

      - `missing`: data point absent. Information gap (low confidence).
      - `unsourced`: value claimed without sources. Hallucination risk.

    Total `unverified = missing + unsourced` drives the confidence band.
    """

    total: int = 0
    verified: int = 0
    missing: int = 0
    unsourced: int = 0
    missing_names: list[str] = field(default_factory=list)
    unsourced_names: list[str] = field(default_factory=list)

    @property
    def unverified(self) -> int:
        return self.missing + self.unsourced


def _record(
    cov: EvidenceCoverage, name: str, *, is_set: bool, has_ev: bool
) -> None:
    cov.total += 1
    if has_ev:
        cov.verified += 1
    elif not is_set:
        cov.missing += 1
        cov.missing_names.append(name)
    else:
        cov.unsourced += 1
        cov.unsourced_names.append(name)


def evidence_coverage(
    student: StudentProfile, candidate: CandidateAdvisor
) -> EvidenceCoverage:
    """Walk every signal that needs evidence and tally verified / missing /
    unsourced. The matcher uses `unverified = missing + unsourced` for the
    confidence band; the split is surfaced in MatchResult for the agent
    to communicate transparently."""
    cov = EvidenceCoverage()

    # Connection paths to each advisor
    if student.current_advisors:
        for adv in student.current_advisors:
            edge = candidate.paths_to_advisors.get(adv.id)
            if edge is None:
                _record(cov, f"path:{adv.id}", is_set=False, has_ev=False)
            else:
                is_set = edge.has_any_edge
                has_ev = edge.has_evidence
                _record(cov, f"path:{adv.id}", is_set=is_set, has_ev=has_ev)

    # school_tier (always set; required field)
    school_ev = candidate.evidence.get("school_tier") if candidate.evidence else None
    _record(cov, "school_tier", is_set=True, has_ev=_has_evidence(school_ev))

    # Field-strength signals (each can be None or set)
    field_pairs = [
        ("normalized_collab_top20pct", candidate.normalized_collab_top20pct),
        ("collab_with_nas", candidate.collab_with_nas),
        ("grad_placement_quality", candidate.grad_placement_quality),
    ]
    for sig, val in field_pairs:
        is_set = val is not None
        ev = candidate.evidence.get(sig) if candidate.evidence else None
        _record(cov, sig, is_set=is_set, has_ev=_has_evidence(ev))

    # PI signal — "missing" means not set
    is_pi_set = candidate.pi_signal != "missing"
    pi_ev = candidate.evidence.get("pi_signal") if candidate.evidence else None
    _record(cov, "pi_signal", is_set=is_pi_set, has_ev=_has_evidence(pi_ev))

    return cov


def count_unverified_signals(
    student: StudentProfile, candidate: CandidateAdvisor
) -> int:
    """Back-compat wrapper. Use `evidence_coverage()` for the split."""
    return evidence_coverage(student, candidate).unverified


# ---------------------------------------------------------------------------
# Strict-evidence validator (used by --strict-evidence CLI flag)
# ---------------------------------------------------------------------------

def strict_validate(
    student: StudentProfile, candidate: CandidateAdvisor
) -> list[str]:
    """In strict mode, return human-readable errors for each unsourced claim.

    Missing signals (data absent, no evidence) do NOT error — they're a
    legitimate "we couldn't find this" state. Only `unsourced` claims
    (positive value, no evidence) are errors.
    """
    cov = evidence_coverage(student, candidate)
    if cov.unsourced == 0:
        return []
    return [
        f"candidate={candidate.id} unsourced claim: {name} "
        f"(value set without evidence — provide evidence['{name}'].items "
        f"or evidence['{name}'].sources)"
        for name in cov.unsourced_names
    ]


# ---------------------------------------------------------------------------
# Risk-adjusted scoring
# ---------------------------------------------------------------------------

def _risk_adjusted(strength: float, band: float) -> float:
    """`strength - band/2`. Half the band is a downside discount: a
    candidate at 3.0 ±0.2 (risk-adjusted 2.9) outranks 3.2 ±0.8 (2.8)."""
    return strength - band / 2.0


def _lower_bound(strength: float, band: float) -> float:
    """`strength - band`. Conservative reading at the wide edge of
    uncertainty — what the agent should mention when explaining downside."""
    return max(0.0, strength - band)


# ---------------------------------------------------------------------------
# Compute / rank
# ---------------------------------------------------------------------------

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

    cov = evidence_coverage(student, candidate)

    strength, band = admit.application_strength(
        m, candidate.school_tier, candidate.pi_signal, unverified_count=cov.unverified
    )
    label = admit.strength_label(strength)

    explanation = explain_match(student, candidate, cov)

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
        unverified_signals=cov.unverified,
        missing_signals=cov.missing,
        unsourced_signals=cov.unsourced,
        total_signals=cov.total,
        missing_signal_names=cov.missing_names,
        unsourced_signal_names=cov.unsourced_names,
        risk_adjusted_strength=round(_risk_adjusted(strength, band), 2),
        lower_bound=round(_lower_bound(strength, band), 2),
    )


def rank_advisors(
    student: StudentProfile,
    candidates: list[CandidateAdvisor],
    top_k: int = 20,
    field_filter: bool = True,
) -> list[MatchResult]:
    """Rank candidates by **risk-adjusted strength**. A wider confidence band
    is a downside discount, so well-evidenced candidates outrank loosely-
    claimed peers even at lower nominal strength."""
    if field_filter:
        candidates = [c for c in candidates if c.field == student.field]

    results = [compute_match(student, c) for c in candidates]

    def sort_key(r: MatchResult):
        rel = direction_relevance(student.research_direction, r.candidate.research_areas)
        return (r.risk_adjusted_strength, rel, r.application_strength)

    results.sort(key=sort_key, reverse=True)
    return results[:top_k]
