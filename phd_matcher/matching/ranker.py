"""End-to-end match pipeline + ranker.

Per fourth-pass review: evidence verification is now **claim-level**, not
just "any URL anywhere". Each non-default field needs an `EvidenceSource`
in `items` with the field name in its `supports_fields` list.

In `--strict-evidence` mode, legacy bare `sources: list[str]` URLs do not
count — only structured `items` with matching `supports_fields`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from phd_matcher.matching.direction import direction_relevance
from phd_matcher.matching.explainer import explain_match
from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    MatchResult,
    PathEdge,
    StudentProfile,
)
from phd_matcher.scoring import admit, connection, experience, gpa, pub

# Field-strength signals that should each have an EvidenceEntry with sources
# whose items list `<field>` in `supports_fields`.
_FIELD_STRENGTH_SIGNALS = (
    "normalized_collab_top20pct",
    "collab_with_nas",
    "grad_placement_quality",
)


def _entry_has_evidence_for(
    entry: EvidenceEntry | None, field_name: str, *, strict: bool
) -> bool:
    if entry is None:
        return False
    return entry.has_evidence_for(field_name, strict=strict)


# ---------------------------------------------------------------------------
# Evidence coverage — claim-level audit, missing vs unsourced
# ---------------------------------------------------------------------------

@dataclass
class EvidenceCoverage:
    """Per-candidate audit of which signals are verified / missing /
    asserted-without-proof.

      - `missing`: data point absent (information gap, low confidence).
      - `unsourced`: value claimed without sources backing the specific
        field (hallucination risk).

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


def _path_edge_verified(edge: PathEdge, advisor_id: str, *, strict: bool) -> bool:
    """A PathEdge is verified iff every set field has its own evidence.

    For an edge with no fields set (verified-empty: "I searched, found
    nothing"):
      - default mode: any evidence counts (legacy back-compat).
      - strict mode: needs an item with `supports_fields=["path:<id>"]`
        — bare `sources` URLs are not valid claim-level proof of "I
        searched" in strict mode.
    """
    fields_set = edge.fields_set()
    if fields_set:
        return all(edge.has_evidence_for(f, strict=strict) for f in fields_set)
    # Verified-empty case
    if not strict:
        return edge.has_evidence
    return edge.has_evidence_for(f"path:{advisor_id}", strict=True)


def _path_edge_is_set(edge: PathEdge) -> bool:
    """An edge counts as 'agent making a claim' if it has any sub-field set
    OR has any recorded evidence. The latter captures verified-empty-path
    claims ('I searched, found nothing') so they get audited too."""
    return edge.has_any_edge or edge.has_evidence


def evidence_coverage(
    student: StudentProfile,
    candidate: CandidateAdvisor,
    *,
    strict: bool = False,
) -> EvidenceCoverage:
    """Walk every signal that needs evidence and tally verified / missing /
    unsourced. In `strict` mode, only structured `items` with matching
    `supports_fields` count — legacy bare URLs don't.
    """
    cov = EvidenceCoverage()

    # Connection paths to each advisor — per-set-field check.
    # An empty PathEdge with sources but no items counts as "agent claiming
    # verified-empty" — strict mode requires structured items with
    # supports_fields=['path:<id>'] to verify; bare sources fail there.
    if student.current_advisors:
        for adv in student.current_advisors:
            edge = candidate.paths_to_advisors.get(adv.id)
            if edge is None:
                _record(cov, f"path:{adv.id}", is_set=False, has_ev=False)
            else:
                is_set = _path_edge_is_set(edge)
                has_ev = _path_edge_verified(edge, adv.id, strict=strict)
                _record(cov, f"path:{adv.id}", is_set=is_set, has_ev=has_ev)

    # school_tier — always required, always "set"
    school_ev = candidate.evidence.get("school_tier") if candidate.evidence else None
    _record(
        cov, "school_tier",
        is_set=True,
        has_ev=_entry_has_evidence_for(school_ev, "school_tier", strict=strict),
    )

    # research_areas — non-empty counts as set
    ra_ev = candidate.evidence.get("research_areas") if candidate.evidence else None
    _record(
        cov, "research_areas",
        is_set=bool(candidate.research_areas),
        has_ev=_entry_has_evidence_for(ra_ev, "research_areas", strict=strict),
    )

    # Field-strength signals
    field_pairs = [
        ("normalized_collab_top20pct", candidate.normalized_collab_top20pct),
        ("collab_with_nas", candidate.collab_with_nas),
        ("grad_placement_quality", candidate.grad_placement_quality),
    ]
    for sig, val in field_pairs:
        is_set = val is not None
        ev = candidate.evidence.get(sig) if candidate.evidence else None
        _record(
            cov, sig,
            is_set=is_set,
            has_ev=_entry_has_evidence_for(ev, sig, strict=strict),
        )

    # PI signal
    is_pi_set = candidate.pi_signal != "missing"
    pi_ev = candidate.evidence.get("pi_signal") if candidate.evidence else None
    _record(
        cov, "pi_signal",
        is_set=is_pi_set,
        has_ev=_entry_has_evidence_for(pi_ev, "pi_signal", strict=strict),
    )

    return cov


