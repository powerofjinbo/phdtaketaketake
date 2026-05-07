"""Tests for ranker.count_unverified_signals (post-review #1)."""


from phd_matcher.matching.ranker import count_unverified_signals
from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    EvidenceEntry,
    PathEdge,
    StudentProfile,
)


def _student_with_advisor():
    return StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS Higgs analysis",
        current_advisors=[CurrentAdvisor(id="adv_001", name="Prof. X", institution="THU")],
    )


def _bare_candidate():
    return CandidateAdvisor(
        id="c1", name="Prof. Y", institution="MIT", school_tier="top_10",
        field="physics",
    )


def test_unverified_count_all_missing():
    """Brand-new candidate with no evidence → max unverified count."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # 1 path missing + 3 field-strength missing + 1 pi=missing = 5
    assert count_unverified_signals(student, cand) == 5


def test_unverified_count_all_verified():
    """Fully sourced candidate → 0 unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            small_team_coauthor_5y=3,
            sources=["https://scholar.google.com/..."],
        ),
    }
    cand.normalized_collab_top20pct = 0.7
    cand.collab_with_nas = True
    cand.grad_placement_quality = 0.8
    cand.pi_signal = "normal"
    cand.evidence = {
        "normalized_collab_top20pct": EvidenceEntry(sources=["https://scholar.google.com/..."]),
        "collab_with_nas": EvidenceEntry(sources=["https://www.nasonline.org/..."]),
        "grad_placement_quality": EvidenceEntry(sources=["https://lab.mit.edu/alumni"]),
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/people"]),
    }
    assert count_unverified_signals(student, cand) == 0


def test_unverified_path_without_sources_counts():
    """Per #1: even non-default path edges without sources are unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(small_team_coauthor_5y=3),  # no sources
    }
    # 1 path (unsourced) + 3 field-strength + 1 pi = 5
    assert count_unverified_signals(student, cand) == 5


def test_unverified_pi_signal_non_missing_without_sources():
    """Per #1: pi_signal != 'missing' without evidence sources is unverified."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"  # claim without sources
    # 1 path missing + 3 field-strength + 1 pi (claimed without sources) = 5
    assert count_unverified_signals(student, cand) == 5


def test_unverified_pi_signal_non_missing_with_sources_is_verified():
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.pi_signal = "strong"
    cand.evidence = {
        "pi_signal": EvidenceEntry(sources=["https://lab.mit.edu/openings"]),
    }
    # 1 path missing + 3 field-strength + 0 pi = 4
    assert count_unverified_signals(student, cand) == 4


def test_unverified_field_strength_default_value_without_sources():
    """Per #1: even default values count as unverified without sources."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    # All field-strengths at default 0/false/0; pi missing
    assert count_unverified_signals(student, cand) == 5


def test_unverified_no_advisor_means_no_path_count():
    """Without a current advisor, paths_to_advisors isn't checked."""
    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS",
        # no current_advisors
    )
    cand = _bare_candidate()
    # 0 paths + 3 field-strength + 1 pi = 4
    assert count_unverified_signals(student, cand) == 4


def test_unverified_path_with_only_sources_and_note_is_verified():
    """Honest 'we searched, found nothing' record with sources is treated
    as verified, even if no edge fields are set."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors = {
        "adv_001": PathEdge(
            sources=["https://scholar.google.com/..."],
            note="searched OpenAlex + Math Genealogy: 0 co-authored papers, no shared lineage",
        ),
    }
    # 0 path + 3 field-strength + 1 pi = 4 (path verified-as-empty)
    assert count_unverified_signals(student, cand) == 4
