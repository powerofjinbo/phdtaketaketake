"""Tests for keyword-overlap direction relevance."""

import pytest

from phd_matcher.matching.direction import (
    _tokenize,
    direction_relevance,
    filter_by_direction,
)


def test_empty_inputs_are_zero():
    assert direction_relevance("", ["quantum computing"]) == 0.0
    assert direction_relevance("quantum computing", []) == 0.0


def test_no_overlap_is_zero():
    assert direction_relevance("protein folding", ["dark matter"]) == 0.0


def test_identical_is_one():
    d = "quantum error correction"
    assert direction_relevance(d, [d]) == pytest.approx(1.0)


def test_inflections_match():
    assert direction_relevance("neural networks", ["neural network"]) == pytest.approx(1.0)
    rel = direction_relevance("reinforcement learning", ["learned reinforcement"])
    assert rel == pytest.approx(1.0)


def test_broad_pi_not_punished_for_listing_more_areas():
    """A PI covering the student's whole direction plus extra topics should
    beat a PI covering only half of it (Jaccard got this backwards)."""
    direction = "graph neural networks drug discovery"
    broad = ["graph neural networks", "drug discovery", "robotics", "vision", "speech"]
    narrow = ["graph theory"]
    assert direction_relevance(direction, broad) > direction_relevance(direction, narrow)


def test_chinese_direction_uses_bigrams():
    assert "量子" in _tokenize("量子计算")
    assert direction_relevance("量子计算", ["量子信息与量子计算"]) > 0.5
    assert direction_relevance("量子计算", ["蛋白质折叠"]) == 0.0


def test_mixed_language_direction():
    assert direction_relevance("强化学习 robotics", ["robotic manipulation", "强化学习"]) > 0.5


def test_filter_by_direction_threshold():
    class C:
        def __init__(self, areas):
            self.research_areas = areas

    cs = [C(["quantum computing"]), C(["ecology"])]
    assert len(filter_by_direction(cs, "quantum computing")) == 2
    assert len(filter_by_direction(cs, "quantum computing", threshold=0.5)) == 1
