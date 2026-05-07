"""Tests for ProgramProfile + program_difficulty_penalty (roadmap #5)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from phd_matcher.matching.ranker import (
    compute_match,
    evidence_coverage,
    rank_advisors,
    strict_validate,
)
from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    EvidenceSource,
    ProgramProfile,
    StudentProfile,
)
from phd_matcher.scoring.program import (
    PENALTY_MAX,
    SCHOOL_TIER_FACTOR,
    program_difficulty_penalty,
)


def _student() -> StudentProfile:
    return StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS Higgs analysis",
    )


def _candidate(school_tier="top_10", program_profile=None) -> CandidateAdvisor:
    return CandidateAdvisor(
        id="c1", name="Prof. Y", institution="MIT",
        school_tier=school_tier, field="physics",
        research_areas=["physics"],
        program_profile=program_profile,
    )


# ---- school_tier_admit_rate_factor (replaces tier_adj) ------------------

def test_penalty_school_tier_only_top_10():
    """No program_profile → only school_tier contributes. Top_10 = 0.70."""
    penalty, reasons = program_difficulty_penalty("top_10", None)
    assert penalty == pytest.approx(0.70)
    assert any("top_10" in r for r in reasons)


def test_penalty_school_tier_only_top_11_30():
    penalty, _ = program_difficulty_penalty("top_11_30", None)
    assert penalty == pytest.approx(0.50)


def test_penalty_school_tier_only_top_31_60():
    penalty, _ = program_difficulty_penalty("top_31_60", None)
    assert penalty == pytest.approx(0.30)


def test_penalty_school_tier_only_top_60_plus_no_boost():
    """Roadmap-#5 calibration shift: top_60+ no longer gets the v1 +0.4
    boost. With no program_profile, penalty is 0.0."""
    penalty, reasons = program_difficulty_penalty("top_60_plus", None)
    assert penalty == 0.0
    assert reasons == []  # no positive contribution to surface


def test_penalty_factor_table_exposed():
    """Sanity: SCHOOL_TIER_FACTOR is exposed and has all 4 tiers."""
    assert set(SCHOOL_TIER_FACTOR) == {
        "top_10", "top_11_30", "top_31_60", "top_60_plus"
    }
    # All non-negative — penalty is one-sided.
    assert all(v >= 0 for v in SCHOOL_TIER_FACTOR.values())


# ---- Cohort size component -----------------------------------------------

def test_penalty_small_cohort_adds_penalty():
    p = ProgramProfile(cohort_size_estimate=4)
    penalty, reasons = program_difficulty_penalty("top_31_60", p)
    # 0.30 (top_31_60) + 0.10 (small cohort)
    assert penalty == pytest.approx(0.40)
    assert any("small cohort" in r for r in reasons)


def test_penalty_large_cohort_relieves():
    p = ProgramProfile(cohort_size_estimate=40)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    # 0.30 − 0.05 = 0.25
    assert penalty == pytest.approx(0.25)


def test_penalty_medium_cohort_neutral():
    """Cohort ≥ 8 and < 30 → no contribution."""
    p = ProgramProfile(cohort_size_estimate=15)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.30)  # school_tier only


# ---- Admission model component -------------------------------------------

def test_penalty_direct_admit_via_admission_model():
    p = ProgramProfile(admission_model="direct_admit")
    penalty, reasons = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.40)  # 0.30 + 0.10
    assert any("direct-admit" in r for r in reasons)


def test_penalty_direct_admit_via_required_flag():
    """direct_admit_required=True triggers the penalty even when
    admission_model is 'unknown'."""
    p = ProgramProfile(direct_admit_required=True)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.40)


def test_penalty_rotation_relieves():
    p = ProgramProfile(admission_model="rotation")
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.25)


def test_penalty_centralized_relieves():
    p = ProgramProfile(admission_model="centralized")
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.25)


# ---- Funding component ---------------------------------------------------

def test_penalty_pi_grant_funding_adds_penalty():
    p = ProgramProfile(funding_structure="pi_grant")
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.40)


def test_penalty_guaranteed_funding_relieves():
    p = ProgramProfile(funding_structure="guaranteed")
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.25)


# ---- Faculty count / area coverage ---------------------------------------

def test_penalty_solo_faculty_adds_penalty():
    p = ProgramProfile(faculty_count_in_area=1)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.40)


def test_penalty_broad_area_relieves():
    p = ProgramProfile(faculty_count_in_area=7)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.25)


# ---- International friendliness -----------------------------------------

def test_penalty_low_international_friendliness():
    p = ProgramProfile(international_friendliness=0.1)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.35)  # 0.30 + 0.05


def test_penalty_high_international_friendliness_neutral():
    p = ProgramProfile(international_friendliness=0.8)
    penalty, _ = program_difficulty_penalty("top_31_60", p)
    assert penalty == pytest.approx(0.30)


# ---- Clipping ------------------------------------------------------------

def test_penalty_clipped_at_max_080():
    """Worst-case top_10 stack should saturate at 0.80, not exceed."""
    p = ProgramProfile(
        cohort_size_estimate=4,
        admission_model="direct_admit",
        funding_structure="pi_grant",
        faculty_count_in_area=1,
        international_friendliness=0.1,
    )
    # 0.70 + 0.10 + 0.10 + 0.10 + 0.10 + 0.05 = 1.15 → clipped 0.80
    penalty, _ = program_difficulty_penalty("top_10", p)
    assert penalty == PENALTY_MAX
    assert penalty == 0.80


def test_penalty_clipped_at_min_0():
    """Best-case top_60+ with all reliefs cannot go negative."""
    p = ProgramProfile(
        cohort_size_estimate=40,
        admission_model="rotation",
        funding_structure="guaranteed",
        faculty_count_in_area=8,
    )
    # 0.0 − 0.05 − 0.05 − 0.05 − 0.05 = −0.20 → clipped 0.0
    penalty, _ = program_difficulty_penalty("top_60_plus", p)
    assert penalty == 0.0


# ---- ProgramProfile schema -----------------------------------------------

def test_program_profile_extra_forbid():
    with pytest.raises(ValidationError):
        ProgramProfile(unknown_field=True)


def test_program_profile_admission_model_literal_typo():
    with pytest.raises(ValidationError):
        ProgramProfile(admission_model="direct_admission")  # typo


def test_program_profile_cohort_negative_rejected():
    with pytest.raises(ValidationError):
        ProgramProfile(cohort_size_estimate=-1)


def test_program_profile_intl_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ProgramProfile(international_friendliness=1.5)


# ---- difficulty_adjusted_strength is the new sort key --------------------

def test_difficulty_adjusted_outranks_risk_adjusted():
    """Two candidates with identical risk_adjusted_strength but different
    program_profiles: the easier program ranks first via the new primary
    sort key (difficulty_adjusted_strength)."""
    student = _student()

    # Same school_tier (so school_tier_factor identical), but cand_easy
    # has a rotation/large-cohort program (negative contributions),
    # cand_hard has direct-admit/small-cohort.
    easy_program = ProgramProfile(
        admission_model="rotation",
        cohort_size_estimate=40,
        funding_structure="guaranteed",
    )
    hard_program = ProgramProfile(
        admission_model="direct_admit",
        cohort_size_estimate=4,
        funding_structure="pi_grant",
    )

    cand_easy = _candidate("top_31_60", easy_program)
    cand_easy.id = "easy"
    cand_hard = _candidate("top_31_60", hard_program)
    cand_hard.id = "hard"

    ranked = rank_advisors(student, [cand_hard, cand_easy], top_k=2)
    assert ranked[0].candidate.id == "easy"
    assert ranked[0].program_difficulty_penalty < ranked[1].program_difficulty_penalty
    # And the diff_adj values reflect the inversion vs the still-equal
    # risk_adjusted_strength baseline:
    assert ranked[0].risk_adjusted_strength == ranked[1].risk_adjusted_strength
    assert ranked[0].difficulty_adjusted_strength > ranked[1].difficulty_adjusted_strength


def test_strength_label_applied_to_difficulty_adjusted():
    """Label tracks difficulty_adjusted_strength, not application_strength.
    A top_10 candidate gets a 0.70 penalty subtracted before the label is
    computed; a top_60+ candidate gets no penalty. The easier program
    must end up with a higher-or-equal label, never lower.

    Note: application_strength can still differ across tiers because
    TIER_WEIGHTS shift the underlying CAPEG match_score. This test
    asserts the label/penalty invariant, not strength equality."""
    student = _student()
    hard = _candidate("top_10", program_profile=None)
    hard.id = "hard"
    easy = _candidate("top_60_plus", program_profile=None)
    easy.id = "easy"

    r_hard = compute_match(student, hard)
    r_easy = compute_match(student, easy)

    # The penalty side of the equation is exactly the school_tier_factor
    # gap (0.70 vs 0.00), since neither candidate has a program_profile:
    assert r_hard.program_difficulty_penalty == pytest.approx(0.70)
    assert r_easy.program_difficulty_penalty == 0.0

    # Label should reflect the diff_adj-based ranking — easy candidate's
    # label is higher-or-equal in tier ordering.
    LABEL_ORDER = ["Far Reach", "Reach", "Target", "Match", "Safe"]
    assert (
        LABEL_ORDER.index(r_easy.strength_label)
        >= LABEL_ORDER.index(r_hard.strength_label)
    ), (
        f"easy ({r_easy.strength_label}, "
        f"diff_adj={r_easy.difficulty_adjusted_strength}) must rank ≥ "
        f"hard ({r_hard.strength_label}, "
        f"diff_adj={r_hard.difficulty_adjusted_strength})"
    )


def test_difficulty_adjusted_clipped_at_0():
    """If risk_adjusted < penalty, diff_adj clips to 0.0 (cannot go negative)."""
    student = _student()
    # Bare top_10 candidate (school_tier_factor=0.70). With pi='missing'
    # (-0.1) and a defaults-only candidate the strength is low, but the
    # ranker should never emit negative diff_adj.
    bare = _candidate("top_10", program_profile=None)
    r = compute_match(student, bare)
    assert r.difficulty_adjusted_strength >= 0.0


# ---- Evidence coverage for ProgramProfile signals ------------------------

def test_program_signals_only_count_when_set():
    """ProgramProfile signals follow the same opt-in pattern as
    research_fit: a None / "unknown" field doesn't enter coverage."""
    student = _student()
    cand = _candidate("top_10", program_profile=None)
    cov_no_prog = evidence_coverage(student, cand)

    # With an empty ProgramProfile (all defaults), coverage is identical:
    cand.program_profile = ProgramProfile()
    cov_empty_prog = evidence_coverage(student, cand)

    assert cov_no_prog.total == cov_empty_prog.total
    assert "program:cohort_size_estimate" not in cov_empty_prog.missing_names


