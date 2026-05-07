"""Tests for EvidenceCollector + scripts/collect_evidence.py (Sprint-3-c1).

All tests use fixture mode — no live HTTP. Live mode is exercised
implicitly by the OpenAlex API contract (urls / params), not by tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.evidence_collector import EvidenceCollector
from phd_matcher.matching.ranker import compute_match
from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    StudentProfile,
)
from phd_matcher.sources.openalex import OpenAlexAdapter

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
COLLECT_SCRIPT = REPO_ROOT / "scripts" / "collect_evidence.py"
DATA_DIR = REPO_ROOT / "data"


def _student_with_advisor() -> StudentProfile:
    return StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8, gpa_scale="4.0",
        research_direction="ATLAS Higgs",
        current_advisors=[CurrentAdvisor(
            id="adv_001", name="Prof. Wang",
            institution="Tsinghua University",
        )],
    )


def _bare_candidate(cid="c1", name="Prof. Y", institution="MIT") -> CandidateAdvisor:
    return CandidateAdvisor(
        id=cid, name=name, institution=institution,
        school_tier="top_10", field="physics",
    )


# ---- Adapter base behavior -----------------------------------------------

def test_openalex_adapter_offline_returns_none():
    """Without fixture_dir or live=True, adapter is a no-op."""
    a = OpenAlexAdapter()
    assert a.find_author("Prof. Y", "MIT") is None
    assert a.recent_works("A123") == []
    assert a.coauthored_works("A123", "A456") == []


def test_openalex_adapter_fixture_finds_author():
    """Fixture mode reads from disk."""
    a = OpenAlexAdapter(fixture_dir=FIXTURES)
    rec = a.find_author("Prof. Y", "MIT")
    assert rec is not None
    assert rec.source == "openalex"
    assert rec.id == "A_PROF_Y_MIT"
    assert "Higgs boson" in rec.concepts


def test_openalex_adapter_fixture_miss_records_error():
    """Missing fixture → None + error appended (so collector can surface it)."""
    a = OpenAlexAdapter(fixture_dir=FIXTURES)
    rec = a.find_author("Nobody", "Nowhere")
    assert rec is None
    assert any("fixture miss" in e for e in a.errors)


# ---- research_areas filling ---------------------------------------------

def test_collect_evidence_fills_research_areas_from_concepts():
    student = _student_with_advisor()
    cand = _bare_candidate()    # research_areas empty by default
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026,
        field_profile=physics,
    )
    enriched = collector.collect_for_candidate(student, cand)

    assert enriched.research_areas, "research_areas should be filled"
    assert "Higgs boson" in enriched.research_areas
    # Evidence attached
    assert "research_areas" in enriched.evidence
    items = enriched.evidence["research_areas"].items
    assert items
    assert items[0].source_type == "openalex"
    assert "research_areas" in items[0].supports_fields


def test_collect_evidence_skips_already_filled_research_areas():
    """Agent's manual research_areas wins — collector does NOT overwrite."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.research_areas = ["agent-set", "topic"]
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)
    assert cand.research_areas == ["agent-set", "topic"]


# ---- paths_to_advisors filling ------------------------------------------

def test_collect_evidence_fills_path_from_coauthored_works():
    """Fixture has 3 coauthored works (2 small-team, 1 big-collab) → counts
    + most_recent_connection_year set."""
    student = _student_with_advisor()
    cand = _bare_candidate()
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)

    edge = cand.paths_to_advisors.get("adv_001")
    assert edge is not None
    # Physics threshold is 10; fixtures have author_counts 6, 8, 312
    # → 2 small-team (≤10) + 1 big-collab (>10)
    assert edge.small_team_coauthor_5y == 2
    assert edge.big_collab_papers_5y == 1
    assert edge.most_recent_connection_year == 2024
    # Evidence attached
    assert edge.items
    assert "small_team_coauthor_5y" in edge.items[0].supports_fields
    assert "big_collab_papers_5y" in edge.items[0].supports_fields


def test_collect_evidence_records_verified_empty_path():
    """Adapter returns 0 coauthored works → verified-empty path with
    supports_fields=['path:<id>']."""
    student = _student_with_advisor()
    # Use a candidate fixture (Prof. Z) that has no coauthored fixture
    # with the advisor (Prof. Wang).
    cand = _bare_candidate(cid="c2", name="Prof. Z", institution="Stanford University")
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)

    edge = cand.paths_to_advisors.get("adv_001")
    assert edge is not None
    # No edge fields set (verified-empty)
    assert not edge.has_any_edge
    # supports_fields=['path:<adv_id>'] per strict-mode contract
    assert edge.items
    assert "path:adv_001" in edge.items[0].supports_fields


def test_collect_evidence_skips_path_when_already_populated():
    """If the agent already filled paths_to_advisors[adv_id] with an
    edge, collector does NOT overwrite."""
    from phd_matcher.models import PathEdge

    student = _student_with_advisor()
    cand = _bare_candidate()
    cand.paths_to_advisors["adv_001"] = PathEdge(small_team_coauthor_5y=99)
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)
    assert cand.paths_to_advisors["adv_001"].small_team_coauthor_5y == 99


# ---- Author-not-found path ---------------------------------------------

def test_collect_evidence_unresolved_when_author_not_found():
    """Adapter can't find the candidate → unresolved entry, no fields filled."""
    student = _student_with_advisor()
    cand = _bare_candidate(cid="ghost", name="Prof. Ghost", institution="Nowhere")
    physics = load_field_profile(DATA_DIR, "physics")

    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)

    summary = collector.summary()
    queue_signals = {e["signal"] for e in summary["unresolved_repair_queue"]}
    assert "author_lookup" in queue_signals


