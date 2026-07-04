"""Tests for match score and application strength (Scoring Design v0.3, post-review)."""

import pytest

from phd_matcher.scoring.admit import (
    application_strength,
    application_strength_from_adj,
    confidence_band_from_coverage,
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


def test_application_strength_school_tier_does_not_affect_strength():
    """Post-roadmap-#5: tier_adj removed. application_strength is now
    `match + pi_adj` (clipped 0–4); school difficulty is layered on top
    via `program_difficulty_penalty` / `difficulty_adjusted_strength`.
    Same match + same pi must give the same strength across all tiers."""
    s_top10,    _ = application_strength(3.0, "top_10",      "normal")
    s_top11_30, _ = application_strength(3.0, "top_11_30",   "normal")
    s_top31_60, _ = application_strength(3.0, "top_31_60",   "normal")
    s_top60p,   _ = application_strength(3.0, "top_60_plus", "normal")
    assert s_top10 == s_top11_30 == s_top31_60 == s_top60p == pytest.approx(3.0)


def test_application_strength_strong_pi_signal():
    """pi_adj=+0.2 is the only adjustment now."""
    s, _ = application_strength(3.0, "top_31_60", "strong")
    assert s == pytest.approx(3.2)


def test_application_strength_shrinking_pi_penalty():
    s, _ = application_strength(3.0, "top_31_60", "shrinking")
    assert s == pytest.approx(2.6)


def test_application_strength_missing_pi_penalty():
    """pi_signal='missing' applies −0.1 (default for unverified)."""
    s, _ = application_strength(3.0, "top_31_60", "missing")
    assert s == pytest.approx(2.9)


def test_application_strength_not_recruiting_zeros_out():
    """Forces strength to 0 regardless of tier or match (unchanged)."""
    s, _ = application_strength(4.0, "top_10", "not_recruiting")
    assert s == 0.0


def test_application_strength_clipped_at_0():
    """Low match + shrinking pi can drive strength below 0 → clipped."""
    s, _ = application_strength(0.3, "top_10", "shrinking")  # 0.3 − 0.4 = −0.1
    assert s == 0.0


def test_application_strength_clipped_at_4():
    """High match + strong pi can exceed 4.0 → clipped."""
    s, _ = application_strength(4.0, "top_60_plus", "strong")  # 4.0 + 0.2 = 4.2
    assert s == 4.0


def test_application_strength_unknown_tier_no_longer_raises():
    """Post-roadmap-#5 the school_tier param is unused (kept for compat).
    Passing an unknown value should not raise — that validation moved
    to `program.program_difficulty_penalty`."""
    s, _ = application_strength(3.0, "top_31_60", "normal")
    assert s == pytest.approx(3.0)


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


# ---- Coverage-fraction band (post-audit): rewards partial sourcing ----

def test_coverage_band_endpoints():
    assert confidence_band_from_coverage(0, 8) == 0.2   # fully sourced
    assert confidence_band_from_coverage(8, 8) == 0.8   # fully unsourced


def test_coverage_band_no_signals_falls_back_narrow():
    assert confidence_band_from_coverage(0, 0) == 0.2


def test_coverage_band_is_monotone_in_coverage():
    # The audit's core fix: across a realistic 8-signal candidate, sourcing
    # each additional signal must NARROW the band (strictly monotone), unlike
    # the absolute-count band which saturated at 0.8 for any >=5 unverified.
    # u = unverified count, from 8 (no coverage) down to 0 (full coverage);
    # the band must strictly narrow as u falls.
    bands = [confidence_band_from_coverage(u, 8) for u in range(8, -1, -1)]
    assert bands == sorted(bands, reverse=True)         # strictly decreasing
    assert len(set(bands)) == len(bands)                # every step distinct


def test_coverage_band_beats_saturation_where_absolute_is_flat():
    # 3-of-8 sourced (5 unverified) must be narrower than 0-of-8 (8 unverified).
    # Under the old absolute band both were a flat 0.8.
    assert confidence_band_from_coverage(5, 8) < confidence_band_from_coverage(8, 8)


def test_from_adj_total_none_uses_legacy_absolute_band():
    # Back-compat: omitting total_count reproduces the absolute-count band.
    _, band = application_strength_from_adj(
        3.0, 0.0, force_zero=False, unverified_count=5, total_count=None
    )
    assert band == 0.8


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
