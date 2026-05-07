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
    FieldProfile,
    MatchResult,
    PathEdge,
    StudentProfile,
)
from phd_matcher.scoring import admit, advisor, connection, experience, gpa, program, pub

# A-dimension (Advisor influence) signals. Each needs an EvidenceEntry
# whose items list `<field>` in `supports_fields`.
# (Renamed from _FIELD_STRENGTH_SIGNALS in roadmap-#3 — these describe
# the candidate PI's own standing, distinct from C / connection paths.)
_ADVISOR_INFLUENCE_SIGNALS = (
    "normalized_collab_top20pct",
    "collab_with_nas",
    "grad_placement_quality",
    "active_funding_quality",
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

    # A-dimension (Advisor influence) signals
    advisor_pairs = [
        ("normalized_collab_top20pct", candidate.normalized_collab_top20pct),
        ("collab_with_nas", candidate.collab_with_nas),
        ("grad_placement_quality", candidate.grad_placement_quality),
        ("active_funding_quality", candidate.active_funding_quality),
    ]
    for sig, val in advisor_pairs:
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

    # Research fit (roadmap #4) — tie-breaker, not a pillar. Counted in
    # coverage ONLY when the agent actually computed a score; an absent
    # research_fit (None) must NOT widen the confidence band, otherwise
    # it would indirectly move risk_adjusted_strength and break the
    # tie-breaker-only invariant. When set, evidence is required (strict
    # mode rejects unsourced; default mode flags it in unsourced_names).
    if candidate.research_fit_score is not None:
        rf_ev = candidate.evidence.get("research_fit") if candidate.evidence else None
        _record(
            cov, "research_fit",
            is_set=True,
            has_ev=_entry_has_evidence_for(rf_ev, "research_fit", strict=strict),
        )

    # Program profile (roadmap #5) — same opt-in pattern as research_fit.
    # Each scoring-relevant program field is counted in coverage ONLY when
    # the agent actually set it; "unknown" (literal) and None (numeric /
    # bool optionals) both mean "didn't check" and don't enter coverage.
    # When set, evidence under `program_profile.evidence[<field>]` with
    # `supports_fields=["program:<field>"]` is required in strict mode.
    if candidate.program_profile is not None:
        prog = candidate.program_profile
        for field_name in program.SCORING_RELEVANT_FIELDS:
            if not program.program_signal_is_set(prog, field_name):
                continue
            ev = program.program_evidence_for(prog, field_name)
            ns_name = f"program:{field_name}"
            _record(
                cov, ns_name,
                is_set=True,
                has_ev=_entry_has_evidence_for(ev, ns_name, strict=strict),
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
    "active_funding_quality": (
        "evidence['active_funding_quality'].items must include an "
        "EvidenceSource citing active grant records "
        "(NIH RePORTER / NSF Award Search / DOE Office of Science / ERC)"
    ),
    "pi_signal": (
        "evidence['pi_signal'].items must include an EvidenceSource citing "
        "the lab's current-students or recruiting page"
    ),
    "research_fit": (
        "evidence['research_fit'].items must include an EvidenceSource "
        "with supports_fields containing 'research_fit' (cite the candidate's "
        "recent papers, lab page, or open-grant abstract that demonstrates "
        "alignment with the student's research_direction)"
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
    if name.startswith("program:"):
        field = name.split(":", 1)[1]
        return (
            f"program_profile.evidence['{field}'].items must include an "
            f"EvidenceSource with supports_fields containing 'program:{field}' "
            f"(cite the department's admissions / cohort / funding page, an "
            f"alumni report, or a faculty-listing page that backs the "
            f"specific program signal)"
        )
    return _FIX_HINTS.get(
        name,
        f"evidence['{name}'].items must include an EvidenceSource "
        f"with supports_fields containing '{name}'",
    )


def validate_research_fit_axes(
    candidates: list[CandidateAdvisor],
    field_profile: FieldProfile | None,
) -> list[str]:
    """Warn on `research_fit_axes` keys that aren't declared by the active
    FieldProfile. The numeric range [0, 1] is already enforced by Pydantic
    on `CandidateAdvisor.research_fit_axes`; this catches axis-key drift
    (e.g., a CS-field candidate using {'detector_or_technique': 0.9},
    which is a physics-only axis).

    Returns a list of human-readable warning strings — empty when no
    profile is loaded, the profile declares no axes, or all keys match.
    """
    if field_profile is None or not field_profile.research_fit_axes:
        return []
    profile_axes = set(field_profile.research_fit_axes)
    warnings: list[str] = []
    for cand in candidates:
        if not cand.research_fit_axes:
            continue
        unknown = sorted(a for a in cand.research_fit_axes if a not in profile_axes)
        if unknown:
            warnings.append(
                f"candidate={cand.id}: research_fit_axes contains "
                f"{unknown!r} which are not in {field_profile.id} "
                f"FieldProfile.research_fit_axes={sorted(profile_axes)!r}"
            )
    return warnings


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

def compute_match(
    student: StudentProfile,
    candidate: CandidateAdvisor,
    *,
    field_profile: FieldProfile | None = None,
) -> MatchResult:
    """Score one (student, candidate) pair across all dimensions.

    Post-roadmap-#5 the pipeline is:
      1. CAPEG match_score (unchanged formula)
      2. application_strength = match_score + pi_adj   (no more tier_adj)
      3. risk_adjusted_strength = application_strength − band/2
      4. program_difficulty_penalty = f(school_tier, program_profile)
      5. difficulty_adjusted_strength = max(0, risk_adjusted − penalty)  ← new sort key
      6. strength_label is applied to difficulty_adjusted_strength
         (previously applied to application_strength)

    `field_profile`, when provided, flows into `pub_score` for per-field
    paper-status weight overrides and author-role normalization. Its `id`
    is recorded on the result for traceability.
    """
    p = pub.pub_score(
        [pp.model_dump() for pp in student.papers],
        field_profile=field_profile,
    )
    g = gpa.gpa_score(student.gpa_raw, student.gpa_scale)
    e = experience.experience_score([ee.model_dump() for ee in student.experiences])
    c = connection.connection_score(
        [a.model_dump() for a in student.current_advisors],
        candidate.model_dump(),
    )
    a_score = advisor.advisor_strength(candidate.model_dump())

    m = admit.match_score(c, a_score, p, e, g, candidate.school_tier)

    cov = evidence_coverage(student, candidate)

    strength, band = admit.application_strength(
        m, candidate.school_tier, candidate.pi_signal, unverified_count=cov.unverified
    )
    risk_adj = _risk_adjusted(strength, band)

    penalty, difficulty_reasons = program.program_difficulty_penalty(
        candidate.school_tier, candidate.program_profile
    )
    diff_adj = max(0.0, risk_adj - penalty)

    # Label is now applied to difficulty_adjusted_strength (post-roadmap-#5).
    label = admit.strength_label(diff_adj)

    explanation = explain_match(student, candidate, cov)

    return MatchResult(
        candidate=candidate,
        c_score=round(c, 2),
        a_score=round(a_score, 2),
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
        risk_adjusted_strength=round(risk_adj, 2),
        lower_bound=round(_lower_bound(strength, band), 2),
        program_difficulty_penalty=round(penalty, 2),
        difficulty_adjusted_strength=round(diff_adj, 2),
        difficulty_reasons=difficulty_reasons,
        field_profile_id=(field_profile.id if field_profile else None),
        research_fit_score=candidate.research_fit_score,
        research_fit_summary=candidate.research_fit_summary,
        research_fit_axes=dict(candidate.research_fit_axes),
    )


def rank_advisors(
    student: StudentProfile,
    candidates: list[CandidateAdvisor],
    top_k: int = 20,
    field_filter: bool = True,
    *,
    field_profile: FieldProfile | None = None,
) -> list[MatchResult]:
    """Rank candidates by **difficulty-adjusted strength** (post-roadmap-#5).

    Sort key (descending priority):
      1. difficulty_adjusted_strength = risk_adjusted_strength − program_difficulty_penalty
      2. risk_adjusted_strength
      3. research_fit_score   (None → -inf; ranked last among ties)
      4. direction_relevance  (keyword overlap fallback)
      5. application_strength (raw)
      6. lower_bound          (final tiebreak — favors narrower band)

    Program difficulty enters the *primary* sort key — a hard top_10
    direct-admit small-cohort program is now visibly down-ranked vs an
    equally-strong candidate at a broader, rotation-based program.
    Research fit remains a pure tie-breaker (rank 3).

    `field_profile`, when provided, flows into the scoring engine (paper
    status overrides, author-role) and the result `field_profile_id`.
    """
    if field_filter:
        candidates = [c for c in candidates if c.field == student.field]

    results = [
        compute_match(student, c, field_profile=field_profile) for c in candidates
    ]

    def sort_key(r: MatchResult):
        rel = direction_relevance(student.research_direction, r.candidate.research_areas)
        # None research_fit_score sorts last among ties (with reverse=True
        # below, the smallest goes last; -1.0 puts it strictly below 0.0).
        rf = r.research_fit_score if r.research_fit_score is not None else -1.0
        return (
            r.difficulty_adjusted_strength,
            r.risk_adjusted_strength,
            rf,
            rel,
            r.application_strength,
            r.lower_bound,
        )

    results.sort(key=sort_key, reverse=True)
    return results[:top_k]
