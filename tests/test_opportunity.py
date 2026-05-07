"""Tests for OpportunitySignal + opportunity_adj (roadmap #6a)."""

from __future__ import annotations

import pytest

from phd_matcher.matching.ranker import (
    compute_match,
    evidence_coverage,
    strict_validate,
)
from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    EvidenceSource,
    OpportunitySignal,
    StudentProfile,
)
from phd_matcher.scoring.advisor import (
    W_ELITE,
    W_INFLUENCE,
    W_PLACEMENT,
    advisor_strength_raw,
)
from phd_matcher.scoring.opportunity import (
    LEGACY_PI_ADJ,
    compute_opportunity_state,
    effective_active_funding_quality,
    effective_pi_signal,
    legacy_pi_adj,
    opportunity_adj_from_score,
    opportunity_score,
)


def _student() -> StudentProfile:
    return StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS Higgs",
    )


def _candidate(**kwargs) -> CandidateAdvisor:
    base = dict(
        id="c1", name="Prof. Y", institution="MIT",
        school_tier="top_10", field="physics",
        research_areas=["physics"],
    )
    base.update(kwargs)
    return CandidateAdvisor(**base)


# ---- A no longer reads funding / recruiting ------------------------------

def test_advisor_strength_excludes_funding():
    """Roadmap-#6a invariant: A_raw must not change when
    `active_funding_quality` changes — funding lives in O now."""
    base = {
        "normalized_collab_top20pct": 0.7,
        "collab_with_nas": True,
        "grad_placement_quality": 0.6,
    }
    a_no_funding = advisor_strength_raw(base)
    a_with_funding = advisor_strength_raw(
        {**base, "active_funding_quality": 0.95}
    )
    assert a_no_funding == a_with_funding


def test_advisor_strength_excludes_recruiting():
    """Roadmap-#6a invariant: A_raw must not change when `pi_signal`
    changes — recruiting health lives in O now."""
    base = {
        "normalized_collab_top20pct": 0.7,
        "collab_with_nas": True,
        "grad_placement_quality": 0.6,
    }
    a_missing_pi = advisor_strength_raw(base)
    a_strong_pi = advisor_strength_raw({**base, "pi_signal": "strong"})
    a_not_recruiting = advisor_strength_raw(
        {**base, "pi_signal": "not_recruiting"}
    )
    assert a_missing_pi == a_strong_pi == a_not_recruiting


def test_advisor_strength_new_weights():
    """A_raw = 0.40·influence + 0.30·elite + 0.30·placement."""
    assert W_INFLUENCE == pytest.approx(0.40)
    assert W_ELITE == pytest.approx(0.30)
    assert W_PLACEMENT == pytest.approx(0.30)
    assert W_INFLUENCE + W_ELITE + W_PLACEMENT == pytest.approx(1.0)

    raw = advisor_strength_raw({
        "normalized_collab_top20pct": 0.5,
        "collab_with_nas": True,
        "grad_placement_quality": 0.8,
    })
    expected = 0.40 * 0.5 + 0.30 * 1.0 + 0.30 * 0.8
    assert raw == pytest.approx(expected)


# ---- O score formula -----------------------------------------------------

def test_opportunity_score_strong_recruiting_with_funding():
    """Strong recruiting + active R01 + healthy lab → high O score."""
    cand = _candidate(opportunity_signal=OpportunitySignal(
        pi_signal="strong",
        active_funding_quality=0.85,
        lab_open_positions=2,
        current_student_count=6,
        recent_phd_graduations=2,
        grant_end_years=4,
        sabbatical_or_admin_load=False,
    ))
    o = opportunity_score(cand)
    assert o is not None
    # All components near max → O should clear the +0.2 threshold.
    assert o >= 0.70
    assert opportunity_adj_from_score(o) == pytest.approx(0.2)


def test_opportunity_score_missing_fields_neutral():
    """Empty OpportunitySignal (everything default) → all sub-signals
    neutral except recruiting_health(missing)=0.5 and funding=0.5
    (None → neutral). O = 0.5 → adj = 0.0 (the 'no info' baseline)."""
    cand = _candidate(opportunity_signal=OpportunitySignal())
    o = opportunity_score(cand)
    assert o is not None
    assert o == pytest.approx(0.50)
    assert opportunity_adj_from_score(o) == 0.0


def test_opportunity_score_shrinking_no_funding_low_capacity():
    """Shrinking lab + zero funding + zero open positions + no recent
    graduates + sabbatical → low O → -0.4 adj."""
    cand = _candidate(opportunity_signal=OpportunitySignal(
        pi_signal="shrinking",
        active_funding_quality=0.0,
        lab_open_positions=0,
        recent_phd_graduations=0,
        grant_end_years=0,
        sabbatical_or_admin_load=True,
    ))
    o = opportunity_score(cand)
    assert o is not None
    assert o < 0.30
    assert opportunity_adj_from_score(o) == pytest.approx(-0.4)


