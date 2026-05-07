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
    """Brand-new candidate with no evidence → max unverified count.

    Total signals per 1-advisor case (post-roadmap-#4):
    1 path + 1 school_tier + 1 research_areas + 4 advisor-influence
    (normalized_collab + nas + placement + active_funding) + 1 pi = 8.
    research_fit is **not** counted when `research_fit_score is None` —
    that's the tie-breaker-only invariant: a missing fit must NOT widen
    the band and indirectly move risk_adjusted_strength.
    """
    student = _student_with_advisor()
    cand = _bare_candidate()
    assert count_unverified_signals(student, cand) == 8


def test_unverified_count_all_verified():
    """Fully sourced candidate → 0 unverified. Evidence given via legacy
    bare sources (back-compat — counts in default mode)."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.research_areas = ["ATLAS", "Higgs"]
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            sources=["https://scholar.google.com/..."],  # legacy back-compat
        ),
    }
    cand.normalized_collab_top20pct = 0.7
    cand.collab_with_nas = True
    cand.grad_placement_quality = 0.8
    cand.active_funding_quality = 0.7
    cand.pi_signal = "normal"
    cand.research_fit_score = 0.85
    cand.evidence = {
        "normalized_collab_top20pct": EvidenceEntry(sources=["https://scholar.google.com/..."]),
        "collab_with_nas": EvidenceEntry(sources=["https://www.nasonline.org/..."]),
        "grad_placement_quality": EvidenceEntry(sources=["https://lab.mit.edu/alumni"]),
        "active_funding_quality": EvidenceEntry(sources=["https://reporter.nih.gov/..."]),
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/people"]),
        "school_tier": EvidenceEntry(sources=["https://www.usnews.com/..."]),
        "research_areas": EvidenceEntry(sources=["https://lab.mit.edu/research"]),
        "research_fit": EvidenceEntry(sources=["https://scholar.google.com/papers"]),
    }
    assert count_unverified_signals(student, cand) == 0


def test_unverified_path_without_sources_counts():
    """Per #1: even non-default path edges without sources are unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(small_team_coauthor_5y=3),  # no sources
    }
    # 1 path (unsourced) + 1 school + 1 research + 4 advisor + 1 pi = 8
    # (research_fit not counted; score is None.)
    assert count_unverified_signals(student, cand) == 8


