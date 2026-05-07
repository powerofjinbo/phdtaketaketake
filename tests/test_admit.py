"""Tests for match score and application strength (Scoring Design v0.3, post-review)."""

import pytest

from phd_matcher.scoring.admit import (
    application_strength,
    confidence_band_from_unverified,
    match_score,
    strength_label,
)


def test_match_score_top_10_weights():
    """Post-roadmap-#3: 5-pillar CAPEG. C=0.38, A=0.17, P=0.27, E=0.10, G=0.08."""
    m = match_score(c=4.0, a=3.0, p=3.5, e=3.0, g=3.5, school_tier="top_10")
    expected = 0.38 * 4.0 + 0.17 * 3.0 + 0.27 * 3.5 + 0.10 * 3.0 + 0.08 * 3.5
    assert m == pytest.approx(expected)


def test_match_score_top_60_plus_gpa_weighted_more():
    """top_60_plus: G=0.27 — the largest non-C/P weight; A is bounded at 0.12."""
    m = match_score(c=4.0, a=3.0, p=3.5, e=3.0, g=3.5, school_tier="top_60_plus")
    expected = 0.25 * 4.0 + 0.12 * 3.0 + 0.18 * 3.5 + 0.18 * 3.0 + 0.27 * 3.5
    assert m == pytest.approx(expected)


def test_match_score_invalid_tier_raises():
    with pytest.raises(ValueError):
        match_score(3, 3, 3, 3, 3, "top_999")


def test_tier_weights_sum_to_one():
    """Sanity: 5-pillar weights must sum to 1.0 within each tier."""
    from phd_matcher.scoring.admit import TIER_WEIGHTS

    for tier, ws in TIER_WEIGHTS.items():
        total = sum(ws.values())
        assert total == pytest.approx(1.0), f"{tier} weights sum to {total}, not 1.0"


def test_a_does_not_outrank_c_in_any_tier():
    """The user's explicit invariant: A is bounded so it doesn't compete
    with C. Under no tier does Advisor influence weight exceed Connection.

    (At top_60_plus, G > C — that's the established 'lower tier weights
    GPA more' rule from the original CPEG calibration. But A specifically
    must never beat C, or the connection-first thesis dilutes.)"""
    from phd_matcher.scoring.admit import TIER_WEIGHTS

    for tier, ws in TIER_WEIGHTS.items():
        assert ws["C"] > ws["A"], (
            f"{tier}: C={ws['C']} but A={ws['A']} — A would outrank C, "
            f"diluting connection-first."
        )


def test_application_strength_top_10_penalty():
    # match=3.5, top_10 (-1.0), normal (0.0) → 2.5
    s, _ = application_strength(3.5, "top_10", "normal")
    assert s == pytest.approx(2.5)


def test_application_strength_top_11_30_penalty():
    s, _ = application_strength(3.5, "top_11_30", "normal")
    assert s == pytest.approx(3.0)


def test_application_strength_top_60_plus_bonus():
    s, _ = application_strength(3.0, "top_60_plus", "normal")
    assert s == pytest.approx(3.4)


def test_application_strength_strong_pi_signal():
    s, _ = application_strength(3.0, "top_31_60", "strong")
    assert s == pytest.approx(3.2)


def test_application_strength_shrinking_pi_penalty():
    s, _ = application_strength(3.0, "top_31_60", "shrinking")
    assert s == pytest.approx(2.6)


def test_application_strength_not_recruiting_zeros_out():
    s, _ = application_strength(4.0, "top_10", "not_recruiting")
    assert s == 0.0


def test_application_strength_perfect_at_top10_is_match_not_safe():
    # match=4.0, top_10 (-1.0), strong (+0.2) → 3.2 (Match)
    s, _ = application_strength(4.0, "top_10", "strong")
    assert s == pytest.approx(3.2)


def test_application_strength_clipped_at_0():
    s, _ = application_strength(0.5, "top_10", "shrinking")
    assert s == 0.0


def test_application_strength_clipped_at_4():
    s, _ = application_strength(4.0, "top_60_plus", "strong")
    assert s == 4.0


def test_confidence_band_all_verified():
    assert confidence_band_from_unverified(0) == 0.2


def test_confidence_band_few_unverified():
    assert confidence_band_from_unverified(1) == 0.4
    assert confidence_band_from_unverified(2) == 0.4


def test_confidence_band_some_unverified():
    assert confidence_band_from_unverified(3) == 0.6
    assert confidence_band_from_unverified(4) == 0.6


def test_confidence_band_mostly_unverified():
    assert confidence_band_from_unverified(5) == 0.8
    assert confidence_band_from_unverified(99) == 0.8


def test_strength_labels():
    assert strength_label(3.6) == "Safe"
    assert strength_label(3.2) == "Match"
    assert strength_label(2.7) == "Target"
    assert strength_label(2.2) == "Reach"
    assert strength_label(1.5) == "Far Reach"


def test_application_strength_returns_band():
    """When more signals are unverified, the band widens."""
    _, band_full = application_strength(3.0, "top_31_60", "normal", unverified_count=0)
    _, band_partial = application_strength(3.0, "top_31_60", "normal", unverified_count=3)
    _, band_thin = application_strength(3.0, "top_31_60", "normal", unverified_count=10)
    assert band_full < band_partial < band_thin
