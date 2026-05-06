"""Tests for GPA scoring (Scoring Design v0.3 §3)."""

import pytest

from phd_matcher.scoring.gpa import gpa_score, percentage_to_4_0, uk_class_to_4_0


def test_4_0_direct():
    assert gpa_score(3.8, "4.0") == pytest.approx(3.8)


def test_4_0_capped_at_4():
    assert gpa_score(4.5, "4.0") == pytest.approx(4.0)


def test_4_3_scaling():
    assert gpa_score(4.0, "4.3") == pytest.approx(4.0 * 4.0 / 4.3)


def test_4_5_scaling():
    assert gpa_score(4.5, "4.5") == pytest.approx(4.0)


def test_percentage_90_plus_is_4():
    assert percentage_to_4_0(95) == 4.0
    assert percentage_to_4_0(90) == 4.0


def test_percentage_85_to_89():
    assert percentage_to_4_0(87) == pytest.approx(3.7)


def test_percentage_below_65_is_2():
    assert percentage_to_4_0(60) == 2.0


def test_percentage_via_gpa_score():
    assert gpa_score(88, "100") == pytest.approx(3.7)


def test_uk_first():
    assert uk_class_to_4_0("first") == pytest.approx(3.8)


def test_uk_2_2():
    assert uk_class_to_4_0("2_2") == pytest.approx(2.8)


def test_uk_unknown_falls_back():
    assert uk_class_to_4_0("nonsense") == pytest.approx(2.0)


def test_invalid_scale_raises():
    with pytest.raises(ValueError):
        gpa_score(3.5, "5.0")
