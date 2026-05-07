"""Tests for ranker: evidence coverage split + risk-adjusted ranking."""

import pytest
from pydantic import ValidationError

from phd_matcher.matching.ranker import (
    _lower_bound,
    _risk_adjusted,
    count_unverified_signals,
    evidence_coverage,
    rank_advisors,
    strict_validate,
)
from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    EvidenceEntry,
    EvidenceSource,
    PathEdge,
    StudentProfile,
)


def _student_with_advisor():
    return StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS Higgs analysis",
        current_advisors=[CurrentAdvisor(id="adv_001", name="Prof. X", institution="THU")],
    )


def _bare_candidate():
    return CandidateAdvisor(
        id="c1", name="Prof. Y", institution="MIT", school_tier="top_10",
        field="physics",
    )


def test_unverified_count_all_missing():
    """Brand-new candidate with no evidence → max unverified count."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # 1 path missing + 3 field-strength + 1 school_tier + 1 pi=missing = 6
    assert count_unverified_signals(student, cand) == 6


def test_unverified_count_all_verified():
    """Fully sourced candidate → 0 unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            sources=["https://scholar.google.com/..."],
        ),
    }
    cand.normalized_collab_top20pct = 0.7
    cand.collab_with_nas = True
    cand.grad_placement_quality = 0.8
    cand.pi_signal = "normal"
    cand.evidence = {
        "normalized_collab_top20pct": EvidenceEntry(sources=["https://scholar.google.com/..."]),
        "collab_with_nas": EvidenceEntry(sources=["https://www.nasonline.org/..."]),
        "grad_placement_quality": EvidenceEntry(sources=["https://lab.mit.edu/alumni"]),
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/people"]),
        "school_tier": EvidenceEntry(sources=["https://www.usnews.com/..."]),
    }
    assert count_unverified_signals(student, cand) == 0


def test_unverified_path_without_sources_counts():
    """Per #1: even non-default path edges without sources are unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(small_team_coauthor_5y=3),  # no sources
    }
    # 1 path (unsourced) + 3 field-strength + 1 school_tier + 1 pi = 6
    assert count_unverified_signals(student, cand) == 6


def test_unverified_pi_signal_non_missing_without_sources():
    """Per #1: pi_signal != 'missing' without evidence sources is unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"  # claim without sources
    # 1 path + 3 field-strength + 1 school_tier + 1 pi (unsourced) = 6
    assert count_unverified_signals(student, cand) == 6


def test_unverified_pi_signal_non_missing_with_sources_is_verified():
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"
    cand.evidence = {
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/openings"]),
    }
    # 1 path + 3 field-strength + 1 school_tier + 0 pi(verified) = 5
    assert count_unverified_signals(student, cand) == 5


def test_unverified_field_strength_default_value_without_sources():
    """Per #1: even default values count as unverified without sources."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # All field-strengths at default None; pi missing; school_tier no sources
    assert count_unverified_signals(student, cand) == 6


def test_unverified_no_advisor_means_no_path_count():
    """Without a current advisor, paths_to_advisors isn't checked."""
    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS",
        # no current_advisors
    )
    cand = _bare_candidate()
    # 0 paths + 3 field-strength + 1 school_tier + 1 pi = 5
    assert count_unverified_signals(student, cand) == 5


