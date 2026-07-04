"""Tests for publication scoring (Scoring Design v0.3 §2)."""

import pytest

from phd_matcher.scoring.pub import aggregate_papers, paper_score, pub_score

# ---- Single paper, position decay ----

def test_top_tier_first_author():
    assert paper_score(1, 1) == pytest.approx(4.0)


def test_top_tier_second_author():
    assert paper_score(1, 2) == pytest.approx(3.9)


def test_top_tier_third_author():
    assert paper_score(1, 3) == pytest.approx(3.75)


def test_top_tier_fourth_author():
    assert paper_score(1, 4) == pytest.approx(3.55)


def test_top_tier_fifth_author_big_collab_floor():
    # min(3.5, 3.55) = 3.5 — keeps the big-collab credit at 3.5
    assert paper_score(1, 5) == pytest.approx(3.5)


def test_top_tier_hundredth_author():
    # 5+ rule applies for any position >= 5
    assert paper_score(1, 100) == pytest.approx(3.5)


def test_tier_2_first_author():
    assert paper_score(2, 1) == pytest.approx(3.7)


def test_tier_3_first_author():
    assert paper_score(3, 1) == pytest.approx(3.3)


def test_tier_3_fifth_author_no_inversion():
    # Tier 3 baseline 3.3, 4-author = 2.85
    # 5+ rule: min(3.5, 2.85) = 2.85 — no reverse boost in low tier
    assert paper_score(3, 5) == pytest.approx(2.85)


def test_tier_4_fifth_author_no_inversion():
    # Tier 4 baseline 2.8, 4-author = 2.35
    # 5+ rule: min(3.5, 2.35) = 2.35
    assert paper_score(4, 5) == pytest.approx(2.35)


def test_retracted_paper_zero():
    assert paper_score(0, 1) == 0.0
    assert paper_score(0, 5) == 0.0


def test_cross_disciplinary_S_tier():
    # Tier S should be 4.0 baseline like Tier 1
    assert paper_score("S", 1) == pytest.approx(4.0)


def test_invalid_tier_raises():
    with pytest.raises(ValueError):
        paper_score(99, 1)


def test_invalid_position_raises():
    with pytest.raises(ValueError):
        paper_score(1, 0)


# ---- Aggregation ----

def test_aggregate_no_papers_floor():
    assert aggregate_papers([]) == pytest.approx(2.0)


def test_no_paper_floor_below_any_real_paper():
    # Honesty invariant: reporting a real (even weak) paper must never score
    # below reporting nothing. tier-5 first-author = 2.3 > NO_PAPER_FLOOR.
    from phd_matcher.scoring.pub import NO_PAPER_FLOOR, TIER_BASELINE
    assert NO_PAPER_FLOOR <= min(v for v in TIER_BASELINE.values() if v > 0)


def test_aggregate_one_paper():
    assert aggregate_papers([3.5]) == pytest.approx(3.5)


def test_aggregate_two_papers():
    assert aggregate_papers([4.0, 3.0]) == pytest.approx(0.7 * 4.0 + 0.3 * 3.0)


def test_aggregate_three_papers():
    assert aggregate_papers([4.0, 3.5, 3.0]) == pytest.approx(
        0.5 * 4.0 + 0.3 * 3.5 + 0.2 * 3.0
    )


def test_aggregate_more_than_three_only_top_3_used():
    expected = 0.5 * 4.0 + 0.3 * 3.5 + 0.2 * 3.0
    assert aggregate_papers([4.0, 3.5, 3.0, 2.5, 2.0]) == pytest.approx(expected)


def test_aggregate_unsorted_input():
    expected = 0.5 * 4.0 + 0.3 * 3.5 + 0.2 * 3.0
    assert aggregate_papers([2.0, 4.0, 3.0, 3.5]) == pytest.approx(expected)


def test_aggregate_is_convex_average_by_design():
    # Pinned: adding a weaker paper lowers the top-weighted average. This
    # is intentional (consistency over one spike; anti-CV-padding), not a bug.
    assert aggregate_papers([4.0, 2.3]) < aggregate_papers([4.0])


# ---- pub_score end-to-end ----

def test_pub_score_no_papers_returns_floor():
    assert pub_score([]) == pytest.approx(2.0)


def test_pub_score_full_pipeline():
    papers = [
        {"journal_tier": 1, "author_position": 1},  # 4.0
        {"journal_tier": 2, "author_position": 2},  # 3.6
    ]
    expected = 0.7 * 4.0 + 0.3 * 3.6
    assert pub_score(papers) == pytest.approx(expected)


def test_pub_score_atlas_paper():
    """Real-world test: HEP undergrad with PRD position 312 + PRL position 456."""
    papers = [
        {"journal_tier": 3, "author_position": 312},  # PRD, 5+ → min(3.5, 2.85) = 2.85
        {"journal_tier": 1, "author_position": 456},  # PRL, 5+ → min(3.5, 3.55) = 3.5
    ]
    # best=3.5, 2nd=2.85
    expected = 0.7 * 3.5 + 0.3 * 2.85
    assert pub_score(papers) == pytest.approx(expected)