def test_program_set_signal_unsourced_counts():
    """A set program signal without supports_fields evidence shows up
    as unsourced (and triggers strict-mode rejection)."""
    student = _student()
    cand = _candidate(
        "top_31_60",
        program_profile=ProgramProfile(cohort_size_estimate=10),  # set, no ev
    )
    cov = evidence_coverage(student, cand)
    assert "program:cohort_size_estimate" in cov.unsourced_names

    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "program:cohort_size_estimate" in cov_strict.unsourced_names


def test_program_set_signal_with_evidence_verified():
    """Properly-cited program signal counts as verified."""
    student = _student()
    cand = _candidate(
        "top_31_60",
        program_profile=ProgramProfile(
            cohort_size_estimate=10,
            evidence={
                "cohort_size_estimate": EvidenceEntry(items=[EvidenceSource(
                    url="https://physics.example.edu/admissions",
                    source_type="lab_page",
                    claim="department admits ~10 PhDs/yr per admissions page",
                    supports_fields=["program:cohort_size_estimate"],
                )]),
            },
        ),
    )
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "program:cohort_size_estimate" not in cov_strict.unsourced_names
    assert "program:cohort_size_estimate" not in cov_strict.missing_names


def test_program_strict_validate_hint_points_to_program_profile_evidence():
    """Strict-mode error must direct the agent to
    program_profile.evidence['<field>'].items, not the candidate's top-
    level evidence dict."""
    student = _student()
    cand = _candidate(
        "top_31_60",
        program_profile=ProgramProfile(funding_structure="pi_grant"),  # set, no ev
    )
    errors = strict_validate(student, cand)
    fund_error = next((e for e in errors if "program:funding_structure" in e), None)
    assert fund_error is not None
    assert "program_profile.evidence['funding_structure']" in fund_error
    assert "supports_fields" in fund_error
    assert "program:funding_structure" in fund_error
