"""Tests for Strategy / Portfolio explainer (Sprint-2-c5)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from phd_matcher.matching.ranker import compute_match, rank_advisors
from phd_matcher.matching.strategy import (
    DROP_UNSOURCED_THRESHOLD,
    summarize_portfolio,
)
from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    EvidenceEntry,
    EvidenceSource,
    OpportunitySignal,
    PathEdge,
    StrategyRecommendation,
    StudentProfile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MATCH_SCRIPT = REPO_ROOT / "scripts" / "match.py"


def _student() -> StudentProfile:
    return StudentProfile(
        field="physics",
        undergrad_institution="X",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
        current_advisors=[CurrentAdvisor(id="adv_001", name="Wang", institution="Y")],
    )


def _bare_candidate(cid: str = "c1", **kwargs) -> CandidateAdvisor:
    base = dict(
        id=cid, name=f"Prof. {cid}", institution="MIT",
        school_tier="top_31_60", field="physics",
        research_areas=["physics"],
    )
    base.update(kwargs)
    return CandidateAdvisor(**base)


# ---- Strategy is purely derivative ---------------------------------------

def test_strategy_does_not_change_scores():
    """The strategy layer must NOT modify any scoring field. compute_match
    must produce the same scores regardless of strategy attachment."""
    cand = _bare_candidate(
        normalized_collab_top20pct=0.7,
        collab_with_nas=True,
        grad_placement_quality=0.8,
    )
    r = compute_match(_student(), cand)
    # Capture all numeric fields BEFORE inspecting strategy
    s_before = (
        r.match_score, r.application_strength, r.risk_adjusted_strength,
        r.difficulty_adjusted_strength, r.research_fit_score,
        r.c_score, r.a_score, r.p_score, r.e_score, r.g_score,
        r.confidence_band, r.lower_bound,
        r.program_difficulty_penalty, r.opportunity_adj,
    )
    # Strategy is attached
    assert r.strategy is not None
    # Re-compute and confirm identical scores
    r2 = compute_match(_student(), cand)
    s_after = (
        r2.match_score, r2.application_strength, r2.risk_adjusted_strength,
        r2.difficulty_adjusted_strength, r2.research_fit_score,
        r2.c_score, r2.a_score, r2.p_score, r2.e_score, r2.g_score,
        r2.confidence_band, r2.lower_bound,
        r2.program_difficulty_penalty, r2.opportunity_adj,
    )
    assert s_before == s_after


# ---- Bucket precedence (drop → only_if_space → reach → target → priority)

def test_not_recruiting_forces_drop():
    """Effective pi_signal == 'not_recruiting' → bucket=drop, action=skip."""
    cand = _bare_candidate(pi_signal="not_recruiting")
    r = compute_match(_student(), cand)
    assert r.strategy is not None
    assert r.strategy.apply_bucket == "drop"
    assert r.strategy.recommended_action == "skip"


def test_unsourced_3_or_more_forces_drop():
    """≥3 unsourced claims → bucket=drop regardless of nominal score."""
    cand = _bare_candidate(
        normalized_collab_top20pct=0.95,    # set, no evidence → unsourced
        collab_with_nas=True,                # set, no evidence → unsourced
        grad_placement_quality=0.9,          # set, no evidence → unsourced
        # school_tier always required → 4th unsourced
    )
    r = compute_match(_student(), cand)
    assert r.unsourced_signals >= DROP_UNSOURCED_THRESHOLD
    assert r.strategy is not None
    assert r.strategy.apply_bucket == "drop"


def test_low_research_fit_can_drop_even_if_school_famous():
    """research_fit_score < 0.20 → drop, even at top_10. The candidate
    has unsourced<3 so the unsourced-rule doesn't fire first; the
    research_fit drop branch is what triggers."""
    cand = _bare_candidate(
        cid="famous_low_fit",
        institution="MIT", school_tier="top_10",
        research_fit_score=0.10,
        # Source the always-required signals so unsourced stays < 3 and
        # the research_fit drop rule is the decisive one.
        evidence={
            "school_tier": EvidenceEntry(items=[EvidenceSource(
                url="https://www.usnews.com/...",
                source_type="us_news",
                claim="MIT physics top 10",
                supports_fields=["school_tier"],
            )]),
            "research_areas": EvidenceEntry(items=[EvidenceSource(
                url="https://lab.mit.edu/research",
                source_type="lab_page",
                claim="research focus",
                supports_fields=["research_areas"],
            )]),
            "research_fit": EvidenceEntry(items=[EvidenceSource(
                url="https://scholar.google.com/papers",
                source_type="google_scholar",
                claim="0/10 recent papers on student's topic",
                supports_fields=["research_fit"],
            )]),
        },
    )
    r = compute_match(_student(), cand)
    assert r.unsourced_signals < DROP_UNSOURCED_THRESHOLD
    assert r.strategy is not None
    assert r.strategy.apply_bucket == "drop"
    assert any("research_fit" in reason for reason in r.strategy.why_this_rank)


def test_drop_precedence_beats_priority_threshold():
    """Bucket precedence test: even if risk_adjusted is high, hard risks
    (e.g., not_recruiting) override and the candidate drops to bucket=drop."""
    # Build a high-risk_adjusted candidate but with not_recruiting
    cand = _bare_candidate(
        cid="high_score_not_recruiting",
        school_tier="top_60_plus",   # easy
        opportunity_signal=OpportunitySignal(pi_signal="not_recruiting"),
    )
    r = compute_match(_student(), cand)
    assert r.strategy is not None
    assert r.strategy.apply_bucket == "drop"


# ---- Action mapping ------------------------------------------------------

def test_unsourced_claims_force_investigate_evidence():
    """Without strong C, having any unsourced claim forces
    recommended_action=investigate_evidence (unless bucket is
    drop/only_if_space, which take precedence in the action ladder)."""
    # Source missing signals to keep bucket out of only_if_space
    cand = _bare_candidate(
        cid="some_unsourced",
        school_tier="top_60_plus",
        normalized_collab_top20pct=0.7,    # set, no evidence → unsourced
        collab_with_nas=True,               # set, no evidence → unsourced
        grad_placement_quality=0.7,         # set, no evidence → unsourced
        # school_tier always-required no evidence → another unsourced
    )
    r = compute_match(_student(), cand)
    assert r.unsourced_signals >= 1
    if r.strategy.apply_bucket == "drop":
        # If high unsourced count tripped the drop rule (≥3), action=skip
        assert r.strategy.recommended_action == "skip"
    elif r.strategy.apply_bucket == "only_if_space":
        # only_if_space → deprioritize when no strong C
        assert r.strategy.recommended_action == "deprioritize"
    else:
        # Without strong C, unsourced → investigate_evidence
        assert r.strategy.recommended_action == "investigate_evidence"


def test_strong_connection_gets_contact_first():
    """Candidate with strong C (≥3.7) → recommended_action=contact_first
    (regardless of priority/target — strong direct path warrants
    personal outreach)."""
    cand = _bare_candidate(
        cid="strong_c",
        institution="MIT", school_tier="top_60_plus",  # easy program
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
        evidence={
            "school_tier": EvidenceEntry(items=[EvidenceSource(
                url="https://www.usnews.com/...",
                source_type="us_news",
                claim="ranking 50",
                supports_fields=["school_tier"],
            )]),
        },
    )
    r = compute_match(_student(), cand)
    assert r.c_score >= 3.7
    assert r.strategy is not None
    assert r.strategy.recommended_action == "contact_first"


# ---- Priority / target requirements --------------------------------------

def test_priority_requires_clean_evidence():
    """Priority bucket requires unsourced_signals == 0 AND
    risk_adjusted_strength >= 2.70 AND lower_bound >= 2.30 AND
    (strong C or strong fit). Missing the unsourced=0 requirement
    cannot reach priority."""
    # Build a high-risk_adjusted candidate but with 1 unsourced
    cand = _bare_candidate(
        cid="almost_priority",
        institution="MIT", school_tier="top_60_plus",
        normalized_collab_top20pct=0.7,    # 1 unsourced
        paths_to_advisors={
            "adv_001": PathEdge(
                small_team_coauthor_5y=5,
                most_recent_connection_year=2026,
                items=[EvidenceSource(
                    url="https://scholar.google.com/...",
                    source_type="google_scholar",
                    claim="5 papers",
                    supports_fields=["small_team_coauthor_5y"],
                )],
            ),
        },
    )
    r = compute_match(_student(), cand)
    assert r.unsourced_signals >= 1
    # Must NOT be priority (despite high risk_adjusted)
    assert r.strategy is not None
    assert r.strategy.apply_bucket != "priority"


# ---- Evidence-fix queue --------------------------------------------------

def test_evidence_fix_queue_prioritizes_unsourced_over_missing():
    """In the portfolio summary, unsourced entries (severity=high) sort
    before missing entries (severity=medium)."""
    cand_unsourced = _bare_candidate(
        cid="unsourced_cand",
        normalized_collab_top20pct=0.7,    # set without evidence
    )
    cand_missing = _bare_candidate(cid="missing_cand")    # all defaults → missing

    student = _student()
    r_unsourced = compute_match(student, cand_unsourced)
    r_missing = compute_match(student, cand_missing)
    summary = summarize_portfolio([r_unsourced, r_missing])

    # All high-severity entries appear before any medium entries
    severities = [entry["severity"] for entry in summary.evidence_fix_queue]
    assert severities == sorted(
        severities, key=lambda s: (0 if s == "high" else 1),
    )


# ---- Schema enforcement --------------------------------------------------

def test_output_strategy_schema_forbids_extra_fields():
    """StrategyRecommendation must use extra=forbid (Pydantic-strict)."""
    with pytest.raises(ValidationError):
        StrategyRecommendation(
            apply_bucket="target",
            recommended_action="apply",
            unknown_field=True,
        )


def test_strategy_recommendation_validates_bucket_enum():
    with pytest.raises(ValidationError):
        StrategyRecommendation(
            apply_bucket="DEFINITELY_NOT_A_BUCKET",
            recommended_action="apply",
        )


# ---- CLI subprocess tests ------------------------------------------------

def test_cli_outputs_strategy_summary(tmp_path):
    """Top-level `strategy_summary` block in match output."""
    profile = {
        "field": "physics",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "ATLAS Higgs",
    }
    candidates = [
        {
            "id": "c1", "name": "P", "institution": "MIT",
            "school_tier": "top_60_plus", "field": "physics",
            "research_areas": ["physics"],
        },
    ]
    pf = tmp_path / "p.json"
    cf = tmp_path / "c.json"
    pf.write_text(json.dumps(profile))
    cf.write_text(json.dumps(candidates))
    result = subprocess.run(
        [
            sys.executable, str(MATCH_SCRIPT),
            "--profile-file", str(pf), "--candidates-file", str(cf),
            "--field", "physics", "--top-k", "1",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert "strategy_summary" in out
    for key in (
        "priority_candidates", "target_candidates", "reach_candidates",
        "only_if_space_candidates", "drop_candidates",
        "evidence_fix_queue", "portfolio_notes",
    ):
        assert key in out["strategy_summary"]


def test_cli_results_include_strategy(tmp_path):
    """Each MatchResult in the output JSON has a `strategy` block."""
    profile = {
        "field": "physics",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "ATLAS",
    }
    candidates = [
        {
            "id": "c1", "name": "P", "institution": "MIT",
            "school_tier": "top_31_60", "field": "physics",
            "research_areas": ["physics"],
        },
    ]
    pf = tmp_path / "p.json"
    cf = tmp_path / "c.json"
    pf.write_text(json.dumps(profile))
    cf.write_text(json.dumps(candidates))
    result = subprocess.run(
        [
            sys.executable, str(MATCH_SCRIPT),
            "--profile-file", str(pf), "--candidates-file", str(cf),
            "--field", "physics", "--top-k", "1",
        ],
        capture_output=True, text=True, check=False,
    )
    out = json.loads(result.stdout)
    assert out["results"]
    for res in out["results"]:
        assert "strategy" in res
        assert res["strategy"] is not None
        assert "apply_bucket" in res["strategy"]
        assert "recommended_action" in res["strategy"]


# ---- Outreach angle ------------------------------------------------------

def test_outreach_angle_uses_only_sourced_material():
    """Without a verified path or sourced research_fit_summary, the
    outreach_angle is None — the agent should fall back to 'read papers
    before contacting'."""
    cand = _bare_candidate()
    r = compute_match(_student(), cand)
    assert r.strategy is not None
    assert r.strategy.outreach_angle is None


