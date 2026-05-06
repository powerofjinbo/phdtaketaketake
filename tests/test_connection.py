"""Tests for connection scoring (Scoring Design v0.3 §5)."""

import pytest

from phd_matcher.scoring.connection import (
    coauthor_strength,
    collaboration_strength,
    connection_score,
    field_strength,
    genealogy_strength,
    path_strength,
    raw_to_4_0,
)


def test_coauthor_strength_capped_at_1():
    assert coauthor_strength(10) == 1.0


def test_coauthor_strength_zero():
    assert coauthor_strength(0) == 0.0


def test_coauthor_strength_partial():
    assert coauthor_strength(2) == pytest.approx(0.4)


def test_genealogy_same_advisor():
    assert genealogy_strength("same_advisor") == 1.0


def test_genealogy_two_hop():
    assert genealogy_strength("two_hop") == 0.4


def test_genealogy_unknown_zero():
    assert genealogy_strength("nonsense") == 0.0


def test_collaboration_5y_full():
    assert collaboration_strength(5) == 1.0


def test_collaboration_under_1y_partial():
    assert collaboration_strength(0.5) == 0.3


def test_collaboration_zero():
    assert collaboration_strength(0) == 0.0


def test_path_strength_takes_max_no_stack():
    # Co-author 4 papers → 0.8; same advisor genealogy → 1.0
    # Should take MAX, not sum
    edges = {
        "coauthor_papers_5y": 4,
        "genealogy_relation": "same_advisor",
    }
    assert path_strength(edges) == 1.0


def test_path_strength_empty():
    assert path_strength({}) == 0.0


def test_raw_to_4_0_buckets():
    assert raw_to_4_0(0.85) == 4.0
    assert raw_to_4_0(0.65) == 3.7
    assert raw_to_4_0(0.45) == 3.3
    assert raw_to_4_0(0.25) == 2.8
    assert raw_to_4_0(0.05) == 2.3


def test_field_strength_components():
    cand = {
        "normalized_collab_top20pct": 0.5,
        "collab_with_nas": True,
        "grad_placement_quality": 0.4,
    }
    expected = 0.4 * 0.5 + 0.3 * 1.0 + 0.3 * 0.4
    assert field_strength(cand) == pytest.approx(expected)


def test_connection_score_no_advisor_uses_field_only():
    cand = {
        "normalized_collab_top20pct": 1.0,
        "collab_with_nas": True,
        "grad_placement_quality": 1.0,
        "paths_to_advisors": {},
    }
    # field_strength = 0.4 + 0.3 + 0.3 = 1.0 → 4.0
    assert connection_score([], cand) == 4.0


def test_connection_score_with_strong_path():
    cand = {
        "normalized_collab_top20pct": 0.5,
        "collab_with_nas": False,
        "grad_placement_quality": 0.5,
        "paths_to_advisors": {
            "adv_001": {"coauthor_papers_5y": 5},  # → 1.0 path
        },
    }
    # c_path = 1.0; c_field = 0.4*0.5 + 0 + 0.3*0.5 = 0.35
    # c_raw = 0.6*1.0 + 0.4*0.35 = 0.74 → 3.7 bucket
    advisors = [{"id": "adv_001", "name": "Adv"}]
    assert connection_score(advisors, cand) == 3.7
