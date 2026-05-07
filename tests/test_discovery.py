"""Tests for build_discovery_plan + scripts/build_discovery_plan.py
(Sprint-2-c4)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.discovery import (
    EXCLUSION_RULES,
    build_discovery_plan,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCOVERY_SCRIPT = REPO_ROOT / "scripts" / "build_discovery_plan.py"
DATA_DIR = REPO_ROOT / "data"


# ---- Library-level tests -------------------------------------------------

def test_plan_includes_per_field_recipes_for_physics():
    """Physics-specific engines (INSPIRE, ATLAS Glance) appear in the plan."""
    physics = load_field_profile(DATA_DIR, "physics")
    plan = build_discovery_plan(
        field="physics",
        schools=["MIT"],
        keywords="ATLAS Higgs",
        field_profile=physics,
    )
    engines = {q["engine"] for q in plan["queries"]}
    assert "inspire" in engines
    assert "atlas_glance" in engines
    assert "arxiv" in engines


def test_plan_includes_per_field_recipes_for_cs():
    """CS-specific engines (DBLP, OpenReview, CSRankings) appear."""
    cs = load_field_profile(DATA_DIR, "cs")
    plan = build_discovery_plan(
        field="cs", schools=["MIT"], keywords="multi-agent RL",
        field_profile=cs,
    )
    engines = {q["engine"] for q in plan["queries"]}
    assert "dblp" in engines
    assert "openreview" in engines
    assert "csrankings" in engines


def test_plan_includes_per_field_recipes_for_biology():
    """Biology engines (PubMed, bioRxiv, NIH RePORTER, HHMI)."""
    bio = load_field_profile(DATA_DIR, "biology")
    plan = build_discovery_plan(
        field="biology", schools=["Harvard"], keywords="CRISPR cancer",
        field_profile=bio,
    )
    engines = {q["engine"] for q in plan["queries"]}
    assert "pubmed" in engines
    assert "biorxiv" in engines
    assert "nih_reporter" in engines
    assert "hhmi" in engines


def test_plan_includes_per_field_recipes_for_math():
    """Math engines (arXiv, Math Genealogy Project)."""
    math = load_field_profile(DATA_DIR, "math")
    plan = build_discovery_plan(
        field="math", schools=["Princeton"], keywords="algebraic geometry",
        field_profile=math,
    )
    engines = {q["engine"] for q in plan["queries"]}
    assert "arxiv" in engines
    assert "math_genealogy" in engines


def test_plan_per_school_query_expansion():
    """3 schools × N field recipes → 3·N queries."""
    cs = load_field_profile(DATA_DIR, "cs")
    plan = build_discovery_plan(
        field="cs", schools=["MIT", "Stanford", "Berkeley"],
        keywords="LLMs", field_profile=cs,
    )
    # CS has 6 recipes (dblp/openreview/semantic_scholar/csrankings/faculty_page/arxiv)
    assert len(plan["queries"]) == 3 * 6


def test_plan_includes_universal_exclusion_rules():
    physics = load_field_profile(DATA_DIR, "physics")
    plan = build_discovery_plan(
        field="physics", schools=["MIT"], keywords="ATLAS",
        field_profile=physics,
    )
    assert plan["exclusion_rules"] == EXCLUSION_RULES
    assert any("emeritus" in r for r in plan["exclusion_rules"])
    assert any("not recruiting" in r for r in plan["exclusion_rules"])


def test_plan_carries_primary_databases_and_ranking_source():
    """The plan surfaces the loaded FieldProfile's primary_databases
    and ranking_source_url so the agent can cross-reference."""
    cs = load_field_profile(DATA_DIR, "cs")
    plan = build_discovery_plan(
        field="cs", schools=["MIT"], keywords="...", field_profile=cs,
    )
    assert plan["primary_databases"]   # non-empty for CS
    assert plan["ranking_source_url"] == "https://csrankings.org/"
    assert plan["field_profile_loaded"] is True


def test_plan_falls_back_to_generic_for_unknown_field():
    """Unknown field → generic Scholar + faculty_page queries.
    field_profile_loaded=False signals the fallback to the agent."""
    plan = build_discovery_plan(
        field="some_obscure_field", schools=["MIT"], keywords="xyz",
        field_profile=None,
    )
    engines = {q["engine"] for q in plan["queries"]}
    assert engines == {"google_scholar", "faculty_page"}
    assert plan["field_profile_loaded"] is False
    assert plan["primary_databases"] == []
    assert plan["ranking_source_url"] is None


def test_plan_carries_field_caveats():
    """Per-field caveats from the YAML flow through unchanged."""
    cs = load_field_profile(DATA_DIR, "cs")
    plan = build_discovery_plan(
        field="cs", schools=["MIT"], keywords="...", field_profile=cs,
    )
    assert any("Conferences" in c for c in plan["field_caveats"])


# ---- CLI subprocess tests ------------------------------------------------

def test_cli_emits_valid_json(tmp_path):
    """End-to-end: scripts/build_discovery_plan.py outputs valid JSON
    with the expected top-level shape."""
    schools_file = tmp_path / "schools.json"
    schools_file.write_text(json.dumps(["MIT", "Stanford"]))
    result = subprocess.run(
        [
            sys.executable, str(DISCOVERY_SCRIPT),
            "--field", "physics",
            "--schools-file", str(schools_file),
            "--keywords", "ATLAS Higgs",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    plan = json.loads(result.stdout)
    for key in (
        "field_profile_id", "field_display_name", "schools", "keywords",
        "queries", "primary_databases", "ranking_source_url",
        "field_caveats", "exclusion_rules", "field_profile_loaded",
    ):
        assert key in plan


def test_cli_inline_schools_arg(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(DISCOVERY_SCRIPT),
            "--field", "cs",
            "--schools", '["CMU", "MIT"]',
            "--keywords", "robotics",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    plan = json.loads(result.stdout)
    assert plan["schools"] == ["CMU", "MIT"]


def test_cli_errors_on_empty_schools(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(DISCOVERY_SCRIPT),
            "--field", "physics",
            "--schools", "[]",
            "--keywords", "xyz",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "error" in out


def test_cli_errors_on_malformed_schools_arg(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(DISCOVERY_SCRIPT),
            "--field", "physics",
            "--schools", "not-json",
            "--keywords", "xyz",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
