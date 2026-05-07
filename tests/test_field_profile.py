"""Tests for FieldProfile schema + loader."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.models import FieldProfile

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


# ---- Bundled-profile loading ----

def test_load_physics_directly():
    p = load_field_profile(DATA_DIR, "physics")
    assert p is not None
    assert p.id == "physics"
    assert "INSPIRE-HEP" in " ".join(p.primary_databases)


def test_load_via_alias_hep_resolves_to_physics():
    p = load_field_profile(DATA_DIR, "hep")
    assert p is not None
    assert p.id == "physics"


def test_load_via_alias_ml_resolves_to_cs():
    p = load_field_profile(DATA_DIR, "ml")
    assert p is not None
    assert p.id == "cs"


def test_load_via_alias_case_insensitive():
    p = load_field_profile(DATA_DIR, "Machine Learning")
    assert p is not None
    assert p.id == "cs"


def test_load_unknown_field_returns_none():
    p = load_field_profile(DATA_DIR, "futurology")
    assert p is None


def test_all_bundled_profiles_validate():
    """Every bundled YAML must parse against the FieldProfile model."""
    expected_ids = {"physics", "mse", "cs", "biology", "chemistry", "math"}
    profiles_dir = DATA_DIR / "field_profiles"
    found = set()
    for path in profiles_dir.glob("*.yaml"):
        p = load_field_profile(DATA_DIR, path.stem)
        assert p is not None, f"{path.name} failed to load"
        found.add(p.id)
    assert expected_ids.issubset(found), f"missing profiles: {expected_ids - found}"


# ---- Schema validation ----

def test_field_profile_rejects_unknown_venue_system():
    with pytest.raises(ValidationError):
        FieldProfile(
            id="x", display_name="X",
            venue_system="hieroglyphic",  # not a Literal value
        )


def test_field_profile_rejects_negative_big_collab_threshold():
    with pytest.raises(ValidationError):
        FieldProfile(
            id="x", display_name="X",
            venue_system="journal_first",
            big_collab_threshold=-1,
        )


def test_field_profile_rejects_unknown_extra_field():
    with pytest.raises(ValidationError):
        FieldProfile(
            id="x", display_name="X",
            venue_system="journal_first",
            unknown_field=True,  # extra='forbid'
        )


# ---- Field-specific calibration spot checks ----

def test_cs_uses_conference_first_venue_system():
    p = load_field_profile(DATA_DIR, "cs")
    assert p is not None
    assert p.venue_system == "conference_first"


def test_math_uses_preprint_first_venue_system():
    p = load_field_profile(DATA_DIR, "math")
    assert p is not None
    assert p.venue_system == "preprint_first"
    assert p.big_collab_threshold == 4   # math papers rarely have many authors


def test_biology_supports_co_first_authorship():
    p = load_field_profile(DATA_DIR, "biology")
    assert p is not None
    assert p.co_first_supported is True
    assert p.senior_author_position == "last"


def test_physics_does_not_support_co_first():
    p = load_field_profile(DATA_DIR, "physics")
    assert p is not None
    assert p.co_first_supported is False


# ---- compute_match records field_profile_id ----

def test_compute_match_records_field_profile_id():
    from phd_matcher.matching.ranker import compute_match
    from phd_matcher.models import (
        CandidateAdvisor,
        CurrentAdvisor,
        StudentProfile,
    )

    student = StudentProfile(
        field="physics",
        undergrad_institution="Tsinghua",
        gpa_raw=3.8,
        gpa_scale="4.0",
        research_direction="ATLAS Higgs",
        current_advisors=[CurrentAdvisor(id="adv_001", name="X", institution="Y")],
    )
    cand = CandidateAdvisor(
        id="c1", name="Prof. Z", institution="MIT",
        school_tier="top_10", field="physics",
    )

    profile = load_field_profile(DATA_DIR, "physics")
    assert profile is not None

    result = compute_match(student, cand, field_profile=profile)
    assert result.field_profile_id == "physics"

    result_no_profile = compute_match(student, cand)
    assert result_no_profile.field_profile_id is None


# ---- P1: field-aware paper scoring ----

def test_pub_score_co_first_author_role_treats_as_first():
    """Bio convention: 'These authors contributed equally' = first equivalent."""
    from phd_matcher.scoring.pub import paper_score

    # Tier 1 journal, byline position 3 — without role: tier 1 - 0.25 = 3.75
    plain = paper_score(1, 3)
    # Same paper but author_role='co_first' → effective position 1 → 4.0
    co_first = paper_score(1, 3, author_role="co_first")
    assert plain == 3.75
    assert co_first == 4.0


def test_pub_score_math_preprint_override_active():
    """Math FieldProfile activates preprint=0.9 (vs cross-field default 0.7)."""
    from phd_matcher.scoring.pub import paper_score

    math_profile = load_field_profile(DATA_DIR, "math")
    assert math_profile is not None

    default_preprint = paper_score(1, 1, status="preprint")
    math_preprint = paper_score(1, 1, status="preprint", field_profile=math_profile)
    # Default: 4.0 * 0.7 = 2.8
    # Math:    4.0 * 0.9 = 3.6
    assert default_preprint == 2.8
    assert math_preprint == 3.6


def test_pub_score_chemistry_preprint_uses_default_not_overridden():
    """Chemistry doesn't override preprint weight, so cross-field default applies."""
    from phd_matcher.scoring.pub import paper_score

    chem_profile = load_field_profile(DATA_DIR, "chemistry")
    assert chem_profile is not None
    assert "preprint" not in chem_profile.paper_status_weight_overrides

    chem_preprint = paper_score(1, 1, status="preprint", field_profile=chem_profile)
    assert chem_preprint == 2.8  # 4.0 * 0.7


