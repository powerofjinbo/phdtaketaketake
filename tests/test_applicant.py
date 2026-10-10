"""Tests for the applicant model v2 (phd_matcher.scoring.applicant)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from phd_matcher.matching.ranker import compute_match, rank_advisors
from phd_matcher.models import (
    CandidateAdvisor,
    ClassRank,
    Experience,
    Honor,
    Paper,
    Recommender,
    StandardizedTests,
    StudentProfile,
)
from phd_matcher.scoring import admit
from phd_matcher.scoring.applicant import (
    academic_score,
    academic_screen_penalty,
    assess_applicant,
    honors_bonus,
    letters_score,
    rank_to_4_0,
    research_experience_score,
    score_letter,
    standardized_tests_adjustment,
    tier_applicant_score,
)
from phd_matcher.scoring.experience import experience_score


def _student(**kw) -> StudentProfile:
    base = dict(
        field="physics", undergrad_institution="X",
        gpa_raw=3.7, gpa_scale="4.0", research_direction="quantum optics",
    )
    base.update(kw)
    return StudentProfile(**base)


def _exp(**kw) -> Experience:
    base = dict(lab_pi_name="P", lab_tier="top_us", duration_months=12,
                output_type="conference_poster")
    base.update(kw)
    return Experience(**base)


def _rec(**kw) -> Recommender:
    base = dict(name="R", standing="top_us", relationship="research_supervisor",
                months_known=18, expected_strength="strong")
    base.update(kw)
    return Recommender(**base)


def _cand(tier: str = "top_31_60") -> CandidateAdvisor:
    return CandidateAdvisor(
        id="c", name="C", institution="U", school_tier=tier, field="physics",
        research_areas=["quantum optics"],
    )


# ---- Back-compat ---------------------------------------------------------

def test_v1_profile_scores_exactly_as_before():
    """No v2 inputs → the applicant block equals the v1 P/E/G sum."""
    s = _student(
        experiences=[_exp()],
        papers=[Paper(journal_tier=3, author_position=2)],
    )
    a = assess_applicant(s)
    assert a.letters_score is None
    assert a.honors_bonus == 0 and a.tests_adj == 0 and a.spike_bonus == 0
    for tier, w in admit.TIER_WEIGHTS.items():
        w_peg = w["P"] + w["E"] + w["G"]
        v1 = (w["P"] * a.research_output_score + w["E"] * a.research_experience_score
              + w["G"] * a.academic_score)
        assert w_peg * tier_applicant_score(a, w) == pytest.approx(v1)
        r = compute_match(s, _cand(tier))
        assert r.match_score == pytest.approx(
            round(admit.match_score(r.c_score, r.a_score, r.p_score, r.e_score,
                                    r.g_score, tier), 2), abs=0.011)


def test_single_experience_matches_v1():
    e = _exp()
    assert research_experience_score([e]) == pytest.approx(
        experience_score([e.model_dump()])
    )


# ---- Academic record -----------------------------------------------------

def test_institution_context_moves_gpa():
    elite = academic_score(_student(undergrad_tier="elite"))
    plain = academic_score(_student())
    other = academic_score(_student(undergrad_tier="other"))
    assert elite > plain > other
    assert elite - plain == pytest.approx(0.15)


def test_class_rank_blends_with_gpa():
    assert rank_to_4_0(0.01) == pytest.approx(4.0)
    assert rank_to_4_0(0.10) == pytest.approx(3.7)
    top = academic_score(_student(class_rank=ClassRank(rank=2, cohort_size=200)))
    mid = academic_score(_student(class_rank=ClassRank(rank=100, cohort_size=200)))
    assert top > academic_score(_student()) > mid


def test_class_rank_cannot_exceed_cohort():
    with pytest.raises(ValidationError):
        ClassRank(rank=5, cohort_size=3)


def test_major_gpa_weighs_more_than_overall():
    s = _student(gpa_raw=3.5, major_gpa_raw=3.9)
    assert academic_score(s) == pytest.approx(0.4 * 3.5 + 0.6 * 3.9)


def test_trend_and_graduate_courses():
    assert academic_score(_student(gpa_trend="rising")) > academic_score(_student())
    assert academic_score(_student(gpa_trend="falling")) < academic_score(_student())
    assert academic_score(_student(graduate_course_count=10)) == pytest.approx(3.7 + 0.12)


def test_master_degree_weighs_more():
    s = _student(gpa_raw=3.2, degree_level="master", master_gpa_raw=3.9,
                 master_gpa_scale="4.0")
    assert academic_score(s) == pytest.approx(0.6 * 3.9 + 0.4 * 3.2)


def test_academic_capped():
    s = _student(gpa_raw=4.0, undergrad_tier="elite", gpa_trend="rising",
                 graduate_course_count=5)
    assert academic_score(s) == pytest.approx(4.0)


# ---- Research experience -------------------------------------------------

def test_role_and_relevance_adjust_experience():
    base = research_experience_score([_exp()])
    assert research_experience_score([_exp(role="lead")]) > base
    assert research_experience_score([_exp(role="assistant")]) < base
    assert research_experience_score([_exp(field_relevance="different")]) < base


def test_second_experience_never_hurts_and_weak_adds_nothing():
    strong = _exp(lab_tier="world_class", duration_months=24, output_type="conference_oral")
    weak = _exp(lab_tier="other", duration_months=1, output_type="participation_only")
    one = research_experience_score([strong])
    assert research_experience_score([strong, weak]) == pytest.approx(one)
    assert research_experience_score([strong, strong]) >= one
    assert research_experience_score([_exp(), _exp()]) > research_experience_score([_exp()])


# ---- Letters -------------------------------------------------------------

def test_letters_none_when_not_described():
    assert letters_score([]) is None


def test_supervisor_letter_beats_course_letter():
    assert score_letter(_rec()) > score_letter(_rec(relationship="course_instructor"))
    assert score_letter(_rec(standing="world_class")) > score_letter(_rec())
    assert score_letter(_rec(months_known=30)) > score_letter(_rec(months_known=2))


def test_fewer_than_three_letters_fill_weak_slots():
    one = letters_score([_rec()])
    three = letters_score([_rec(), _rec(), _rec()])
    assert three > one


def test_letters_enter_match_and_strong_letters_help():
    weak = _student(recommenders=[_rec(relationship="other", standing="other",
                                       months_known=1, expected_strength="good")] * 3)
    strong = _student(recommenders=[_rec(standing="world_class", months_known=30,
                                         expected_strength="exceptional")] * 3)
    r_weak = compute_match(weak, _cand())
    r_strong = compute_match(strong, _cand())
    assert r_strong.l_score > r_weak.l_score
    assert r_strong.match_score > r_weak.match_score


# ---- Honors / tests / spike ---------------------------------------------

def test_honors_bonus_bounded():
    assert honors_bonus(_student()) == 0.0
    assert honors_bonus(_student(honors=[Honor(name="IPhO gold", level="international")])) == \
        pytest.approx(0.15)
    many = _student(honors=[Honor(name=f"h{i}", level="international") for i in range(10)])
    assert honors_bonus(many) == pytest.approx(0.18)


def test_english_below_minimum_is_flagged():
    adj, flags = standardized_tests_adjustment(_student(
        test_scores=StandardizedTests(english_test="toefl", english_score=85)))
    assert adj < 0 and flags
    adj, flags = standardized_tests_adjustment(_student(
        test_scores=StandardizedTests(english_test="toefl", english_score=105,
                                      subject_gre_percentile=95)))
    assert adj > 0 and not flags


def test_spike_bonus_for_standout_research():
    papers = [Paper(journal_tier=1, author_position=1)]
    a = assess_applicant(_student(papers=papers))
    assert a.research_output_score == pytest.approx(4.0)
    assert a.spike_bonus == pytest.approx(0.05)
    assert any("standout" in s for s in a.strengths)


# ---- Screening -----------------------------------------------------------

def test_academic_screen_penalty_is_tier_dependent():
    assert academic_screen_penalty(3.5, "top_10") == 0.0
    assert academic_screen_penalty(3.0, "top_10") == pytest.approx(0.4 * 0.3)
    assert academic_screen_penalty(3.0, "top_60_plus") == 0.0


def test_low_gpa_screened_harder_at_top_schools():
    s = _student(gpa_raw=2.8)
    top = compute_match(s, _cand("top_10"))
    low = compute_match(s, _cand("top_60_plus"))
    assert top.academic_screen_penalty > low.academic_screen_penalty


# ---- Assessment output ---------------------------------------------------

def test_assessment_reports_tier_confidence_and_gaps():
    bare = assess_applicant(_student())
    assert bare.confidence == "low"
    assert bare.missing_inputs
    assert "no publications or preprints yet" in bare.weaknesses

    rich = assess_applicant(_student(
        undergrad_tier="elite", class_rank=ClassRank(rank=3, cohort_size=150),
        gpa_trend="rising",
        experiences=[_exp(role="lead", field_relevance="same_subfield")],
        recommenders=[_rec(), _rec(), _rec(relationship="course_instructor")],
        test_scores=StandardizedTests(english_test="toefl", english_score=110),
        papers=[Paper(journal_tier=2, author_position=1)],
    ))
    assert rich.confidence == "high"
    assert rich.missing_inputs == []
    assert rich.tier in ("strong", "exceptional")
    assert rich.applicant_strength > bare.applicant_strength


def test_missing_research_letter_is_a_weakness():
    a = assess_applicant(_student(recommenders=[_rec(relationship="course_instructor")]))
    assert any("supervised your research" in w for w in a.weaknesses)
    assert any("three letters" in f for f in a.risk_flags)


def test_rank_advisors_attaches_same_assessment():
    s = _student(recommenders=[_rec()])
    ranked = rank_advisors(s, [_cand("top_10"), _cand("top_60_plus")], top_k=2)
    assert all(r.applicant is not None for r in ranked)
    assert ranked[0].applicant == ranked[1].applicant
