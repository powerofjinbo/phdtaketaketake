"""Tests for experience scoring (Scoring Design v0.3 §4)."""

import pytest

from phd_matcher.scoring.experience import (
    duration_score,
    experience_score,
    lab_prestige_score,
    output_score,
    score_one_experience,
)


def test_lab_prestige_world_class():
    assert lab_prestige_score("world_class") == 4.0


def test_lab_prestige_top_us():
    assert lab_prestige_score("top_us") == 3.7


def test_lab_prestige_unknown_falls_back():
    assert lab_prestige_score("totally_made_up") == 2.0


def test_duration_24_months():
    assert duration_score(24) == 4.0


def test_duration_3_months_boundary():
    assert duration_score(3) == 2.5


def test_duration_below_3_months():
    assert duration_score(1) == 2.0


def test_output_paper():
    # paper already counted in P; assign 3.7 here so experience isn't penalized
    assert output_score("paper") == 3.7


def test_output_poster():
    assert output_score("conference_poster") == 3.3


def test_score_one_experience_weights():
    # weights: 0.20*lab + 0.30*duration + 0.50*output
    exp = {"lab_tier": "top_us", "duration_months": 12, "output_type": "honors_thesis"}
    expected = 0.20 * 3.7 + 0.30 * 3.5 + 0.50 * 3.0
    assert score_one_experience(exp) == pytest.approx(expected)


def test_experience_score_takes_max():
    exps = [
        {"lab_tier": "other", "duration_months": 6, "output_type": "participation_only"},
        {"lab_tier": "top_us", "duration_months": 24, "output_type": "paper"},
    ]
    # second experience is stronger, take it
    expected = 0.20 * 3.7 + 0.30 * 4.0 + 0.50 * 3.7
    assert experience_score(exps) == pytest.approx(expected)


def test_experience_score_empty_returns_2():
    assert experience_score([]) == 2.0
