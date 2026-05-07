"""End-to-end tests for `scripts/match.py`.

Subprocess-based so the actual CLI argument parsing and JSON output path
are exercised. These guard P0-level user-facing contracts:

- `input_warnings` always appears in the output JSON (success path)
- `input_warnings` survives a strict-evidence failure (the agent must
  see paper-role and axis-key warnings even when strict mode rejects
  unsourced claims, so a single fix-up pass can address both)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATCH_SCRIPT = REPO_ROOT / "scripts" / "match.py"


def _profile_with_co_first_in_physics() -> dict:
    """Physics profile whose paper uses `author_role='co_first'` — physics
    doesn't recognize co_first as a convention, so `validate_paper_roles`
    must surface a warning."""
    return {
        "field": "physics",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8,
        "gpa_scale": "4.0",
        "research_direction": "ATLAS Higgs analysis",
        "papers": [{
            "journal_tier": 1,
            "author_position": 1,
            "author_role": "co_first",
        }],
    }


def _bare_physics_candidate() -> dict:
    return {
        "id": "c1",
        "name": "Prof. Y",
        "institution": "MIT",
        "school_tier": "top_10",
        "field": "physics",
    }


def _run_cli(tmp_path: Path, profile: dict, candidates: list[dict],
             *extra: str) -> subprocess.CompletedProcess:
    profile_path = tmp_path / "profile.json"
    cands_path = tmp_path / "cands.json"
    profile_path.write_text(json.dumps(profile))
    cands_path.write_text(json.dumps(candidates))
    return subprocess.run(
        [
            sys.executable, str(MATCH_SCRIPT),
            "--profile-file", str(profile_path),
            "--candidates-file", str(cands_path),
            "--field", "physics", "--top-k", "1",
            *extra,
        ],
        capture_output=True, text=True, check=False,
    )


def test_cli_output_contains_input_warnings(tmp_path):
    """Success path: output JSON has top-level `input_warnings` listing
    co_first usage in physics."""
    result = _run_cli(
        tmp_path,
        _profile_with_co_first_in_physics(),
        [_bare_physics_candidate()],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert "input_warnings" in out
    assert any("co_first" in w for w in out["input_warnings"])


def test_cli_strict_fail_still_includes_input_warnings(tmp_path):
    """Strict-fail path: the candidate is unsourced (school_tier alone
    is enough to fail), so the script returns code 2 with a structured
    error JSON. That JSON must still include `input_warnings` — paper
    issues are orthogonal to evidence gaps and the agent shouldn't have
    to fix one to discover the other."""
    result = _run_cli(
        tmp_path,
        _profile_with_co_first_in_physics(),
        [_bare_physics_candidate()],
        "--strict-evidence",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert out.get("error", "").startswith("strict-evidence:")
    assert "input_warnings" in out
    assert any("co_first" in w for w in out["input_warnings"])
