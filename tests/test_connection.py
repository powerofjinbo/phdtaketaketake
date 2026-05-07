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


def test_big_collab_capped_at_0_10():
    """v2 recalibration: even 100+ ATLAS papers cap at 0.10 — alphabetical
    author-list bulk is a very weak signal alone. Rescue via
    `same_working_group` or `analysis_contact_overlap` for big-collab fields."""
    assert big_collab_paper_strength(100) == 0.10
    assert big_collab_paper_strength(50) == pytest.approx(0.10)


def test_big_collab_well_below_small_team_at_same_count():
    """v2: 5 small-team papers (1.0) is dramatically stronger than 5 big-collab
    papers (0.05). Recalibration tightened the gap further so big-collab
    bulk cannot mask absence of real working relationship."""
    small = small_team_coauthor_strength(5)
    big = big_collab_paper_strength(5)
    assert small > big
    assert small == 1.0
    assert big == pytest.approx(0.05)


def test_genealogy_same_advisor_v2_recalibrated():
    """v2: same_advisor genealogy is 0.65 (was 1.0). Academic siblings
    alone — without active collaboration — are no longer the strongest
    possible signal; that role belongs to verified small-team coauthorship."""
    assert genealogy_strength("same_advisor") == 0.65


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


def test_path_strength_strongest_plus_secondary_bonus():
    """v2 aggregation: strongest single edge + 0.10 × second-strongest,
    capped at 1.0, then × recency multiplier. With unknown recency
    (default 0.75): max(0.8, 0.65) = 0.8; raw = 0.8 + 0.10·0.65 = 0.865;
    final = 0.865 · 0.75 = 0.64875."""
    edges = {
        "small_team_coauthor_5y": 4,        # → 0.8
        "genealogy_relation": "same_advisor",  # → 0.65 (v2 recalibrated)
    }
    assert path_strength(edges) == pytest.approx(0.64875)


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
    """v2: 100 ATLAS papers gives only 0.10 raw (cap), times unknown
    recency 0.75 → 0.075. Big-collab alphabetical author bulk does NOT
    create a strong connection — must be rescued by working-group /
    analysis-contact / co-mentored-student / shared-grant evidence."""
    edges = {"big_collab_papers_5y": 100}
    assert path_strength(edges) == pytest.approx(0.075)


def test_path_strength_working_group_overrides_big_collab():
    """v2: working-group rescue. max=0.75 (WG), second=0.10 (big_collab);
    raw = 0.75 + 0.10·0.10 = 0.76; × unknown recency 0.75 = 0.57.
    The big-collab presence adds a tiny secondary bonus; the headline
    strength is the working-group evidence."""
    edges = {"big_collab_papers_5y": 50, "same_working_group": True}
    assert path_strength(edges) == pytest.approx(0.57)


def test_path_strength_analysis_contact_v2_recalibrated():
    """v2: analysis_contact_overlap is 0.70 (was 0.95). Recalibrated to
    fit the secondary-bonus + recency aggregation. With unknown recency
    0.75: 0.70 · 0.75 = 0.525."""
    edges = {"analysis_contact_overlap": True}
    assert path_strength(edges) == pytest.approx(0.525)


def test_path_strength_empty():
    assert path_strength({}) == 0.0


def test_raw_to_4_0_buckets():
    assert raw_to_4_0(0.85) == 4.0
    assert raw_to_4_0(0.65) == 3.7
    assert raw_to_4_0(0.45) == 3.3
    assert raw_to_4_0(0.25) == 2.8
    assert raw_to_4_0(0.05) == 2.3