# ---- Strategy/scoring invariant -----------------------------------------

def test_collect_evidence_does_not_modify_scores():
    """The collector adds evidence but does NOT change scores. Re-running
    compute_match on enriched candidates produces consistent scores
    derived from the (now richer) inputs."""
    student = _student_with_advisor()
    cand_pre = _bare_candidate()
    cand_pre.research_areas = ["physics"]    # set so collector skips this field
    physics = load_field_profile(DATA_DIR, "physics")

    # Score BEFORE enrichment — only path missing.
    r_before = compute_match(student, cand_pre, field_profile=physics)

    # Enrich (collector fills paths_to_advisors)
    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand_pre)
    r_after = compute_match(student, cand_pre, field_profile=physics)

    # The collector adds path data (which legitimately raises C),
    # but does NOT invent any score directly. Verify via the structural
    # invariant: scores are determined by inputs through the existing
    # scoring pipeline. Specifically, the collector did NOT touch any
    # of the scoring sub-components directly.
    # C must change because the path is now populated; A / G should not.
    assert r_after.a_score == r_before.a_score
    assert r_after.g_score == r_before.g_score
    assert r_after.p_score == r_before.p_score
    # And c_score should reflect the newly-populated path
    assert r_after.c_score >= r_before.c_score


# ---- Summary correctness -----------------------------------------------

def test_collect_evidence_summary_counts_correct():
    student = _student_with_advisor()
    cand = _bare_candidate()
    physics = load_field_profile(DATA_DIR, "physics")
    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)
    s = collector.summary()
    assert s["fields_attempted"] == s["fields_filled"] + s["fields_unresolved"]
    # All operations should have succeeded (research_areas + 1 path)
    assert s["fields_filled"] >= 2


def test_collect_evidence_source_errors_surface_fixture_misses():
    student = _student_with_advisor()
    cand = _bare_candidate(cid="ghost", name="Prof. Ghost", institution="Nowhere")
    physics = load_field_profile(DATA_DIR, "physics")
    collector = EvidenceCollector(
        OpenAlexAdapter(fixture_dir=FIXTURES),
        current_year=2026, field_profile=physics,
    )
    collector.collect_for_candidate(student, cand)
    s = collector.summary()
    # Fixture-miss errors propagate from adapter.errors → summary.source_errors
    assert s["source_errors"]
    assert any("fixture miss" in e for e in s["source_errors"])


# ---- CLI subprocess tests ------------------------------------------------

def test_cli_emits_enriched_candidates(tmp_path):
    """End-to-end CLI: fixture mode populates paths_to_advisors and
    emits a JSON with collection_summary."""
    profile = {
        "field": "physics",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "ATLAS Higgs",
        "current_advisors": [{
            "id": "adv_001", "name": "Prof. Wang",
            "institution": "Tsinghua University",
        }],
    }
    candidates = [{
        "id": "c1", "name": "Prof. Y", "institution": "MIT",
        "school_tier": "top_10", "field": "physics",
    }]
    pf = tmp_path / "p.json"
    cf = tmp_path / "c.json"
    out_path = tmp_path / "enriched.json"
    pf.write_text(json.dumps(profile))
    cf.write_text(json.dumps(candidates))

    result = subprocess.run(
        [
            sys.executable, str(COLLECT_SCRIPT),
            "--profile-file", str(pf),
            "--candidates-file", str(cf),
            "--field", "physics",
            "--fixture-dir", str(FIXTURES),
            "--out", str(out_path),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(out_path.read_text())
    assert out["adapter"] == "openalex"
    assert out["mode"] == "fixture"
    assert "candidates" in out
    assert "collection_summary" in out

    cs = out["collection_summary"]
    for key in (
        "fields_attempted", "fields_filled", "fields_unresolved",
        "source_errors", "unresolved_repair_queue", "filled_log",
    ):
        assert key in cs

    enriched = out["candidates"][0]
    assert enriched["paths_to_advisors"]["adv_001"]["small_team_coauthor_5y"] == 2


def test_cli_offline_mode_returns_unresolved(tmp_path):
    """No --fixture-dir, no --live → adapter returns nothing. Every
    field becomes unresolved; collection_summary surfaces this."""
    profile = {
        "field": "physics", "undergrad_institution": "X",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "physics",
    }
    candidates = [{
        "id": "c1", "name": "P", "institution": "MIT",
        "school_tier": "top_10", "field": "physics",
    }]
    pf = tmp_path / "p.json"
    cf = tmp_path / "c.json"
    pf.write_text(json.dumps(profile))
    cf.write_text(json.dumps(candidates))
    result = subprocess.run(
        [
            sys.executable, str(COLLECT_SCRIPT),
            "--profile-file", str(pf),
            "--candidates-file", str(cf),
            "--field", "physics",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert out["mode"] == "offline"
    cs = out["collection_summary"]
    # author_lookup unresolvable → at least 1 unresolved entry
    assert cs["fields_unresolved"] >= 1


def test_cli_errors_on_empty_candidates(tmp_path):
    profile = {
        "field": "physics", "undergrad_institution": "X",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "physics",
    }
    pf = tmp_path / "p.json"
    cf = tmp_path / "c.json"
    pf.write_text(json.dumps(profile))
    cf.write_text("[]")
    result = subprocess.run(
        [
            sys.executable, str(COLLECT_SCRIPT),
            "--profile-file", str(pf),
            "--candidates-file", str(cf),
            "--field", "physics",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "error" in out