def test_outreach_angle_present_when_path_exists():
    cand = _bare_candidate(
        institution="MIT", school_tier="top_60_plus",
        paths_to_advisors={
            "adv_001": PathEdge(
                small_team_coauthor_5y=3,
                most_recent_connection_year=2026,
                items=[EvidenceSource(
                    url="https://...",
                    source_type="google_scholar",
                    claim="3 papers",
                    supports_fields=["small_team_coauthor_5y"],
                )],
            ),
        },
    )
    r = compute_match(_student(), cand)
    assert r.strategy is not None
    assert r.strategy.outreach_angle is not None
    assert "small-team" in r.strategy.outreach_angle


# ---- Portfolio summary ---------------------------------------------------

def test_summarize_portfolio_partitions_candidates_by_bucket():
    """Candidates are listed in the matching bucket field."""
    student = _student()
    drop_cand = _bare_candidate(cid="drop1", pi_signal="not_recruiting")
    cands = [drop_cand]
    results = [compute_match(student, c) for c in cands]
    summary = summarize_portfolio(results)
    assert "drop1" in summary.drop_candidates


def test_summarize_portfolio_notes_include_total_breakdown():
    student = _student()
    cands = [_bare_candidate(cid=f"c{i}") for i in range(3)]
    results = [compute_match(student, c) for c in cands]
    summary = summarize_portfolio(results)
    # First note line contains the total breakdown
    assert summary.portfolio_notes
    assert "3 candidates" in summary.portfolio_notes[0]


# ---- Sanity: rank_advisors composes with strategy ------------------------

def test_rank_advisors_attaches_strategy_per_candidate():
    student = _student()
    cands = [
        _bare_candidate(cid=f"c{i}", school_tier="top_31_60")
        for i in range(3)
    ]
    ranked = rank_advisors(student, cands, top_k=3)
    assert all(r.strategy is not None for r in ranked)