def test_unverified_pi_signal_non_missing_without_sources():
    """Per #1: pi_signal != 'missing' without evidence sources is unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"  # claim without sources
    # 1 path + 1 school + 1 research + 4 advisor + 1 pi(unsourced) = 8
    assert count_unverified_signals(student, cand) == 8


def test_unverified_pi_signal_non_missing_with_sources_is_verified():
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"
    cand.evidence = {
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/openings"]),
    }
    # 1 path + 1 school + 1 research + 4 advisor + 0 pi(verified) = 7 unverified
    assert count_unverified_signals(student, cand) == 7


def test_unverified_field_strength_default_value_without_sources():
    """Per #1: even default values count as unverified without sources."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # All defaults; path + school + research + 4 advisor + pi = 8
    assert count_unverified_signals(student, cand) == 8


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
    # 0 paths + 1 school + 1 research + 4 advisor + 1 pi = 7
    assert count_unverified_signals(student, cand) == 7


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
    # 0 path(verified-empty) + 1 school + 1 research + 4 advisor + 1 pi = 7
    assert count_unverified_signals(student, cand) == 7


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

    # Tight: pi_signal=normal but everything sourced (all 9 signals incl. research_fit).
    #   strength loss: 0 (normal recruiting baseline)
    #   band benefit: ±0.2 (0 unverified)
    tight = CandidateAdvisor(
        id="tight", name="Prof. Tight", institution="Berkeley",
        school_tier="top_10",
        field="physics", research_areas=["physics"],
        normalized_collab_top20pct=0.7,
        collab_with_nas=False,
        grad_placement_quality=0.6,
        active_funding_quality=0.6,
        pi_signal="normal",
        research_fit_score=0.7,
        evidence={
            "school_tier":                EvidenceEntry(sources=["https://www.usnews.com/..."]),
            "research_areas":             EvidenceEntry(sources=["https://lab.berkeley.edu/research"]),
            "normalized_collab_top20pct": EvidenceEntry(sources=["https://scholar.google.com/..."]),
            "collab_with_nas":            EvidenceEntry(sources=["https://www.nasonline.org/..."]),
            "grad_placement_quality":     EvidenceEntry(sources=["https://lab.berkeley.edu/alumni"]),
            "active_funding_quality":     EvidenceEntry(sources=["https://reporter.nih.gov/..."]),
            "pi_signal":                  EvidenceEntry(sources=["https://lab.berkeley.edu/people"]),
            "research_fit":               EvidenceEntry(sources=["https://scholar.google.com/papers"]),
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
    # 1 path + 1 school + 1 research + 4 advisor + 1 pi = 8
    # (research_fit not counted; score is None.)
    assert cov.total == 8
    # Unsourced: school_tier (always set) + collab_with_nas (set, no ev) = 2
    assert cov.unsourced == 2
    assert "school_tier" in cov.unsourced_names
    assert "collab_with_nas" in cov.unsourced_names
    # Missing: 1 path + 1 research_areas + 3 advisor None + 1 pi = 6
    assert cov.missing == 6


def test_evidence_coverage_all_verified_via_items():
    """Evidence via the structured `items` field, with `supports_fields`
    enforcing per-claim attribution. All 7 signals verified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.research_areas = ["ATLAS", "Higgs"]
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
        "research_areas": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/research",
            source_type="lab_page",
            claim="research focus stated on lab page",
            supports_fields=["research_areas"],
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

    # Add active_funding evidence too (post-roadmap-#3 — required for full coverage)
    cand.active_funding_quality = 0.6
    cand.evidence["active_funding_quality"] = EvidenceEntry(items=[EvidenceSource(
        url="https://reporter.nih.gov/...",
        source_type="nih_reporter",
        claim="active R01 grant 2023–2028",
        supports_fields=["active_funding_quality"],
    )])

    # Add research_fit too (post-roadmap-#4 — also required for full coverage)
    cand.research_fit_score = 0.8
    cand.evidence["research_fit"] = EvidenceEntry(items=[EvidenceSource(
        url="https://scholar.google.com/papers",
        source_type="google_scholar",
        claim="6 of 10 recent papers in same subfield as student",
        supports_fields=["research_fit"],
    )])

    cov = evidence_coverage(student, cand)
    assert cov.unverified == 0
    assert cov.verified == cov.total
    assert cov.total == 9


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


# ---- Per-claim evidence enforcement (post-fourth-pass review) ----

def test_evidence_supports_fields_must_match_in_strict():
    """An EvidenceEntry whose item lists supports_fields=['pi_signal']
    does NOT verify school_tier in strict mode."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.evidence = {
        # The item supports pi_signal, NOT school_tier
        "school_tier": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/people",
            source_type="lab_page",
            claim="lists 3 PhDs",
            supports_fields=["pi_signal"],   # wrong field!
        )]),
    }
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "school_tier" in cov_strict.unsourced_names


def test_strict_mode_rejects_legacy_bare_sources():
    """Default mode accepts legacy bare URLs; strict mode rejects them."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.evidence = {
        "school_tier": EvidenceEntry(sources=["https://www.usnews.com/..."]),
    }

    cov_default = evidence_coverage(student, cand, strict=False)
    cov_strict = evidence_coverage(student, cand, strict=True)
    # Default mode: legacy URL counts → school_tier verified
    assert "school_tier" not in cov_default.unsourced_names
    # Strict mode: legacy URL does NOT count → school_tier unsourced
    assert "school_tier" in cov_strict.unsourced_names


def test_path_edge_per_field_evidence():
    """A PathEdge with two set fields needs evidence for BOTH; one missing
    counts as unsourced even if the other field has its own evidence."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            big_collab_papers_5y=12,
            items=[EvidenceSource(
                url="https://scholar.google.com/...",
                source_type="google_scholar",
                claim="3 small-team papers found",
                supports_fields=["small_team_coauthor_5y"],
                # NOT big_collab_papers_5y
            )],
        ),
    }
    cov = evidence_coverage(student, cand, strict=True)
    # Path is unsourced because big_collab_papers_5y has no covering evidence
    assert "path:adv_001" in cov.unsourced_names