# ---- P2: classify_coauthorship deterministic helper ----

def test_classify_coauthorship_uses_field_threshold():
    from phd_matcher.scoring.connection import classify_coauthorship

    physics_p = load_field_profile(DATA_DIR, "physics")
    math_p = load_field_profile(DATA_DIR, "math")

    # 6-author paper: small_team in physics (≤10), big_collab in math (>4)
    assert classify_coauthorship(6, physics_p) == "small_team"
    assert classify_coauthorship(6, math_p) == "big_collab"

    # No profile → default 10 threshold
    assert classify_coauthorship(8, None) == "small_team"
    assert classify_coauthorship(11, None) == "big_collab"


def test_classify_coauthorship_rejects_invalid_count():
    from phd_matcher.scoring.connection import classify_coauthorship

    with pytest.raises(ValueError):
        classify_coauthorship(0)


# ---- P0: field canonicalization (alias resolution + filter) ----

def test_match_alias_input_canonicalizes_field():
    """The bug: --field hep should match candidate.field='physics'."""
    import json
    import subprocess

    profile_json = {
        "field": "hep",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8, "gpa_scale": "4.0",
        "research_direction": "ATLAS Higgs",
        "current_advisors": [
            {"id": "adv_001", "name": "Prof. Wang", "institution": "Tsinghua"}
        ],
    }
    cands_json = [{
        "id": "c1", "name": "Prof. Test", "institution": "MIT",
        "school_tier": "top_10", "field": "physics",
        "research_areas": ["ATLAS"],
    }]

    result = subprocess.run(
        [
            "python3", str(REPO_ROOT / "scripts" / "match.py"),
            "--profile-json", json.dumps(profile_json),
            "--candidates-json", json.dumps(cands_json),
            "--field", "hep",
        ],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    # Before P0 fix: results would be [] (filter rejects field mismatch)
    # After fix: candidate is matched; field canonicalized to physics
    assert out["input_field"] == "hep"
    assert out["field_profile_id"] == "physics"
    assert len(out["results"]) == 1
    assert out["results"][0]["candidate"]["id"] == "c1"
