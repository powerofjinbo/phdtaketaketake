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

    result = compute_match(student, cand, field_profile_id="physics")
    assert result.field_profile_id == "physics"

    result_no_profile = compute_match(student, cand)
    assert result_no_profile.field_profile_id is None