def test_strict_validate_error_for_path_points_to_correct_location():
    """Per fourth-pass review: the strict-mode error for an unsourced path
    should tell the agent to fix paths_to_advisors[id].items, not the
    candidate-level evidence dict."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(small_team_coauthor_5y=3),  # no items, no sources
    }
    errors = strict_validate(student, cand)
    path_error = next((e for e in errors if "path:adv_001" in e), None)
    assert path_error is not None
    # Error must direct the agent at the right field
    assert "paths_to_advisors['adv_001'].items" in path_error
    # Error must NOT direct the agent at the wrong field
    assert "evidence['path:adv_001']" not in path_error
    assert "evidence[\"path:adv_001\"]" not in path_error


def test_strict_rejects_verified_empty_path_with_only_bare_sources():
    """P0 fix: 'searched, found nothing' must use structured items with
    supports_fields=['path:<id>'] in strict mode. Bare sources slip through
    in default mode (legacy) but are rejected as claim-level proof in strict."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            sources=["https://scholar.example/search"],  # bare URL only
            note="searched, found nothing",
        ),
    }
    cov_default = evidence_coverage(student, cand, strict=False)
    cov_strict = evidence_coverage(student, cand, strict=True)
    # Default mode: legacy bare URL counts → path is verified (verified-empty)
    assert "path:adv_001" not in cov_default.unsourced_names
    assert "path:adv_001" not in cov_default.missing_names
    # Strict mode: bare URL doesn't count → unsourced (agent claimed
    # verified-empty without proper format)
    assert "path:adv_001" in cov_strict.unsourced_names


def test_strict_accepts_verified_empty_path_with_supports_fields():
    """The canonical strict-mode pattern: items with
    supports_fields=['path:<id>']."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            items=[EvidenceSource(
                url="https://scholar.example/search?q=Wang+Doe",
                source_type="google_scholar",
                claim="searched 2020–2024: 0 co-authored papers found",
                supports_fields=["path:adv_001"],
            )],
            note="also checked Math Genealogy, no shared lineage",
        ),
    }
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "path:adv_001" not in cov_strict.unsourced_names
    assert "path:adv_001" not in cov_strict.missing_names


def test_strict_validate_path_hint_mentions_path_supports_fields():
    """The strict error should mention the verified-empty pattern."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(sources=["https://example.com/search"]),
    }
    errors = strict_validate(student, cand)
    path_error = next((e for e in errors if "path:adv_001" in e), None)
    assert path_error is not None
    assert "supports_fields=['path:adv_001']" in path_error


# ---- Roadmap-#3: Advisor Influence (A) is a separate dimension ----

def test_advisor_strength_independent_of_connection_path():
    """Verify A doesn't depend on student.current_advisors — it's the
    candidate PI's intrinsic strength, scored independently from C."""
    from phd_matcher.scoring.advisor import advisor_strength

    cand_with_no_path = {
        "normalized_collab_top20pct": 0.8,
        "collab_with_nas": True,
        "grad_placement_quality": 0.7,
        "active_funding_quality": 0.7,
        "pi_signal": "normal",
        "paths_to_advisors": {},   # no path data at all
    }
    a = advisor_strength(cand_with_no_path)
    # A should still be high — PI is strong regardless of path data.
    assert a >= 3.7  # bucket from raw ≥ 0.6