def test_opportunity_score_returns_none_for_pure_legacy():
    """No opportunity_signal → opportunity_score returns None (signals
    pure-legacy fallback path to the caller)."""
    cand = _candidate(pi_signal="strong")  # legacy only
    assert opportunity_score(cand) is None


# ---- opportunity_adj replaces pi_adj -------------------------------------

def test_opportunity_adj_replaces_pi_adj_in_application_strength():
    """Compare two candidates with identical CAPEG inputs but different
    pi_signals — opportunity_adj derived from O must produce the same
    adjustment as the old pi_adj table for legacy candidates."""
    student = _student()
    legacy_strong = _candidate(pi_signal="strong")
    legacy_normal = _candidate(pi_signal="normal")

    r_strong = compute_match(student, legacy_strong)
    r_normal = compute_match(student, legacy_normal)

    # Pure-legacy candidates: opportunity_adj == old PI_ADJ.
    assert r_strong.opportunity_adj == pytest.approx(LEGACY_PI_ADJ["strong"])
    assert r_normal.opportunity_adj == pytest.approx(LEGACY_PI_ADJ["normal"])

    # And application_strength differs by exactly +0.2 (the strong
    # boost), confirming opportunity_adj fully replaced pi_adj.
    assert (
        r_strong.application_strength - r_normal.application_strength
        == pytest.approx(0.2)
    )


def test_not_recruiting_still_forces_zero_strength():
    """Effective `not_recruiting` (legacy or new path) zeros out
    application_strength regardless of CAPEG match."""
    student = _student()

    # Legacy path
    legacy = _candidate(pi_signal="not_recruiting")
    r_legacy = compute_match(student, legacy)
    assert r_legacy.application_strength == 0.0

    # New path: opportunity_signal.pi_signal=not_recruiting wins via merge
    new = _candidate(
        pi_signal="strong",   # legacy says strong but new says not_recruiting
        opportunity_signal=OpportunitySignal(pi_signal="not_recruiting"),
    )
    r_new = compute_match(student, new)
    assert r_new.application_strength == 0.0


# ---- Field-by-field merge ------------------------------------------------

def test_opportunity_signal_overrides_legacy_pi_signal():
    """When opportunity_signal.pi_signal is explicitly set (!= 'missing'),
    it wins over the legacy top-level pi_signal."""
    cand = _candidate(
        pi_signal="strong",
        opportunity_signal=OpportunitySignal(pi_signal="shrinking"),
    )
    assert effective_pi_signal(cand) == "shrinking"


def test_opportunity_signal_falls_back_field_by_field():
    """When opportunity_signal exists but pi_signal is left at default
    'missing', the merge falls back to the legacy top-level value
    (NOT object-level override). Same field-by-field rule applies to
    active_funding_quality."""
    cand = _candidate(
        pi_signal="strong",
        active_funding_quality=0.7,
        opportunity_signal=OpportunitySignal(
            # pi_signal default = "missing" → falls back to legacy
            # active_funding_quality default = None → falls back to legacy
            lab_open_positions=2,    # only the new opt-in field is set
        ),
    )
    assert effective_pi_signal(cand) == "strong"
    assert effective_active_funding_quality(cand) == pytest.approx(0.7)


def test_legacy_pi_signal_fallback_preserves_old_behavior():
    """Pure-legacy candidate (no opportunity_signal) must produce the
    exact v1 PI_ADJ values for opportunity_adj — zero behavioral
    change for old JSON / old tests."""
    for sig, expected_adj in LEGACY_PI_ADJ.items():
        cand = _candidate(pi_signal=sig)
        o_score, adj, force_zero = compute_opportunity_state(cand)
        assert o_score is None              # signaled pure-legacy path
        assert adj == pytest.approx(expected_adj)
        assert legacy_pi_adj(sig) == pytest.approx(expected_adj)


def test_opportunity_signal_active_funding_explicit_overrides_legacy():
    """Explicit non-None opportunity_signal.active_funding_quality wins
    over legacy candidate.active_funding_quality."""
    cand = _candidate(
        active_funding_quality=0.7,
        opportunity_signal=OpportunitySignal(active_funding_quality=0.95),
    )
    assert effective_active_funding_quality(cand) == pytest.approx(0.95)


# ---- Evidence requirements / strict mode ---------------------------------

def test_opportunity_evidence_strict_requires_namespace_for_opt_in():
    """New opt-in opportunity field set without
    `supports_fields=['opportunity:<field>']` → unsourced in strict mode."""
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        lab_open_positions=2,   # set, no evidence
    ))
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "opportunity:lab_open_positions" in cov_strict.unsourced_names


