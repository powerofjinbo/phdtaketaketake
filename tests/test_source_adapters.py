"""Tests for the additional source adapters (Sprint-3-c3).

PubMed / DBLP / Semantic Scholar adapters share the OpenAlex pattern:
fixture-first, opt-in live mode. All tests use fixture mode — no
network calls.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from phd_matcher.sources import (
    ADAPTER_CLASSES,
    DEFAULT_ADAPTER_BY_FIELD,
    DBLPAdapter,
    OpenAlexAdapter,
    PubMedAdapter,
    SemanticScholarAdapter,
    default_adapter_for_field,
    select_adapter,
)
from phd_matcher.sources.base import FixtureLookup

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
COLLECT_SCRIPT = REPO_ROOT / "scripts" / "collect_evidence.py"


# ---- FixtureLookup helper ------------------------------------------------

def test_fixture_lookup_sanitize():
    s = FixtureLookup.sanitize
    assert s("Prof. Y") == "prof_y"
    assert s("MIT") == "mit"
    assert s("Stanford University") == "stanford_university"
    # leading/trailing underscores trimmed
    assert s("---hello---") == "hello"


def test_fixture_lookup_find_author_with_institution(tmp_path):
    base = tmp_path / "mysrc" / "find_author"
    base.mkdir(parents=True)
    (base / "prof_y__mit.json").write_text("{}")
    fl = FixtureLookup("mysrc", tmp_path)
    p = fl.find_author_path("Prof. Y", "MIT")
    assert p is not None and p.name == "prof_y__mit.json"


def test_fixture_lookup_find_author_fallback_no_institution(tmp_path):
    base = tmp_path / "mysrc" / "find_author"
    base.mkdir(parents=True)
    (base / "prof_y.json").write_text("{}")
    fl = FixtureLookup("mysrc", tmp_path)
    # With institution but no specific fixture → falls back to no-inst
    p = fl.find_author_path("Prof. Y", "Stanford")
    assert p is not None and p.name == "prof_y.json"


def test_fixture_lookup_coauthored_both_orderings(tmp_path):
    base = tmp_path / "mysrc" / "coauthored"
    base.mkdir(parents=True)
    (base / "a__b.json").write_text("[]")
    fl = FixtureLookup("mysrc", tmp_path)
    assert fl.coauthored_path("a", "b") is not None
    assert fl.coauthored_path("b", "a") is not None    # swapped order works


# ---- PubMed adapter -----------------------------------------------------

def test_pubmed_adapter_offline_returns_none():
    a = PubMedAdapter()
    assert a.find_author("Smith J") is None
    assert a.recent_works("X") == []
    assert a.coauthored_works("X", "Y") == []


def test_pubmed_adapter_fixture_finds_author():
    a = PubMedAdapter(fixture_dir=FIXTURES)
    rec = a.find_author("Dr. Smith", "Harvard")
    assert rec is not None
    assert rec.source == "pubmed"
    assert rec.h_index == 50


def test_pubmed_adapter_fixture_miss_records_error():
    a = PubMedAdapter(fixture_dir=FIXTURES)
    assert a.find_author("Nobody", "Nowhere") is None
    assert any("pubmed fixture miss" in e for e in a.errors)


# ---- DBLP adapter -------------------------------------------------------

def test_dblp_adapter_offline_returns_none():
    a = DBLPAdapter()
    assert a.find_author("Y. Bengio") is None


def test_dblp_adapter_fixture_finds_author():
    a = DBLPAdapter(fixture_dir=FIXTURES)
    rec = a.find_author("Dr. Chen", "CMU")
    assert rec is not None
    assert rec.source == "dblp"
    assert "reinforcement learning" in rec.concepts


def test_dblp_adapter_live_recent_works_v1_unimplemented():
    """v1 live mode for DBLP recent_works is intentionally unimplemented;
    the adapter records an explanatory error rather than silently
    returning empty (so the caller knows to use fixtures or wait for c5)."""
    a = DBLPAdapter(live=True)
    assert a.recent_works("some_id") == []
    assert any("not implemented" in e for e in a.errors)


# ---- Semantic Scholar adapter -------------------------------------------

def test_semantic_scholar_adapter_offline_returns_none():
    a = SemanticScholarAdapter()
    assert a.find_author("Some Author") is None


def test_semantic_scholar_adapter_fixture_finds_author():
    a = SemanticScholarAdapter(fixture_dir=FIXTURES)
    rec = a.find_author("Dr. Lee", "Stanford")
    assert rec is not None
    assert rec.source == "semantic_scholar"
    assert rec.h_index == 30
    assert "transformers" in rec.concepts


# ---- Adapter dispatcher -------------------------------------------------

def test_select_adapter_by_name():
    a = select_adapter("openalex")
    assert isinstance(a, OpenAlexAdapter)
    a = select_adapter("pubmed")
    assert isinstance(a, PubMedAdapter)
    a = select_adapter("dblp")
    assert isinstance(a, DBLPAdapter)
    a = select_adapter("semantic_scholar")
    assert isinstance(a, SemanticScholarAdapter)


def test_select_adapter_unknown_name_raises():
    with pytest.raises(ValueError):
        select_adapter("nonexistent_source")


def test_select_adapter_passes_kwargs():
    """OpenAlex takes mailto; PubMed/SS take api_key. Unknown kwargs
    are silently dropped per adapter."""
    a = select_adapter("openalex", live=True, mailto="me@example.edu")
    assert isinstance(a, OpenAlexAdapter)
    assert a.mailto == "me@example.edu"
    assert a.live is True

    a2 = select_adapter("pubmed", live=True, api_key="ABC")
    assert isinstance(a2, PubMedAdapter)
    assert a2.api_key == "ABC"


def test_default_adapter_for_field_known():
    """Known field IDs map to specific adapters."""
    assert default_adapter_for_field("biology") == "pubmed"
    assert default_adapter_for_field("cs") == "semantic_scholar"
    assert default_adapter_for_field("physics") == "openalex"
    assert default_adapter_for_field("math") == "semantic_scholar"


def test_default_adapter_for_field_unknown_falls_back_openalex():
    assert default_adapter_for_field("some_obscure_field") == "openalex"
    assert default_adapter_for_field(None) == "openalex"


def test_adapter_classes_registry_complete():
    """Every adapter class is registered + mapped from at least one field."""
    assert "openalex" in ADAPTER_CLASSES
    assert "pubmed" in ADAPTER_CLASSES
    assert "dblp" in ADAPTER_CLASSES
    assert "semantic_scholar" in ADAPTER_CLASSES
    # Every field default is a registered adapter
    for field, adapter_name in DEFAULT_ADAPTER_BY_FIELD.items():
        assert adapter_name in ADAPTER_CLASSES, f"{field}→{adapter_name} not registered"


# ---- CLI --source flag --------------------------------------------------

def test_cli_source_flag_overrides_default(tmp_path):
    """Passing `--source pubmed` overrides the per-field default."""
    profile = {
        "field": "biology", "undergrad_institution": "X",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "CRISPR cancer",
        "current_advisors": [{"id": "adv_001", "name": "Adv",
                              "institution": "Y"}],
    }
    candidates = [{
        "id": "c1", "name": "Dr. Smith", "institution": "Harvard",
        "school_tier": "top_10", "field": "biology",
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
            "--field", "biology",
            "--source", "pubmed",
            "--fixture-dir", str(FIXTURES),
            "--out", str(out_path),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(out_path.read_text())
    assert out["adapter"] == "pubmed"
    assert out["source"] == "pubmed"


def test_cli_default_adapter_picks_pubmed_for_biology(tmp_path):
    """Without --source, biology field defaults to PubMed."""
    profile = {
        "field": "biology", "undergrad_institution": "X",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "CRISPR",
    }
    candidates = [{
        "id": "c1", "name": "Dr. Smith", "institution": "Harvard",
        "school_tier": "top_10", "field": "biology",
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
            "--field", "biology",
            "--fixture-dir", str(FIXTURES),
            "--out", str(out_path),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(out_path.read_text())
    assert out["source"] == "pubmed"