def test_strong_connection_beats_strong_advisor_strength():
    """Connection-first invariant: a candidate with high C and low A
    should still outrank one with low C and high A at top_10 (where C
    weight 0.38 > A weight 0.17)."""
    from phd_matcher.matching.ranker import compute_match
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        EvidenceEntry,
        EvidenceSource,
        PathEdge,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )

    # High C (verified strong path), weak A (no PI prestige signals)
    high_c = CandidateAdvisor(
        id="high_c", name="Prof. C", institution="MIT",
        school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={
            "adv_001": PathEdge(
                small_team_coauthor_5y=5,  # → strength 1.0 → C = 4.0
                items=[EvidenceSource(
                    url="https://scholar.google.com/...",
                    source_type="google_scholar",
                    claim="5 small-team papers",
                    supports_fields=["small_team_coauthor_5y"],
                )],
            ),
        },
        # A signals all None → A = bucket 2.3
    )

    # Low C (no path), high A (all signals strong + verified)
    high_a = CandidateAdvisor(
        id="high_a", name="Prof. A", institution="Stanford",
        school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={},  # no path → C = 2.3
        normalized_collab_top20pct=0.95,
        collab_with_nas=True,
        grad_placement_quality=0.9,
        active_funding_quality=0.9,
        pi_signal="strong",
        evidence={
            "normalized_collab_top20pct": EvidenceEntry(items=[EvidenceSource(
                url="https://scholar.google.com/...", source_type="google_scholar",
                claim="h_index=50", supports_fields=["normalized_collab_top20pct"])]),
            "collab_with_nas": EvidenceEntry(items=[EvidenceSource(
                url="https://www.nasonline.org/...", source_type="nas",
                claim="NAS member", supports_fields=["collab_with_nas"])]),
            "grad_placement_quality": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.stanford.example/alumni", source_type="lab_page",
                claim="80% faculty placements",
                supports_fields=["grad_placement_quality"])]),
            "active_funding_quality": EvidenceEntry(items=[EvidenceSource(
                url="https://reporter.nih.gov/...", source_type="nih_reporter",
                claim="active R01", supports_fields=["active_funding_quality"])]),
            "pi_signal": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.stanford.example/people", source_type="lab_page",
                claim="3 new PhDs in 2024", supports_fields=["pi_signal"])]),
            "school_tier": EvidenceEntry(items=[EvidenceSource(
                url="https://www.usnews.com/...", source_type="us_news",
                claim="Stanford physics top 10",
                supports_fields=["school_tier"])]),
            "research_areas": EvidenceEntry(items=[EvidenceSource(
                url="https://physics.stanford.example/...", source_type="faculty_page",
                claim="research focus stated on faculty page",
                supports_fields=["research_areas"])]),
        },
    )

    r_c = compute_match(student, high_c)
    r_a = compute_match(student, high_a)
    # high_c: C=4.0, A≈2.3 (default). At top_10: 0.38·4 + 0.17·2.3 = 1.52 + 0.39
    # high_a: C=2.3, A≈3.7+ (all sourced strong). At top_10: 0.38·2.3 + 0.17·3.7+
    # The C contribution differential (≈0.65) outweighs A differential (≈0.24).
    assert r_c.match_score > r_a.match_score, (
        f"connection-first invariant violated: high_c.match={r_c.match_score}, "
        f"high_a.match={r_a.match_score}"
    )


# ---- Roadmap-#4: Research fit as tie-breaker ----