# ---- Paper status weight (post-review) ----

def test_paper_status_published_full_credit():
    s = paper_score(1, 1, status="published")
    assert s == pytest.approx(4.0)


def test_paper_status_accepted_full_credit():
    s = paper_score(1, 1, status="accepted")
    assert s == pytest.approx(4.0)


def test_paper_status_submitted_partial_credit():
    s = paper_score(1, 1, status="submitted")
    assert s == pytest.approx(4.0 * 0.7)


def test_paper_status_preprint_partial_credit():
    s = paper_score(2, 1, status="preprint")
    assert s == pytest.approx(3.7 * 0.7)


def test_paper_status_in_prep_low_credit():
    s = paper_score(1, 1, status="in_prep")
    assert s == pytest.approx(4.0 * 0.3)


def test_paper_status_unknown_raises():
    """Per code review #2: unknown status must NOT silently default to 1.0."""
    with pytest.raises(ValueError):
        paper_score(1, 1, status="probably_publishable")


def test_pub_score_mixes_statuses():
    """Mixed-status portfolio aggregates with weighted scores."""
    papers = [
        {"journal_tier": 1, "author_position": 1, "status": "published"},  # 4.0
        {"journal_tier": 1, "author_position": 1, "status": "submitted"},  # 4.0 * 0.7 = 2.8
    ]
    # best=4.0 (published), 2nd=2.8 (submitted)
    expected = 0.7 * 4.0 + 0.3 * 2.8
    assert pub_score(papers) == pytest.approx(expected)


def test_pub_score_in_prep_dominated_by_published():
    """An in-prep top-tier paper (4.0 * 0.3 = 1.2) shouldn't out-rank a
    published mid-tier paper (3.3) in the top-1 slot."""
    papers = [
        {"journal_tier": 3, "author_position": 1, "status": "published"},   # 3.3
        {"journal_tier": 1, "author_position": 1, "status": "in_prep"},     # 1.2
    ]
    # Sorted desc: [3.3, 1.2]. Aggregated as 2 papers.
    expected = 0.7 * 3.3 + 0.3 * 1.2
    assert pub_score(papers) == pytest.approx(expected)


# ---- Publication v2 (Sprint-2-c2) ---------------------------------------

from pathlib import Path  # noqa: E402