def count_unverified_signals(
    student: StudentProfile, candidate: CandidateAdvisor
) -> int:
    """Back-compat wrapper. Use `evidence_coverage()` for the breakdown."""
    return evidence_coverage(student, candidate).unverified


# ---------------------------------------------------------------------------
# Strict-evidence validator (used by --strict-evidence CLI flag)
# ---------------------------------------------------------------------------

# How to fix each unsourced signal — points the agent at the right location.
_FIX_HINTS: dict[str, str] = {
    "school_tier": (
        "evidence['school_tier'].items must include an EvidenceSource "
        "with supports_fields containing 'school_tier' (cite US News or "
        "field-equivalent ranking page)"
    ),
    "research_areas": (
        "evidence['research_areas'].items must include an EvidenceSource "
        "with supports_fields containing 'research_areas' (cite the "
        "candidate's faculty page or recent paper abstracts)"
    ),
    "normalized_collab_top20pct": (
        "evidence['normalized_collab_top20pct'].items must include an "
        "EvidenceSource (Google Scholar / OpenAlex profile URL with "
        "h_index)"
    ),
    "collab_with_nas": (
        "evidence['collab_with_nas'].items must include an EvidenceSource "
        "citing the NAS / HHMI directory match"
    ),
    "grad_placement_quality": (
        "evidence['grad_placement_quality'].items must include an "
        "EvidenceSource citing the lab's alumni / former-students page"
    ),
    "pi_signal": (
        "evidence['pi_signal'].items must include an EvidenceSource citing "
        "the lab's current-students or recruiting page"
    ),
}


def _fix_hint_for(name: str) -> str:
    if name.startswith("path:"):
        adv_id = name.split(":", 1)[1]
        return (
            f"paths_to_advisors['{adv_id}'].items must include EvidenceSource "
            f"records covering each set sub-field (small_team_coauthor_5y, "
            f"big_collab_papers_5y, same_working_group, …) via supports_fields. "
            f"For a verified-empty path (searched and found no edges), include "
            f"one item with supports_fields=['path:{adv_id}'] documenting "
            f"what databases you searched."
        )
    return _FIX_HINTS.get(
        name,
        f"evidence['{name}'].items must include an EvidenceSource "
        f"with supports_fields containing '{name}'",
    )


def strict_validate(
    student: StudentProfile, candidate: CandidateAdvisor
) -> list[str]:
    """In strict mode, return human-readable errors for each unsourced claim.

    Missing signals (data absent, no evidence) do NOT error — they're a
    legitimate "we couldn't find this" state. Only `unsourced` claims
    (positive value, no evidence) are errors.

    Strict mode rejects legacy bare `sources` as claim-level proof — only
    structured `items` with matching `supports_fields` count.
    """
    cov = evidence_coverage(student, candidate, strict=True)
    if cov.unsourced == 0:
        return []
    return [
        f"candidate={candidate.id} unsourced claim: {name} — {_fix_hint_for(name)}"
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