def test_research_fit_breaks_tie_when_risk_adjusted_strength_equal():
    """Two candidates at the same risk_adjusted_strength: the one with
    higher research_fit_score ranks first."""
    from phd_matcher.matching.ranker import compute_match, rank_advisors
    from phd_matcher.models import CandidateAdvisor, StudentProfile

    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
    )

    base = dict(
        institution="MIT", school_tier="top_10", field="physics",
        research_areas=["physics"],
    )

    fit_high = CandidateAdvisor(id="fit_high", name="A", **base, research_fit_score=0.9)
    fit_low = CandidateAdvisor(id="fit_low", name="B", **base, research_fit_score=0.3)

    # Both candidates have identical scoring inputs except research_fit_score
    # → identical risk_adjusted_strength → fit breaks the tie.
    r_high = compute_match(student, fit_high)
    r_low = compute_match(student, fit_low)
    assert r_high.risk_adjusted_strength == r_low.risk_adjusted_strength

    ranked = rank_advisors(student, [fit_low, fit_high], top_k=2)
    assert ranked[0].candidate.id == "fit_high"
    assert ranked[1].candidate.id == "fit_low"


def test_research_fit_cannot_beat_clearly_stronger_risk_adjusted():
    """Research fit is a tie-breaker, NOT a pillar: a candidate with
    higher risk_adjusted_strength always outranks a peer with much higher
    research_fit_score but lower strength. The connection-first thesis
    is preserved."""
    from phd_matcher.matching.ranker import compute_match, rank_advisors
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        EvidenceSource,
        PathEdge,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )

    # Strong-but-low-fit: real connection (C=4.0), no research_fit_score
    strong_low_fit = CandidateAdvisor(
        id="strong_low_fit", name="A",
        institution="MIT", school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={
            "adv_001": PathEdge(
                small_team_coauthor_5y=5,
                items=[EvidenceSource(
                    url="https://scholar.google.com/...",
                    source_type="google_scholar",
                    claim="5 small-team papers",
                    supports_fields=["small_team_coauthor_5y"],
                )],
            ),
        },
        research_fit_score=None,  # didn't compute
    )

    # Weak-but-perfect-fit: no path, but research_fit_score = 1.0
    weak_perfect_fit = CandidateAdvisor(
        id="weak_perfect_fit", name="B",
        institution="MIT", school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={},
        research_fit_score=1.0,  # perfect fit
    )

    r_strong = compute_match(student, strong_low_fit)
    r_weak = compute_match(student, weak_perfect_fit)
    # The strong candidate must have a higher risk_adjusted_strength —
    # research_fit is irrelevant to that comparison.
    assert r_strong.risk_adjusted_strength > r_weak.risk_adjusted_strength

    ranked = rank_advisors(student, [weak_perfect_fit, strong_low_fit], top_k=2)
    assert ranked[0].candidate.id == "strong_low_fit"


def test_research_fit_with_no_score_sorts_below_with_score():
    """When risk_adjusted_strength ties, a candidate with research_fit_score
    set ranks above one with None (None → -inf in sort key)."""
    from phd_matcher.matching.ranker import rank_advisors
    from phd_matcher.models import CandidateAdvisor, StudentProfile

    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS",
    )

    base = dict(
        institution="MIT", school_tier="top_10", field="physics",
        research_areas=["physics"],
    )

    has_fit = CandidateAdvisor(id="has_fit", name="A", **base, research_fit_score=0.05)
    no_fit = CandidateAdvisor(id="no_fit", name="B", **base, research_fit_score=None)

    ranked = rank_advisors(student, [no_fit, has_fit], top_k=2)
    assert ranked[0].candidate.id == "has_fit"


def test_research_fit_strict_evidence_requires_supports_fields():
    """Strict mode: a non-None research_fit_score without
    `supports_fields=['research_fit']` evidence is unsourced."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.research_fit_score = 0.7   # claim without evidence
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "research_fit" in cov_strict.unsourced_names


def test_research_fit_strict_evidence_passes_with_correct_supports_fields():
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.research_fit_score = 0.7
    cand.evidence = {
        "research_fit": EvidenceEntry(items=[EvidenceSource(
            url="https://scholar.google.com/papers",
            source_type="google_scholar",
            claim="6 of 10 recent papers in subfield",
            supports_fields=["research_fit"],
        )]),
    }
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "research_fit" not in cov_strict.unsourced_names


def test_research_fit_none_does_not_appear_in_coverage():
    """Mechanism check for the tie-breaker-only invariant: when
    `research_fit_score is None`, `research_fit` must not appear in
    coverage at all — not in `total`, not in `missing_names`, not in
    `unsourced_names`. Otherwise it would feed back into the band."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # research_fit_score defaults to None
    cov = evidence_coverage(student, cand)
    assert "research_fit" not in cov.missing_names
    assert "research_fit" not in cov.unsourced_names
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "research_fit" not in cov_strict.missing_names
    assert "research_fit" not in cov_strict.unsourced_names