def test_advisor_strength_components():
    """Post-roadmap-#6a: A is reputation-only. funding + recruiting moved
    to OpportunitySignal — advisor_strength_raw must NOT read them."""
    cand = {
        "normalized_collab_top20pct": 0.6,
        "collab_with_nas": True,
        "grad_placement_quality": 0.5,
        # active_funding_quality and pi_signal would be ignored by A;
        # not setting them here to make the invariant explicit.
    }
    expected = (
        0.40 * 0.6      # influence
        + 0.30 * 1.0    # elite (NAS)
        + 0.30 * 0.5    # placement
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
    """v2: small_team_coauthor=5 → raw 1.0 (capped). With explicit recent
    connection year (within 2y), recency=1.0; final raw=1.0 → bucket 4.0.
    (Without `most_recent_connection_year`, recency falls to 0.75 →
    raw=0.75 → bucket 3.7 — recency now matters.)"""
    cand = {
        "normalized_collab_top20pct": 0.5,  # ignored by C (lives in A)
        "paths_to_advisors": {
            "adv_001": {
                "small_team_coauthor_5y": 5,
                "most_recent_connection_year": 2026,
            },
        },
    }
    advisors = [{"id": "adv_001", "name": "Adv"}]
    assert connection_score(advisors, cand, current_year=2026) == 4.0


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


# ---- Connection v2 (Sprint 2 commit 1) ----------------------------------

from phd_matcher.scoring.connection import (  # noqa: E402
    aggregate_edge_strengths,
    co_mentored_student_strength,
    committee_or_exam_overlap_strength,
    conference_session_overlap_strength,
    prior_institution_overlap_strength,
    recency_multiplier,
    same_center_or_institute_strength,
    shared_grant_strength,
)


def test_shared_grant_scores_below_small_team_above_big_collab():
    """v2 ladder invariant: shared grants are stronger than big-collab
    co-membership but weaker than verified small-team coauthorship."""
    small_team = small_team_coauthor_strength(5)        # 1.0
    shared_grant_max = shared_grant_strength(2)          # 0.80
    big_collab_max = big_collab_paper_strength(100)      # 0.10
    assert big_collab_max < shared_grant_max < small_team


def test_co_mentored_student_is_strong_connection():
    """v2: co-mentored students rank near direct collaboration (max 0.90,
    just below small_team_coauthor's 1.0)."""
    assert co_mentored_student_strength(3) == pytest.approx(0.90)
    assert co_mentored_student_strength(1) == pytest.approx(0.30)
    # 5 co-mentored students don't exceed the 0.90 cap
    assert co_mentored_student_strength(5) == 0.90


def test_conference_overlap_is_weak_connection():
    """v2: conference-session overlap caps at 0.20 — proximity is not
    a working relationship; useful as a secondary bonus only."""
    assert conference_session_overlap_strength(2) == pytest.approx(0.20)
    assert conference_session_overlap_strength(10) == 0.20  # capped
    assert conference_session_overlap_strength(0) == 0.0


def test_big_collab_only_stays_weak_under_v2():
    """Connection-v2 invariant: big-collab author-list overlap alone
    cannot create strong C, no matter how many papers."""
    # 100 ATLAS papers, with 0–2y recency → still weak
    edges = {
        "big_collab_papers_5y": 100,
        "most_recent_connection_year": 2026,
    }
    assert path_strength(edges, current_year=2026) == pytest.approx(0.10)


def test_same_working_group_boosts_big_collab_context():
    """v2 'rescue' guardrail: working-group evidence dominates over
    weak big-collab co-authorship via the max-of-edges rule. The
    big-collab presence adds only a tiny secondary bonus."""
    edges_with_wg = {
        "big_collab_papers_5y": 50,         # 0.10
        "same_working_group": True,         # 0.75
        "most_recent_connection_year": 2026,
    }
    edges_without_wg = {
        "big_collab_papers_5y": 50,
        "most_recent_connection_year": 2026,
    }
    s_with = path_strength(edges_with_wg, current_year=2026)
    s_without = path_strength(edges_without_wg, current_year=2026)
    # max=0.75, second=0.10 → 0.75 + 0.10·0.10 = 0.76. With recency 1.0.
    assert s_with == pytest.approx(0.76)
    # Big-collab alone is just 0.10.
    assert s_without == pytest.approx(0.10)
    # The rescue is real and substantial.
    assert s_with > s_without + 0.50


def test_recency_decay_reduces_old_connection():
    """v2: the same edges with an old connection year score lower than
    with a recent connection year."""
    edges_recent = {
        "small_team_coauthor_5y": 5,
        "most_recent_connection_year": 2026,
    }
    edges_mid = {
        "small_team_coauthor_5y": 5,
        "most_recent_connection_year": 2022,   # 4y gap → 0.85
    }
    edges_old = {
        "small_team_coauthor_5y": 5,
        "most_recent_connection_year": 2014,   # 12y gap → 0.35
    }
    s_recent = path_strength(edges_recent, current_year=2026)
    s_mid = path_strength(edges_mid, current_year=2026)
    s_old = path_strength(edges_old, current_year=2026)
    assert s_recent > s_mid > s_old
    assert s_recent == 1.00
    assert s_mid == pytest.approx(0.85)
    assert s_old == pytest.approx(0.35)


def test_unknown_recency_uses_neutral_discount():
    """v2: `most_recent_connection_year=None` → multiplier 0.75 ('we
    didn't capture the year'). Distinct from a 0–2y recent connection
    (1.0) and from an old verified one (≤0.60)."""
    assert recency_multiplier(None) == 0.75
    edges = {"small_team_coauthor_5y": 5}   # no year set
    assert path_strength(edges, current_year=2026) == pytest.approx(0.75)


def test_secondary_signals_add_small_bonus_but_cap():
    """v2 aggregation: secondary edges add at most 0.10 × second_strongest
    to the headline edge, and the total is clipped at 1.0. Many weak
    signals must NOT beat one strong verified direct edge."""
    # One strong direct edge (verified small_team coauthor=5) at recent recency.
    one_strong = path_strength(
        {"small_team_coauthor_5y": 5, "most_recent_connection_year": 2026},
        current_year=2026,
    )
    # Many weak signals, even stacked at recent recency, can only carry
    # the strongest weak edge (0.40 same_center) + small bonus.
    many_weak = path_strength({
        "big_collab_papers_5y": 100,                # 0.10
        "conference_session_overlap_5y": 5,         # 0.20
        "same_center_or_institute": True,           # 0.40
        "prior_institution_overlap_years": 10,      # 0.35
        "most_recent_connection_year": 2026,
    }, current_year=2026)
    assert one_strong == 1.00
    assert many_weak < 0.50
    assert one_strong > many_weak

    # Cap at 1.0 — even 5 small_team + same_advisor + co_mentored can't
    # exceed 1.0 due to clipping.
    saturated = path_strength({
        "small_team_coauthor_5y": 5,                # 1.0
        "co_mentored_student_count": 3,             # 0.90
        "genealogy_relation": "same_advisor",       # 0.65
        "most_recent_connection_year": 2026,
    }, current_year=2026)
    assert saturated == 1.00


def test_strict_requires_evidence_for_new_path_fields():
    """v2: every newly-set PathEdge field needs evidence with matching
    `supports_fields` in strict mode (or one verified-empty item with
    `supports_fields=['path:<id>']` for a verified-empty path)."""
    from phd_matcher.matching.ranker import evidence_coverage
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        EvidenceSource,
        PathEdge,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics", undergrad_institution="X",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )
    cand = CandidateAdvisor(
        id="c1", name="Y", institution="MIT",
        school_tier="top_10", field="physics",
        paths_to_advisors={
            "adv_001": PathEdge(
                shared_grant_count_5y=2,            # set, no evidence
                co_mentored_student_count=1,
                # no items, no sources
            ),
        },
    )
    cov_strict = evidence_coverage(student, cand, strict=True)
    # Path is unsourced because the new fields lack supports_fields evidence.
    assert "path:adv_001" in cov_strict.unsourced_names

    # Adding evidence for both v2 fields makes the path verified.
    cand.paths_to_advisors["adv_001"] = PathEdge(
        shared_grant_count_5y=2,
        co_mentored_student_count=1,
        items=[
            EvidenceSource(
                url="https://reporter.nih.gov/...",
                source_type="nih_reporter",
                claim="2 active R01 co-PI grants 2022-2026",
                supports_fields=["shared_grant_count_5y"],
            ),
            EvidenceSource(
                url="https://lab.example/alumni",
                source_type="lab_page",
                claim="Dr. Z co-supervised by both PIs",
                supports_fields=["co_mentored_student_count"],
            ),
        ],
    )
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "path:adv_001" not in cov_strict.unsourced_names


def test_verified_empty_path_still_works():
    """v2 must not break the existing 'searched, found nothing' pattern.
    A PathEdge with no edge fields set + items.supports_fields=['path:<id>']
    counts as verified-empty in strict mode."""
    from phd_matcher.matching.ranker import evidence_coverage
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        EvidenceSource,
        PathEdge,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics", undergrad_institution="X",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )
    cand = CandidateAdvisor(
        id="c1", name="Y", institution="MIT",
        school_tier="top_10", field="physics",
        paths_to_advisors={
            "adv_001": PathEdge(
                items=[EvidenceSource(
                    url="https://scholar.example/search?q=X+Y",
                    source_type="google_scholar",
                    claim="searched 2020-2026: 0 co-authored papers, no shared lineage",
                    supports_fields=["path:adv_001"],
                )],
            ),
        },
    )
    cov_strict = evidence_coverage(student, cand, strict=True)
    assert "path:adv_001" not in cov_strict.unsourced_names
    assert "path:adv_001" not in cov_strict.missing_names


def test_connection_v2_preserves_no_advisor_baseline():
    """v2 must not break: with no current advisor, C honestly returns
    the lowest 4.0 bucket (2.3) — unchanged from v1."""
    cand = {"paths_to_advisors": {}}
    assert connection_score([], cand) == 2.3
    assert connection_score([], cand, current_year=2026) == 2.3


def test_strong_connection_still_beats_strong_A_or_O_only():
    """Connection-first invariant under v2: a candidate with a verified
    strong path (5 small-team papers, recent) outranks a candidate with
    no path but maxed-out A and O signals — the big-effort signal in
    PhD applications is the academic-network connection."""
    from phd_matcher.matching.ranker import compute_match
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        EvidenceSource,
        OpportunitySignal,
        PathEdge,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics", undergrad_institution="X",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )

    high_c = CandidateAdvisor(
        id="high_c", name="C", institution="MIT",
        school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={
            "adv_001": PathEdge(
                small_team_coauthor_5y=5,
                most_recent_connection_year=2026,
                items=[EvidenceSource(
                    url="https://scholar.google.com/...",
                    source_type="google_scholar",
                    claim="5 small-team papers 2024-2026",
                    supports_fields=["small_team_coauthor_5y"],
                )],
            ),
        },
        # No A signals, no O — pure connection candidate.
    )

    high_a_o = CandidateAdvisor(
        id="high_a_o", name="A", institution="Stanford",
        school_tier="top_10", field="physics",
        research_areas=["physics"],
        paths_to_advisors={},
        # Maxed reputation
        normalized_collab_top20pct=0.95,
        collab_with_nas=True,
        grad_placement_quality=0.9,
        # Maxed opportunity
        opportunity_signal=OpportunitySignal(
            pi_signal="strong",
            active_funding_quality=0.9,
            lab_open_positions=2,
            recent_phd_graduations=2,
            grant_end_years=4,
            sabbatical_or_admin_load=False,
        ),
    )

    r_c = compute_match(student, high_c)
    r_ao = compute_match(student, high_a_o)
    # Connection-first: C contribution (0.38·4.0 = 1.52) ought to dominate
    # the A+O delta in the match formula.
    assert r_c.match_score > r_ao.match_score, (
        f"connection-first invariant violated: high_c.match={r_c.match_score}, "
        f"high_a_o.match={r_ao.match_score}"
    )


def test_recency_future_date_treated_as_recent():
    """Edge case: most_recent_connection_year > current_year (data error
    / agent typo) clamps to the recent bucket (1.0) rather than going
    negative or producing nonsense."""
    assert recency_multiplier(2030, current_year=2026) == 1.00


def test_aggregate_edge_strengths_empty_is_zero():
    """No edges → 0.0 (the matcher's 'no claim' baseline)."""
    assert aggregate_edge_strengths([]) == 0.0


def test_aggregate_edge_strengths_single():
    """One edge → that edge's strength, no secondary bonus."""
    assert aggregate_edge_strengths([0.65]) == 0.65


def test_v2_field_specific_strengths():
    """Sanity: v2 strength functions return the expected ladder values."""
    assert shared_grant_strength(2) == pytest.approx(0.80)
    assert co_mentored_student_strength(3) == pytest.approx(0.90)
    assert committee_or_exam_overlap_strength() == 0.45
    assert same_center_or_institute_strength() == 0.40
    # min(0.35, years/10): caps at year ≥ 4 (since 4/10 > 0.35), linear below.
    assert prior_institution_overlap_strength(10) == pytest.approx(0.35)
    assert prior_institution_overlap_strength(1) == pytest.approx(0.10)
    assert prior_institution_overlap_strength(0) == 0.0
    assert conference_session_overlap_strength(1) == pytest.approx(0.10)