def test_unverified_path_with_only_sources_and_note_is_verified():
    """Honest 'we searched, found nothing' record with sources is treated
    as verified, even if no edge fields are set."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            sources=["https://scholar.google.com/..."],
            note="searched OpenAlex + Math Genealogy: 0 co-authored papers, no shared lineage",
        ),
    }
    # 0 path(verified-empty) + 3 field-strength + 1 school_tier + 1 pi = 5
    assert count_unverified_signals(student, cand) == 5


# ---- Risk-adjusted ranking (post-review tier 3 #1) -----------------------

def test_risk_adjusted_subtracts_half_band():
    assert _risk_adjusted(strength=3.0, band=0.4) == 2.8
    assert _risk_adjusted(strength=3.0, band=0.8) == 2.6
    assert _risk_adjusted(strength=3.0, band=0.0) == 3.0


def test_well_evidenced_lower_strength_outranks_loose_higher():
    """A well-sourced candidate (narrow band) outranks a loosely-claimed
    candidate (wide band) when the strength gap is smaller than the
    band-discount gap. Risk-adjusted = strength - band/2."""
    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
    )

    # Loose: pi_signal=strong (+0.2 strength), but NO sources anywhere.
    #   strength gain: +0.2 from strong recruiting
    #   band cost: ±0.8 (5 unverified signals → max band)
    #   risk-adjusted disadvantage: 0.8/2 = 0.4
    loose = CandidateAdvisor(
        id="loose", name="Prof. Loose", institution="Stanford",
        school_tier="top_10",
        field="physics", research_areas=["physics"],
        normalized_collab_top20pct=0.7,
        collab_with_nas=False,
        grad_placement_quality=0.6,
        pi_signal="strong",     # +0.2 over normal
    )

    # Tight: pi_signal=normal but everything sourced.
    #   strength loss: 0 (normal recruiting baseline)
    #   band benefit: ±0.2 (0 unverified)
    tight = CandidateAdvisor(
        id="tight", name="Prof. Tight", institution="Berkeley",
        school_tier="top_10",
        field="physics", research_areas=["physics"],
        normalized_collab_top20pct=0.7,
        collab_with_nas=False,
        grad_placement_quality=0.6,
        pi_signal="normal",
        evidence={
            "school_tier":                EvidenceEntry(sources=["https://www.usnews.com/..."]),
            "normalized_collab_top20pct": EvidenceEntry(sources=["https://scholar.google.com/..."]),
            "collab_with_nas":            EvidenceEntry(sources=["https://www.nasonline.org/..."]),
            "grad_placement_quality":     EvidenceEntry(sources=["https://lab.berkeley.edu/alumni"]),
            "pi_signal":                  EvidenceEntry(sources=["https://lab.berkeley.edu/people"]),
        },
    )

    results = rank_advisors(student, [loose, tight], top_k=2)
    # tight wins:
    #   risk_adj(loose) ≈ strength_loose - 0.4
    #   risk_adj(tight) ≈ strength_tight - 0.1
    #   strength_loose - strength_tight = 0.2 (only the pi adjustment)
    #   so tight risk-adjusted score is higher by 0.3 - 0.2 = 0.1
    assert results[0].candidate.id == "tight"
    assert results[1].candidate.id == "loose"


# ---- Evidence coverage split (P1: claim-level evidence) ----

def test_evidence_coverage_splits_missing_vs_unsourced():
    """A `None` field with no evidence is missing; a *set* field with no
    evidence is unsourced. The matcher reports both separately.

    school_tier is required (always set), so absent evidence makes it
    unsourced — the cardinal rule mandates citing the ranking source.
    """
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.collab_with_nas = True   # additional unsourced claim

    cov = evidence_coverage(student, cand)
    # 1 path + 1 school_tier + 3 field-strength + 1 pi = 6 total
    assert cov.total == 6
    # Unsourced: school_tier (always set) + collab_with_nas (set, no ev) = 2
    assert cov.unsourced == 2
    assert "school_tier" in cov.unsourced_names
    assert "collab_with_nas" in cov.unsourced_names
    # Missing: 1 path + 2 other field-strength (None) + 1 pi (missing) = 4
    assert cov.missing == 4


def test_evidence_coverage_all_verified_via_items():
    """Evidence via the structured `items` field counts equally to the
    legacy `sources` list."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            items=[EvidenceSource(
                url="https://scholar.google.com/...",
                source_type="google_scholar",
                claim="3 co-authored papers in 2022-2024",
                supports_fields=["small_team_coauthor_5y"],
            )],
        ),
    }
    cand.normalized_collab_top20pct = 0.7
    cand.collab_with_nas = True
    cand.grad_placement_quality = 0.8
    cand.pi_signal = "normal"
    cand.evidence = {
        "school_tier": EvidenceEntry(items=[EvidenceSource(
            url="https://www.usnews.com/...",
            source_type="us_news",
            claim="MIT physics ranked #1",
            supports_fields=["school_tier"],
        )]),
        "normalized_collab_top20pct": EvidenceEntry(items=[EvidenceSource(
            url="https://scholar.google.com/...",
            source_type="google_scholar",
            claim="h_index = 35",
            supports_fields=["normalized_collab_top20pct"],
        )]),
        "collab_with_nas": EvidenceEntry(items=[EvidenceSource(
            url="https://www.nasonline.org/...",
            source_type="nas",
            claim="recent co-author Z is NAS member",
            supports_fields=["collab_with_nas"],
        )]),
        "grad_placement_quality": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/alumni",
            source_type="lab_page",
            claim="3 of last 5 alumni in faculty positions",
            supports_fields=["grad_placement_quality"],
        )]),
        "pi_signal": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/people",
            source_type="lab_page",
            claim="lists 3 PhDs admitted in 2023-2024",
            supports_fields=["pi_signal"],
        )]),
    }

    cov = evidence_coverage(student, cand)
    assert cov.unverified == 0
    assert cov.verified == cov.total
    assert cov.total == 6