def test_research_fit_none_does_not_widen_band():
    """Consequence check: two otherwise-identical candidates — one with
    research_fit_score sourced, one with None — must produce the same
    `confidence_band` and `risk_adjusted_strength`. If `None` had been
    folded into coverage as a missing signal, the no-fit candidate would
    have one extra unverified signal, get a wider band, and a lower
    risk_adjusted_strength — which would let the tie-breaker indirectly
    move the main sort key."""
    from phd_matcher.matching.ranker import compute_match
    student = _student_with_advisor()

    sourced = {
        "school_tier": EvidenceEntry(items=[EvidenceSource(
            url="https://www.usnews.com/...", source_type="us_news",
            claim="MIT physics top 10", supports_fields=["school_tier"])]),
        "research_areas": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/research", source_type="lab_page",
            claim="research focus", supports_fields=["research_areas"])]),
        "normalized_collab_top20pct": EvidenceEntry(items=[EvidenceSource(
            url="https://scholar.google.com/...", source_type="google_scholar",
            claim="h_index", supports_fields=["normalized_collab_top20pct"])]),
        "collab_with_nas": EvidenceEntry(items=[EvidenceSource(
            url="https://www.nasonline.org/...", source_type="nas",
            claim="NAS member", supports_fields=["collab_with_nas"])]),
        "grad_placement_quality": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/alumni", source_type="lab_page",
            claim="placement record", supports_fields=["grad_placement_quality"])]),
        "active_funding_quality": EvidenceEntry(items=[EvidenceSource(
            url="https://reporter.nih.gov/...", source_type="nih_reporter",
            claim="active R01", supports_fields=["active_funding_quality"])]),
        "pi_signal": EvidenceEntry(items=[EvidenceSource(
            url="https://lab.mit.edu/people", source_type="lab_page",
            claim="recruiting", supports_fields=["pi_signal"])]),
    }
    common_path = {"adv_001": PathEdge(
        small_team_coauthor_5y=3,
        items=[EvidenceSource(
            url="https://scholar.google.com/...",
            source_type="google_scholar",
            claim="3 small-team papers",
            supports_fields=["small_team_coauthor_5y"],
        )],
    )}
    base = dict(
        institution="MIT", school_tier="top_10", field="physics",
        research_areas=["ATLAS", "Higgs"],
        normalized_collab_top20pct=0.7, collab_with_nas=True,
        grad_placement_quality=0.6, active_funding_quality=0.6,
        pi_signal="normal", paths_to_advisors=common_path,
    )

    fit_none = CandidateAdvisor(
        id="fit_none", name="A", **base,
        research_fit_score=None,
        evidence=sourced,
    )
    fit_set_evidence = dict(sourced)
    fit_set_evidence["research_fit"] = EvidenceEntry(items=[EvidenceSource(
        url="https://scholar.google.com/papers", source_type="google_scholar",
        claim="6 of 10 in subfield", supports_fields=["research_fit"])])
    fit_set = CandidateAdvisor(
        id="fit_set", name="B", **base,
        research_fit_score=0.7,
        evidence=fit_set_evidence,
    )

    r_none = compute_match(student, fit_none)
    r_set = compute_match(student, fit_set)

    # Both candidates fully sourced; fit-set has +1 verified signal but
    # the same 0 unverified count and same band.
    assert r_none.unverified_signals == 0
    assert r_set.unverified_signals == 0
    assert r_none.confidence_band == r_set.confidence_band
    assert r_none.risk_adjusted_strength == r_set.risk_adjusted_strength


