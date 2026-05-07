"""Tests for connection scoring (Scoring Design v0.3, post-review big-collab
fix + strict PathEdge schema)."""

import pytest
from pydantic import ValidationError

from phd_matcher.models import PathEdge
from phd_matcher.scoring.advisor import advisor_strength_raw
from phd_matcher.scoring.connection import (
    big_collab_paper_strength,
    collaboration_strength,
    connection_score,
    genealogy_strength,
    path_strength,
    raw_to_4_0,
    small_team_coauthor_strength,
)


def test_small_team_capped_at_1():
    assert small_team_coauthor_strength(10) == 1.0


def test_small_team_zero():
    assert small_team_coauthor_strength(0) == 0.0


def test_small_team_partial():
    assert small_team_coauthor_strength(2) == pytest.approx(0.4)


def test_big_collab_capped_at_0_4():
    """Even 50 ATLAS papers shouldn't saturate to 1.0 — alphabetical author
    list bulk doesn't imply working relationship."""
    assert big_collab_paper_strength(50) == 0.4


def test_big_collab_well_below_small_team_at_same_count():
    """5 papers in a small team is much stronger than 5 papers as a big-collab
    co-name. This is the core fix from the code review."""
    small = small_team_coauthor_strength(5)
    big = big_collab_paper_strength(5)
    assert small > big
    assert small == 1.0
    assert big == pytest.approx(0.2)


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
    edges = {
        "small_team_coauthor_5y": 4,
        "genealogy_relation": "same_advisor",
    }
    assert path_strength(edges) == 1.0


def test_path_strength_rejects_legacy_coauthor_field():
    """Strict schema (post-review): legacy 'coauthor_papers_5y' is forbidden.
    Agent must use small_team_coauthor_5y / big_collab_papers_5y explicitly."""
    edges = {"coauthor_papers_5y": 5}
    with pytest.raises(ValidationError):
        path_strength(edges)


def test_path_edge_rejects_unknown_field():
    with pytest.raises(ValidationError):
        PathEdge(some_made_up_edge=True)


def test_path_edge_rejects_negative_count():
    with pytest.raises(ValidationError):
        PathEdge(small_team_coauthor_5y=-1)


def test_path_edge_rejects_negative_overlap_years():
    with pytest.raises(ValidationError):
        PathEdge(collaboration_overlap_years=-2.0)


def test_path_edge_rejects_invalid_genealogy_relation():
    with pytest.raises(ValidationError):
        PathEdge(genealogy_relation="cousin")  # not in Literal


def test_path_edge_accepts_minimal_valid():
    """A path entry can be just sources + note (e.g., 'searched, found
    nothing') and still be valid."""
    edge = PathEdge(sources=["https://scholar.google.com/..."], note="no co-authorship")
    assert path_strength(edge) == 0.0


def test_path_strength_big_collab_alone_is_weak():
    """100 ATLAS papers gives only 0.4 path strength — it's *one PhD-relevant
    edge of evidence*, not a working relationship."""
    edges = {"big_collab_papers_5y": 100}
    assert path_strength(edges) == 0.4


def test_path_strength_working_group_overrides_big_collab():
    """When the agent finds verified working-group / convener overlap, that
    beats raw big-collab co-authorship."""
    edges = {"big_collab_papers_5y": 50, "same_working_group": True}
    assert path_strength(edges) == 0.7


def test_path_strength_analysis_contact_strongest_in_big_collab_field():
    edges = {"analysis_contact_overlap": True}
    assert path_strength(edges) == 0.95


def test_path_strength_empty():
    assert path_strength({}) == 0.0


def test_raw_to_4_0_buckets():
    assert raw_to_4_0(0.85) == 4.0
    assert raw_to_4_0(0.65) == 3.7
    assert raw_to_4_0(0.45) == 3.3
    assert raw_to_4_0(0.25) == 2.8
    assert raw_to_4_0(0.05) == 2.3


def test_advisor_strength_components():
    """Per roadmap-#3: advisor influence is now a separate A dimension.
    The previous `field_strength` lived inside Connection — bug: PI prestige
    inflated the C score. Now it's `advisor_strength_raw` and feeds the A
    pillar in MatchResult."""
    cand = {
        "normalized_collab_top20pct": 0.6,
        "collab_with_nas": True,
        "grad_placement_quality": 0.5,
        "active_funding_quality": 0.7,
        "pi_signal": "normal",  # → recruiting_health = 0.7
    }
    expected = (
        0.30 * 0.6      # influence
        + 0.20 * 1.0    # elite (NAS)
        + 0.20 * 0.7    # active funding
        + 0.20 * 0.5    # placement
        + 0.10 * 0.7    # recruiting (normal)
    )
    assert advisor_strength_raw(cand) == pytest.approx(expected)


def test_connection_score_no_advisor_returns_minimum_bucket():
    """Roadmap-#3 split: with no current advisor, C honestly has no path
    signal to evaluate. Returns the lowest 4.0 bucket (2.3) — PI prestige
    is captured separately in A."""
    cand = {
        "normalized_collab_top20pct": 1.0,
        "collab_with_nas": True,
        "grad_placement_quality": 1.0,
        "paths_to_advisors": {},
    }
    assert connection_score([], cand) == 2.3


def test_connection_score_with_strong_path():
    """Roadmap-#3 split: C now only reflects path strength (no field-strength
    blending). A 1.0 path strength saturates to bucket 4.0."""
    cand = {
        "normalized_collab_top20pct": 0.5,  # ignored by C now (was: blended)
        "paths_to_advisors": {
            "adv_001": {"small_team_coauthor_5y": 5},  # → strength 1.0
        },
    }
    advisors = [{"id": "adv_001", "name": "Adv"}]
    assert connection_score(advisors, cand) == 4.0


def test_connection_score_big_collab_only_weaker_than_small_team():
    """Two candidates: same field strength, one with 5 small-team papers,
    one with 5 big-collab papers. Small-team should rank higher."""
    base_cand = {
        "normalized_collab_top20pct": 0.5,
        "collab_with_nas": False,
        "grad_placement_quality": 0.5,
    }
    small_team_cand = {
        **base_cand,
        "paths_to_advisors": {"adv_001": {"small_team_coauthor_5y": 5}},
    }
    big_collab_cand = {
        **base_cand,
        "paths_to_advisors": {"adv_001": {"big_collab_papers_5y": 5}},
    }
    advisors = [{"id": "adv_001", "name": "Adv"}]
    assert connection_score(advisors, small_team_cand) > connection_score(
        advisors, big_collab_cand
    )
