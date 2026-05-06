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
    assert aggregate_papers([]) == pytest.approx(3.0)


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


# ---- pub_score end-to-end ----

def test_pub_score_no_papers_returns_floor():
    assert pub_score([]) == pytest.approx(3.0)


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