def test_research_fit_axes_value_out_of_bounds_rejected():
    """Pydantic must reject `research_fit_axes` values outside [0, 1] —
    keeps the tie-breaker numerically meaningful and prevents silent
    distortion."""
    with pytest.raises(ValidationError):
        CandidateAdvisor(
            id="c1", name="X", institution="MIT",
            school_tier="top_10", field="physics",
            research_fit_axes={"subfield": 2.0},
        )
    with pytest.raises(ValidationError):
        CandidateAdvisor(
            id="c1", name="X", institution="MIT",
            school_tier="top_10", field="physics",
            research_fit_axes={"subfield": -0.1},
        )


def test_validate_research_fit_axes_warns_on_unknown_axis_key():
    """`validate_research_fit_axes` warns when a candidate's axis keys
    don't match the active FieldProfile — catches drift like a CS-field
    candidate using a physics-only axis name."""
    from phd_matcher.matching.ranker import validate_research_fit_axes
    from phd_matcher.models import FieldProfile

    profile = FieldProfile(
        id="physics",
        display_name="Physics",
        venue_system="journal_first",
        research_fit_axes=["subfield", "experiment_vs_theory"],
    )
    cand_ok = CandidateAdvisor(
        id="ok", name="A", institution="MIT",
        school_tier="top_10", field="physics",
        research_fit_axes={"subfield": 0.8},
    )
    cand_bad = CandidateAdvisor(
        id="bad", name="B", institution="MIT",
        school_tier="top_10", field="physics",
        research_fit_axes={"detector": 0.9, "subfield": 0.5},
    )

    warnings = validate_research_fit_axes([cand_ok, cand_bad], field_profile=profile)
    assert len(warnings) == 1
    assert "candidate=bad" in warnings[0]
    assert "detector" in warnings[0]
    assert "physics" in warnings[0]

    # No profile / empty axes → no warnings (the axis-key check is opt-in
    # and only meaningful when the profile declares which axes apply).
    assert validate_research_fit_axes([cand_bad], field_profile=None) == []
    profile_no_axes = FieldProfile(
        id="other", display_name="Other", venue_system="mixed",
    )
    assert validate_research_fit_axes([cand_bad], field_profile=profile_no_axes) == []


def test_explainer_filters_sources_per_claim():
    """Per fourth-pass review: an item supporting only small_team should
    NOT appear after the big_collab claim in the explanation."""
    from phd_matcher.matching.explainer import explain_match
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            big_collab_papers_5y=12,
            items=[
                EvidenceSource(
                    url="https://scholar.google.com/small",
                    source_type="google_scholar",
                    claim="3 small-team papers",
                    supports_fields=["small_team_coauthor_5y"],
                ),
                EvidenceSource(
                    url="https://inspirehep.net/big",
                    source_type="inspire",
                    claim="12 ATLAS bulk papers",
                    supports_fields=["big_collab_papers_5y"],
                ),
            ],
        ),
    }
    explanation = explain_match(student, cand)

    # The small-team URL should appear AFTER the small-team claim, not the big-collab one.
    # We can't easily test sequence, but we can test that BOTH claims got their own URL.
    assert "scholar.google.com/small" in explanation
    assert "inspirehep.net/big" in explanation
    # And critically, the small-team URL doesn't contaminate the big-collab claim:
    # the big-collab line must reference the big-collab URL, not the scholar URL.
    big_collab_line_idx = explanation.find("big-collab paper")
    next_section_idx = explanation.find("·", big_collab_line_idx)
    big_collab_line = explanation[big_collab_line_idx:next_section_idx]
    assert "inspirehep.net/big" in big_collab_line
    assert "scholar.google.com/small" not in big_collab_line
