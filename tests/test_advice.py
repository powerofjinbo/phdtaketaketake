"""Tests for applicant-side advice: tier readiness, what-if improvement
plan, balanced application list."""

from __future__ import annotations

import pytest

from phd_matcher.matching.advice import (
    TYPICAL_ADMIT_BAR,
    build_application_list,
    improvement_plan,
    tier_readiness,
)
from phd_matcher.matching.ranker import rank_advisors
from phd_matcher.models import (
    CandidateAdvisor,
    Experience,
    Paper,
    Recommender,
    StandardizedTests,
    StudentProfile,
)
from phd_matcher.scoring.applicant import assess_applicant


def _student(**kw) -> StudentProfile:
    base = dict(
        field="physics", undergrad_institution="X", gpa_raw=3.7,
        gpa_scale="4.0", research_direction="quantum optics",
        experiences=[Experience(lab_pi_name="P", lab_tier="top_us",
                                duration_months=6, output_type="conference_poster")],
    )
    base.update(kw)
    return StudentProfile(**base)


def _cand(cid: str, tier: str, inst: str | None = None, **kw) -> CandidateAdvisor:
    return CandidateAdvisor(
        id=cid, name=cid, institution=inst or cid, school_tier=tier,
        field="physics", research_areas=["quantum optics"], **kw,
    )


# ---- Tier readiness ------------------------------------------------------

def test_tier_readiness_covers_all_tiers_and_is_monotone():
    rows = tier_readiness(assess_applicant(_student()))
    assert [r.school_tier for r in rows] == list(TYPICAL_ADMIT_BAR)
    margins = [r.margin for r in rows]
    assert margins == sorted(margins)  # easier tiers → bigger margin


def test_low_gpa_is_below_bar_at_top_with_screen_note():
    top = tier_readiness(assess_applicant(_student(gpa_raw=2.8)))[0]
    assert top.verdict == "below_bar"
    assert top.screen_penalty > 0
    assert "screening floor" in top.note


# ---- Improvement plan ----------------------------------------------------

def test_improvement_plan_ranks_actions_by_gain():
    plan = improvement_plan(_student(
        papers=[Paper(journal_tier=2, author_position=1, status="in_prep")],
        recommenders=[Recommender(name="T", relationship="course_instructor",
                                  months_known=4)],
    ))
    assert plan, "expected at least one applicable action"
    deltas = [a.delta_strength for a in plan]
    assert deltas == sorted(deltas, reverse=True)
    assert all(a.delta_strength > 0 for a in plan)
    names = " ".join(a.action for a in plan)
    assert "research supervisor" in names
    assert "in-prep" in names


def test_improvement_plan_is_hypothetical_and_does_not_mutate():
    s = _student()
    before = s.model_dump()
    improvement_plan(s)
    assert s.model_dump() == before


def test_english_retake_suggested_only_when_below_minimum():
    low = improvement_plan(_student(
        test_scores=StandardizedTests(english_test="toefl", english_score=80)))
    ok = improvement_plan(_student(
        test_scores=StandardizedTests(english_test="toefl", english_score=105)))
    assert any("English" in a.action for a in low)
    assert not any("English" in a.action for a in ok)


def test_no_letter_whatif_when_letters_undescribed():
    """Undescribed letters are an information gap, not a what-if."""
    plan = improvement_plan(_student())
    assert not any(a.pillar == "L" for a in plan)
    assert any("recommendation letters" in m
               for m in assess_applicant(_student()).missing_inputs)


# ---- Application list ----------------------------------------------------

def test_application_list_balances_and_caps_institutions():
    s = _student()
    cands = (
        [_cand(f"t10_{i}", "top_10", inst="Same U") for i in range(4)]
        + [_cand(f"t30_{i}", "top_11_30") for i in range(4)]
        + [_cand(f"t60_{i}", "top_31_60") for i in range(4)]
        + [_cand(f"low_{i}", "top_60_plus") for i in range(4)]
    )
    results = rank_advisors(s, cands, top_k=50)
    plan = build_application_list(results, size=8)
    assert len(plan.picks) <= 8
    assert sum(1 for p in plan.picks if p.institution == "Same U") <= 2
    assert plan.reach_count + plan.target_count + plan.safer_count == len(plan.picks)


def test_application_list_excludes_drops():
    s = _student()
    results = rank_advisors(s, [
        _cand("closed", "top_31_60", pi_signal="not_recruiting"),
        _cand("open", "top_31_60"),
    ], top_k=5)
    plan = build_application_list(results, size=5)
    assert "closed" in plan.excluded
    assert all(p.candidate_id != "closed" for p in plan.picks)


def test_application_list_warns_when_short():
    results = rank_advisors(_student(), [_cand("only", "top_10")], top_k=5)
    plan = build_application_list(results, size=6)
    assert any("eligible candidates" in n for n in plan.notes)


@pytest.mark.parametrize("size", [1, 3, 12])
def test_application_list_never_exceeds_size(size):
    results = rank_advisors(
        _student(), [_cand(f"c{i}", "top_31_60") for i in range(20)], top_k=50)
    assert len(build_application_list(results, size=size).picks) <= size