from phd_matcher.data.loaders import load_field_profile  # noqa: E402
from phd_matcher.scoring.pub import (  # noqa: E402
    BIG_COLLAB_GUARDED_FLOOR,
    CONSORTIUM_NO_EVIDENCE_FACTOR,
    contribution_bonus,
    recency_weight,
    validate_paper_contributions,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_recency_weight_recent():
    """v2: paper from current year or within 2y → no recency discount."""
    assert recency_weight(2026, current_year=2026) == 1.0
    assert recency_weight(2024, current_year=2026) == 1.0


def test_recency_weight_mid():
    """v2: 3–5y old → 0.95 multiplier."""
    assert recency_weight(2022, current_year=2026) == 0.95
    assert recency_weight(2021, current_year=2026) == 0.95


def test_recency_weight_old():
    """v2: >5y old → 0.85 multiplier."""
    assert recency_weight(2018, current_year=2026) == 0.85
    assert recency_weight(2010, current_year=2026) == 0.85


def test_recency_weight_none_is_neutral():
    """v2: year=None → 1.0 (no penalty for unspecified). Future years
    (data error) clamp to 1.0."""
    assert recency_weight(None) == 1.0
    assert recency_weight(2030, current_year=2026) == 1.0


def test_recency_decay_in_paper_score():
    """End-to-end: a 10-year-old tier-1 first-author paper scores below
    a current-year equivalent."""
    recent = paper_score(1, 1, year=2026, current_year=2026)
    old = paper_score(1, 1, year=2014, current_year=2026)
    assert recent == pytest.approx(4.0)
    assert old == pytest.approx(4.0 * 0.85)
    assert recent > old


def test_contribution_bonus_lead_analysis():
    """v2: verified lead_analysis adds +0.15."""
    assert contribution_bonus("lead_analysis", has_evidence=True) == 0.15


def test_contribution_bonus_unclear_no_bonus():
    """v2: contribution_role='unclear' → 0.0 even with evidence."""
    assert contribution_bonus("unclear", has_evidence=True) == 0.0


def test_contribution_bonus_no_evidence_no_bonus():
    """v2: a contribution role without evidence is informational only."""
    assert contribution_bonus("lead_analysis", has_evidence=False) == 0.0
    assert contribution_bonus("method_developer", has_evidence=False) == 0.0


def test_paper_score_with_contribution_bonus():
    """End-to-end: a tier-1 4th-author paper (3.55) with verified
    lead_analysis (+0.15) bumps to 3.70."""
    score = paper_score(
        1, 4,
        contribution_role="lead_analysis",
        has_contribution_evidence=True,
    )
    assert score == pytest.approx(3.70)


def test_paper_score_contribution_capped_at_baseline():
    """v2: contribution bonus cannot exceed the tier baseline."""
    # tier 1 first author = 4.0; +0.15 lead_analysis would be 4.15 → capped at 4.0
    score = paper_score(
        1, 1,
        contribution_role="lead_analysis",
        has_contribution_evidence=True,
    )
    assert score == pytest.approx(4.0)


def test_big_collab_guardrail_caps_unverified_consortium_member():
    """v2: a tier-1 paper at position 1 (via author_role) but with 312
    total authors and no verified contribution → capped at
    BIG_COLLAB_GUARDED_FLOOR."""
    physics = load_field_profile(DATA_DIR, "physics")
    # Without the guardrail, role-override + status would compute to 4.0.
    # With the guardrail (total_authors=312 > physics threshold 10), capped.
    score = paper_score(
        1, 312,
        author_role="middle",
        total_authors=312,
        field_profile=physics,
    )
    assert score <= BIG_COLLAB_GUARDED_FLOOR


def test_big_collab_guardrail_bypassed_by_verified_contribution():
    """v2: same big-collab paper, but with verified lead_analysis →
    full 1st-author equivalent score (no guardrail cap)."""
    physics = load_field_profile(DATA_DIR, "physics")
    score = paper_score(
        1, 312,
        author_role="middle",
        total_authors=312,
        field_profile=physics,
        contribution_role="lead_analysis",
        has_contribution_evidence=True,
    )
    # 5+ rule: min(3.5, baseline-0.45) = 3.5; +0.15 bonus = 3.65
    assert score == pytest.approx(3.65)


def test_consortium_role_capped_without_evidence():
    """v2: author_role='consortium' caps at 0.45 × baseline without
    verified contribution."""
    score = paper_score(
        1, 100,
        author_role="consortium",
        total_authors=200,
    )
    # 0.45 × 4.0 = 1.8 (could be lower from base, but cap is the limit)
    assert score <= CONSORTIUM_NO_EVIDENCE_FACTOR * 4.0


def test_consortium_role_rescued_by_verified_contribution():
    """v2: a consortium-role paper with verified contribution is no longer
    capped at 0.45×baseline — the contribution evidence rescues it."""
    score = paper_score(
        1, 100,
        author_role="consortium",
        total_authors=200,
        contribution_role="lead_analysis",
        has_contribution_evidence=True,
    )
    # No 0.45×baseline cap; falls back to position-based 5+ floor (3.5) + bonus.
    assert score > CONSORTIUM_NO_EVIDENCE_FACTOR * 4.0


def test_field_status_override_cs_preprint():
    """v2: cs.yaml sets preprint=0.85 (was default 0.7) — arXiv preprints
    in CS carry near-publication weight."""
    cs = load_field_profile(DATA_DIR, "cs")
    score = paper_score(1, 1, status="preprint", field_profile=cs)
    assert score == pytest.approx(4.0 * 0.85)


def test_field_status_override_biology_preprint():
    """v2: biology.yaml sets preprint=0.75 (was default 0.7) — bioRxiv
    preprints carry slightly more weight than the cross-field default."""
    bio = load_field_profile(DATA_DIR, "biology")
    score = paper_score(1, 1, status="preprint", field_profile=bio)
    assert score == pytest.approx(4.0 * 0.75)


def test_field_status_override_math_preprint_unchanged():
    """v2: math.yaml's existing preprint=0.9 override is preserved."""
    math = load_field_profile(DATA_DIR, "math")
    score = paper_score(1, 1, status="preprint", field_profile=math)
    assert score == pytest.approx(4.0 * 0.9)


def test_validate_paper_contributions_warns_on_unverified():
    """v2: contribution_role set without contribution_evidence → warning."""
    papers = [
        {
            "journal_tier": 1, "author_position": 1,
            "contribution_role": "lead_analysis",
            # contribution_evidence missing → bonus dropped
        },
        {
            "journal_tier": 1, "author_position": 2,
            "contribution_role": "method_developer",
            "contribution_evidence": [{"url": "...", "source_type": "paper",
                                       "claim": "...", "supports_fields": []}],
        },
    ]
    warnings = validate_paper_contributions(papers)
    assert len(warnings) == 1
    assert "paper[0]" in warnings[0]
    assert "lead_analysis" in warnings[0]


def test_pub_score_threads_year_through():
    """v2: pub_score passes year + current_year into paper_score so
    recency decay applies in the aggregated portfolio."""
    papers_recent = [{"journal_tier": 1, "author_position": 1, "year": 2026}]
    papers_old = [{"journal_tier": 1, "author_position": 1, "year": 2014}]
    s_recent = pub_score(papers_recent, current_year=2026)
    s_old = pub_score(papers_old, current_year=2026)
    assert s_recent > s_old
    assert s_recent == pytest.approx(4.0)
    assert s_old == pytest.approx(4.0 * 0.85)