def test_opportunity_evidence_strict_passes_with_correct_supports_fields():
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        lab_open_positions=2,
        evidence={
            "lab_open_positions": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.example/positions",
                source_type="lab_page",
                claim="Lab page lists 2 open PhD positions for Fall 2026",
                supports_fields=["opportunity:lab_open_positions"],
            )]),
        },
    ))
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "opportunity:lab_open_positions" not in cov_strict.unsourced_names
    assert "opportunity:lab_open_positions" not in cov_strict.missing_names


def test_legacy_pi_signal_evidence_still_satisfies_coverage():
    """Migration-friendly: pre-#6a JSON with
    `evidence['pi_signal'].items[..supports_fields=['pi_signal']]`
    must still verify the pi_signal coverage entry."""
    student = _student()
    cand = _candidate(
        pi_signal="strong",
        evidence={
            "pi_signal": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.example/people",
                source_type="lab_page",
                claim="lab lists 3 new PhDs admitted 2024",
                supports_fields=["pi_signal"],
            )]),
        },
    )
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "pi_signal" not in cov_strict.unsourced_names
    assert "pi_signal" not in cov_strict.missing_names


def test_new_pi_signal_evidence_via_opportunity_namespace_works():
    """Post-#6a: `opportunity_signal.evidence['pi_signal']` with
    `supports_fields=['opportunity:pi_signal']` is the preferred form
    and also verifies the pi_signal coverage entry."""
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        pi_signal="strong",
        evidence={
            "pi_signal": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.example/people",
                source_type="lab_page",
                claim="lab lists 3 new PhDs admitted 2024",
                supports_fields=["opportunity:pi_signal"],
            )]),
        },
    ))
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "pi_signal" not in cov_strict.unsourced_names
    assert "pi_signal" not in cov_strict.missing_names


def test_opt_in_opportunity_field_only_counts_when_set():
    """Empty OpportunitySignal: opt-in fields must NOT enter coverage
    (same opt-in pattern as research_fit / ProgramProfile)."""
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal())
    cov = evidence_coverage(student, cand)
    assert "opportunity:lab_open_positions" not in cov.missing_names
    assert "opportunity:lab_open_positions" not in cov.unsourced_names
    assert "opportunity:grant_end_years" not in cov.missing_names
    assert "opportunity:application_contact_policy" not in cov.missing_names


# ---- MatchResult exposes O fields ----------------------------------------

def test_match_result_outputs_o_score_and_opportunity_adj():
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        pi_signal="strong",
        active_funding_quality=0.85,
        lab_open_positions=2,
        current_student_count=5,
        recent_phd_graduations=2,
        grant_end_years=4,
        sabbatical_or_admin_load=False,
    ))
    r = compute_match(student, cand)
    assert r.o_score is not None
    assert 0.0 <= r.o_score <= 1.0
    # High-quality opportunity → should clear the +0.2 threshold.
    assert r.o_score >= 0.70
    assert r.opportunity_adj == pytest.approx(0.2)


def test_match_result_o_score_none_for_pure_legacy():
    """Pure-legacy candidates (no opportunity_signal) get
    `o_score=None` on the result (signals the legacy path was used)."""
    student = _student()
    cand = _candidate(pi_signal="normal")
    r = compute_match(student, cand)
    assert r.o_score is None
    # opportunity_adj comes from the legacy PI_ADJ table.
    assert r.opportunity_adj == pytest.approx(LEGACY_PI_ADJ["normal"])


def test_strict_validate_hint_for_opt_in_points_at_opportunity_signal():
    """Strict-mode error for an unsourced opt-in opportunity field
    must direct the agent at `opportunity_signal.evidence['<field>']`."""
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        grant_end_years=2,   # set, no evidence
    ))
    errors = strict_validate(student, cand)
    grant_error = next(
        (e for e in errors if "opportunity:grant_end_years" in e), None
    )
    assert grant_error is not None
    assert "opportunity_signal.evidence['grant_end_years']" in grant_error
    assert "supports_fields" in grant_error
    assert "opportunity:grant_end_years" in grant_error


# ---- ContactPolicy literal -----------------------------------------------

def test_contact_policy_literal_typo_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        OpportunitySignal(application_contact_policy="email")  # typo


def test_contact_policy_unknown_does_not_enter_coverage():
    """`application_contact_policy='unknown'` is the default and means
    'didn't check' — must NOT enter coverage."""
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        application_contact_policy="unknown",
    ))
    cov = evidence_coverage(student, cand)
    assert "opportunity:application_contact_policy" not in cov.missing_names
    assert "opportunity:application_contact_policy" not in cov.unsourced_names


def test_contact_policy_explicit_value_enters_coverage():
    student = _student()
    cand = _candidate(opportunity_signal=OpportunitySignal(
        application_contact_policy="email_first",   # set, no ev
    ))
    cov = evidence_coverage(student, cand)
    assert "opportunity:application_contact_policy" in cov.unsourced_names
