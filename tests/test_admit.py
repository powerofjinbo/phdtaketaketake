"""Tests for match score and admission likelihood (Scoring Design v0.3 §6, §7)."""

import pytest

from phd_matcher.scoring.admit import (
    admit_likelihood,
    confidence_band,
    likelihood_label,
    match_score,
)


def test_match_score_top_10_weights():
    # Top 10: 0.45·C + 0.30·P + 0.15·E + 0.10·G
    m = match_score(c=4.0, p=3.5, e=3.0, g=3.5, school_tier="top_10")
    expected = 0.45 * 4.0 + 0.30 * 3.5 + 0.15 * 3.0 + 0.10 * 3.5
    assert m == pytest.approx(expected)


def test_match_score_top_60_plus_gpa_weighted_more():
    # Top 60+: 0.30·C + 0.20·P + 0.20·E + 0.30·G
    m = match_score(c=4.0, p=3.5, e=3.0, g=3.5, school_tier="top_60_plus")
    expected = 0.30 * 4.0 + 0.20 * 3.5 + 0.20 * 3.0 + 0.30 * 3.5
    assert m == pytest.approx(expected)


def test_match_score_invalid_tier_raises():
    with pytest.raises(ValueError):
        match_score(3, 3, 3, 3, "top_999")


def test_admit_likelihood_top_10_penalty():
    # match=3.5, top_10 (-1.0), normal pi (0.0) → 2.5
    likelihood, _ = admit_likelihood(3.5, "top_10", "normal")
    assert likelihood == pytest.approx(2.5)


def test_admit_likelihood_top_11_30_penalty():
    # match=3.5, top_11_30 (-0.5), normal (0.0) → 3.0
    likelihood, _ = admit_likelihood(3.5, "top_11_30", "normal")
    assert likelihood == pytest.approx(3.0)


def test_admit_likelihood_top_60_plus_bonus():
    # match=3.0, top_60_plus (+0.4), normal (0.0) → 3.4
    likelihood, _ = admit_likelihood(3.0, "top_60_plus", "normal")
    assert likelihood == pytest.approx(3.4)


def test_admit_likelihood_strong_pi_signal():
    # match=3.0, top_31_60 (0.0), strong (+0.2) → 3.2
    likelihood, _ = admit_likelihood(3.0, "top_31_60", "strong")
    assert likelihood == pytest.approx(3.2)


def test_admit_likelihood_shrinking_pi_penalty():
    # match=3.0, top_31_60 (0.0), shrinking (-0.4) → 2.6
    likelihood, _ = admit_likelihood(3.0, "top_31_60", "shrinking")
    assert likelihood == pytest.approx(2.6)


def test_admit_likelihood_not_recruiting_zeros_out():
    likelihood, _ = admit_likelihood(4.0, "top_10", "not_recruiting")
    assert likelihood == 0.0


def test_admit_likelihood_perfect_candidate_at_top10_is_match_not_safe():
    # match=4.0 (perfect across C/P/E/G), top_10 (-1.0), strong PI (+0.2)
    # → 3.2 (Match label) — even a perfect candidate at MIT is not "Safe"
    likelihood, _ = admit_likelihood(4.0, "top_10", "strong")
    assert likelihood == pytest.approx(3.2)


def test_admit_likelihood_clipped_at_0():
    likelihood, _ = admit_likelihood(0.5, "top_10", "shrinking")
    # 0.5 - 1.0 - 0.4 = -0.9 → clipped to 0
    assert likelihood == 0.0


def test_admit_likelihood_clipped_at_4():
    likelihood, _ = admit_likelihood(4.0, "top_60_plus", "strong")
    # 4.0 + 0.4 + 0.2 = 4.6 → clipped to 4.0
    assert likelihood == 4.0


def test_confidence_band_full_data():
    assert confidence_band(0) == 0.3


def test_confidence_band_one_missing():
    assert confidence_band(1) == 0.5


def test_confidence_band_two_or_more_missing():
    assert confidence_band(2) == 0.7
    assert confidence_band(3) == 0.7


def test_likelihood_labels():
    assert likelihood_label(3.6) == "Safe"
    assert likelihood_label(3.2) == "Match"
    assert likelihood_label(2.7) == "Target"
    assert likelihood_label(2.2) == "Reach"
    assert likelihood_label(1.5) == "Far Reach"