# ---- EvidenceSource model validation ----

def test_evidence_source_rejects_unknown_source_type():
    with pytest.raises(ValidationError):
        EvidenceSource(
            url="https://...", source_type="random_blog", claim="x",
        )


def test_evidence_source_rejects_unknown_field():
    with pytest.raises(ValidationError):
        EvidenceSource(
            url="https://...", source_type="lab_page", claim="x",
            unknown_field=True,
        )


def test_evidence_entry_supports_both_legacy_and_structured():
    """The matcher accepts either `items` or `sources` as proof."""
    legacy = EvidenceEntry(sources=["https://..."])
    structured = EvidenceEntry(items=[EvidenceSource(
        url="https://...", source_type="other", claim="x",
    )])
    both_empty = EvidenceEntry()

    assert legacy.has_evidence
    assert structured.has_evidence
    assert not both_empty.has_evidence


# ---- strict-evidence validation ----

def test_strict_validate_flags_unsourced_claims():
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.normalized_collab_top20pct = 0.8  # unsourced
    cand.pi_signal = "strong"               # unsourced

    errors = strict_validate(student, cand)
    # 3 unsourced: school_tier (always set) + 2 new claims
    assert len(errors) == 3
    joined = " ".join(errors)
    assert "normalized_collab_top20pct" in joined
    assert "pi_signal" in joined
    assert "school_tier" in joined


def test_strict_validate_passes_when_all_sourced_or_missing():
    """Strict mode allows missing signals (no value, no evidence) — they're
    honest 'we couldn't verify' states. school_tier is required, so it
    needs evidence even when no other claims are made."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # school_tier is required field so it's always "set"; needs evidence
    cand.evidence = {
        "school_tier": EvidenceEntry(items=[EvidenceSource(
            url="https://www.usnews.com/...",
            source_type="us_news",
            claim="MIT physics ranked top 10",
            supports_fields=["school_tier"],
        )]),
    }
    errors = strict_validate(student, cand)
    assert errors == []


# ---- Lower-bound and risk-adjusted are independent ----

def test_lower_bound_subtracts_full_band():
    assert _lower_bound(strength=3.0, band=0.4) == 2.6
    assert _lower_bound(strength=3.0, band=0.8) == 2.2


def test_lower_bound_clamped_at_0():
    assert _lower_bound(strength=0.5, band=2.0) == 0.0


def test_match_result_includes_evidence_breakdown():
    """compute_match populates the new claim-level evidence fields."""
    from phd_matcher.matching.ranker import compute_match
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.collab_with_nas = True   # one extra unsourced claim

    result = compute_match(student, cand)
    assert result.unverified_signals == result.missing_signals + result.unsourced_signals
    # 2 unsourced: school_tier (always required, no evidence) + collab_with_nas
    assert result.unsourced_signals == 2
    assert "collab_with_nas" in result.unsourced_signal_names
    assert "school_tier" in result.unsourced_signal_names
    assert result.lower_bound == round(
        max(0.0, result.application_strength - result.confidence_band), 2
    )
