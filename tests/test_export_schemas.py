"""Tests for scripts/export_schemas.py + phd_matcher.cli.export_schemas
(Sprint-4-c3).

Verifies:
  - All exported models produce valid JSON Schema documents
  - Required top-level keys are present (`$schema` ish, `properties`,
    `type=object`, `$defs` for nested types)
  - Pydantic `extra="forbid"` shows up as `additionalProperties: false`
  - Important enum fields (school_tier, apply_bucket, etc.) are encoded
    as JSON Schema enums
  - The CLI writes one .schema.json per exported model
  - Checked-in schemas/*.json under repo root match what the exporter
    produces (drift detector — fails if Pydantic models change without
    regenerating)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from phd_matcher.cli.export_schemas import (
    EXPORTED_MODELS,
    export_schemas,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schemas.py"


def test_exports_one_file_per_model(tmp_path):
    written = export_schemas(tmp_path)
    assert len(written) == len(EXPORTED_MODELS)
    for model, path in zip(EXPORTED_MODELS, written, strict=True):
        assert path.exists()
        assert path.name == f"{model.__name__}.schema.json"


def test_each_schema_is_valid_json(tmp_path):
    written = export_schemas(tmp_path)
    for path in written:
        # Must parse as JSON (validates the export's serialization)
        json.loads(path.read_text())


def test_each_schema_has_object_shape(tmp_path):
    written = export_schemas(tmp_path)
    for path in written:
        schema = json.loads(path.read_text())
        assert schema.get("type") == "object", f"{path.name}: type != object"
        assert "properties" in schema, f"{path.name}: missing properties"
        # Pydantic emits the model name as the schema title
        assert schema.get("title") == path.name.replace(".schema.json", "")


def test_extra_forbid_emits_additional_properties_false(tmp_path):
    written = export_schemas(tmp_path)
    for path in written:
        schema = json.loads(path.read_text())
        # Top-level model uses extra="forbid"
        assert schema.get("additionalProperties") is False, (
            f"{path.name}: additionalProperties should be False "
            "(Pydantic extra='forbid')"
        )


def test_school_tier_enum_encoded():
    schema = json.loads(
        (SCHEMAS_DIR / "CandidateAdvisor.schema.json").read_text()
    )
    school_tier = schema["properties"]["school_tier"]
    # SchoolTier = Literal["top_10", "top_11_30", "top_31_60", "top_60_plus"]
    assert school_tier["enum"] == [
        "top_10", "top_11_30", "top_31_60", "top_60_plus",
    ]


def test_apply_bucket_enum_encoded():
    schema = json.loads(
        (SCHEMAS_DIR / "StrategyRecommendation.schema.json").read_text()
    )
    apply_bucket = schema["properties"]["apply_bucket"]
    assert set(apply_bucket["enum"]) == {
        "priority", "target", "reach", "only_if_space", "drop",
    }


def test_recommended_action_enum_encoded():
    schema = json.loads(
        (SCHEMAS_DIR / "StrategyRecommendation.schema.json").read_text()
    )
    action = schema["properties"]["recommended_action"]
    assert set(action["enum"]) == {
        "apply", "contact_first", "investigate_evidence",
        "deprioritize", "skip",
    }


def test_field_profile_research_fit_axes_is_array():
    schema = json.loads((SCHEMAS_DIR / "FieldProfile.schema.json").read_text())
    rfa = schema["properties"]["research_fit_axes"]
    # Pydantic represents `list[str]` as {"type": "array", "items": {"type": "string"}}
    assert rfa["type"] == "array"
    assert rfa["items"]["type"] == "string"


def test_research_fit_axes_bounded_in_candidate_advisor():
    """CandidateAdvisor.research_fit_axes: dict[str, float] with the
    field validator enforcing [0, 1]. The schema reports the dict shape;
    the [0,1] bound is enforced at validation time, not in the schema."""
    schema = json.loads(
        (SCHEMAS_DIR / "CandidateAdvisor.schema.json").read_text()
    )
    rfa = schema["properties"]["research_fit_axes"]
    # additionalProperties=number for dict[str, float]
    assert rfa["type"] == "object"


def test_research_fit_v2_axis_bounds_in_schema():
    """ResearchFit's individual axes have ge=0, le=1, which Pydantic
    encodes as minimum/maximum in the schema."""
    schema = json.loads((SCHEMAS_DIR / "ResearchFit.schema.json").read_text())
    topic = schema["properties"]["topic_fit"]
    assert topic["minimum"] == 0.0
    assert topic["maximum"] == 1.0


def test_match_result_includes_strategy_field():
    schema = json.loads((SCHEMAS_DIR / "MatchResult.schema.json").read_text())
    assert "strategy" in schema["properties"]


def test_cli_writes_files(tmp_path):
    """End-to-end: scripts/export_schemas.py --out <dir> writes the
    expected files."""
    result = subprocess.run(
        [
            sys.executable, str(EXPORT_SCRIPT),
            "--out", str(tmp_path),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    written = list(tmp_path.glob("*.schema.json"))
    assert len(written) == len(EXPORTED_MODELS)


def test_cli_list_flag():
    """`--list` works without `--out` (unlike write-mode where it's required)."""
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--list"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    names = result.stdout.strip().splitlines()
    assert "StudentProfile" in names
    assert "CandidateAdvisor" in names
    assert "MatchResult" in names


def test_cli_errors_without_out_or_list():
    """Without --out and without --list, the script errors (exit 2)."""
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "--out is required" in result.stderr


# ---- Drift detector ------------------------------------------------------

def test_checked_in_schemas_match_pydantic_source(tmp_path):
    """If this fails: Pydantic models drifted from `schemas/*.json`.
    Run `phdtaketaketake-export-schemas --out schemas/` to regenerate
    and commit the diff."""
    written = export_schemas(tmp_path)
    for path in written:
        regenerated = json.loads(path.read_text())
        checked_in_path = SCHEMAS_DIR / path.name
        assert checked_in_path.exists(), (
            f"missing checked-in schema: {checked_in_path.name}"
        )
        checked_in = json.loads(checked_in_path.read_text())
        assert regenerated == checked_in, (
            f"{path.name} differs from checked-in version. "
            "Run `phdtaketaketake-export-schemas --out schemas/` and commit."
        )
