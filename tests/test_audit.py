"""End-to-end tests for `scripts/audit_candidates.py` (roadmap #5/#6a)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_candidates.py"


def _student_profile() -> dict:
    return {
        "field": "physics",
        "undergrad_institution": "Tsinghua",
        "gpa_raw": 3.8,
        "gpa_scale": "4.0",
        "research_direction": "ATLAS Higgs analysis",
    }


def _bare_candidate(cid="c1") -> dict:
    return {
        "id": cid,
        "name": f"Prof. {cid}",
        "institution": "MIT",
        "school_tier": "top_10",
        "field": "physics",
    }


def _run_audit(
    tmp_path: Path,
    profile: dict,
    candidates: list[dict],
    *extra: str,
) -> subprocess.CompletedProcess:
    pf = tmp_path / "profile.json"
    cf = tmp_path / "cands.json"
    pf.write_text(json.dumps(profile))
    cf.write_text(json.dumps(candidates))
    return subprocess.run(
        [
            sys.executable, str(AUDIT_SCRIPT),
            "--profile-file", str(pf),
            "--candidates-file", str(cf),
            "--field", "physics",
            *extra,
        ],
        capture_output=True, text=True, check=False,
    )


# ---- Output shape --------------------------------------------------------

def test_audit_output_shape(tmp_path):
    result = _run_audit(tmp_path, _student_profile(), [_bare_candidate()])
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout)
    for key in (
        "input_field", "field_profile_id", "strict_evidence_mode",
        "strict_ready", "blocking_issues", "repair_queue",
        "coverage_summary", "input_warnings",
    ):
        assert key in out, f"missing key {key} in audit output"


def test_audit_repair_queue_entry_shape(tmp_path):
    """Each repair_queue entry has candidate_id / signal / severity /
    kind / hint."""
    result = _run_audit(tmp_path, _student_profile(), [_bare_candidate()])
    out = json.loads(result.stdout)
    assert out["repair_queue"], "expected repair entries for a bare candidate"
    for entry in out["repair_queue"]:
        for key in ("candidate_id", "signal", "severity", "kind", "hint"):
            assert key in entry, f"repair_queue entry missing {key}"
        assert entry["severity"] in ("high", "medium")
        assert entry["kind"] in ("unsourced", "missing")


# ---- Severity classification --------------------------------------------

def test_audit_unsourced_is_high_severity(tmp_path):
    """A candidate with school_tier set (always required) but no
    evidence → unsourced school_tier → severity high."""
    result = _run_audit(tmp_path, _student_profile(), [_bare_candidate()])
    out = json.loads(result.stdout)
    high_entries = [
        e for e in out["repair_queue"] if e["severity"] == "high"
    ]
    school_high = next(
        (e for e in high_entries if e["signal"] == "school_tier"), None,
    )
    assert school_high is not None
    assert school_high["kind"] == "unsourced"


def test_audit_missing_advisor_signal_is_medium(tmp_path):
    """Defaulted advisor-influence signals (None) are missing-required
    → severity medium."""
    result = _run_audit(tmp_path, _student_profile(), [_bare_candidate()])
    out = json.loads(result.stdout)
    medium_entries = [e for e in out["repair_queue"] if e["severity"] == "medium"]
    medium_signals = {e["signal"] for e in medium_entries}
    # The bare candidate has these advisor signals at default → missing.
    assert "normalized_collab_top20pct" in medium_signals
    assert "grad_placement_quality" in medium_signals


# ---- strict_ready boolean -----------------------------------------------

def test_audit_strict_ready_false_for_bare_candidate(tmp_path):
    result = _run_audit(
        tmp_path, _student_profile(), [_bare_candidate()],
        "--strict-evidence",
    )
    # Bare candidate has school_tier always required + no evidence → unsourced
    assert result.returncode == 2, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert out["strict_evidence_mode"] is True
    assert out["strict_ready"] is False
    assert out["blocking_issues"]  # non-empty


def test_audit_strict_ready_true_for_fully_sourced(tmp_path):
    """A candidate with school_tier evidence + all advisor signals at
    None (missing, but allowed in strict) → strict_ready=True."""
    cand = _bare_candidate()
    cand["evidence"] = {
        "school_tier": {
            "items": [{
                "url": "https://www.usnews.com/best-graduate-schools/...",
                "source_type": "us_news",
                "claim": "MIT physics top 10",
                "supports_fields": ["school_tier"],
            }],
        },
    }
    result = _run_audit(
        tmp_path, _student_profile(), [cand],
        "--strict-evidence",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = json.loads(result.stdout)
    assert out["strict_ready"] is True
    assert out["blocking_issues"] == []


# ---- Coverage summary ---------------------------------------------------

def test_audit_coverage_summary_counts(tmp_path):
    """Three candidates → counts reflect each."""
    cands = [
        _bare_candidate("c1"),
        _bare_candidate("c2"),
        _bare_candidate("c3"),
    ]
    result = _run_audit(tmp_path, _student_profile(), cands)
    out = json.loads(result.stdout)
    cs = out["coverage_summary"]
    assert cs["candidates_total"] == 3
    assert cs["candidates_strict_ready"] == 0  # all bare → all unsourced
    assert cs["candidates_with_unsourced"] == 3
    # Each candidate has the same gaps; total verified is 0.
    assert cs["verified_count"] == 0
    # missing + unsourced = total signals across candidates
    assert (
        cs["missing_count"] + cs["unsourced_count"] == cs["total_signals_audited"]
    )


def test_audit_coverage_summary_by_signal(tmp_path):
    """`by_signal` aggregates counts of unsourced/missing per signal name."""
    cands = [_bare_candidate("c1"), _bare_candidate("c2")]
    result = _run_audit(tmp_path, _student_profile(), cands)
    out = json.loads(result.stdout)
    by_signal = out["coverage_summary"]["by_signal"]
    # Both candidates have school_tier set with no evidence → 2 unsourced
    assert by_signal["school_tier"]["unsourced"] == 2


# ---- input_warnings flow through ----------------------------------------

def test_audit_propagates_input_warnings(tmp_path):
    """co_first in physics → warning surfaces in audit output too."""
    profile = {
        **_student_profile(),
        "papers": [{
            "journal_tier": 1, "author_position": 1,
            "author_role": "co_first",
        }],
    }
    result = _run_audit(tmp_path, profile, [_bare_candidate()])
    out = json.loads(result.stdout)
    assert any("co_first" in w for w in out["input_warnings"])


# ---- Repair hints quality -----------------------------------------------

def test_audit_repair_hint_for_program_signal_points_correctly(tmp_path):
    """A set program signal without evidence → repair hint must direct
    the agent at `program_profile.evidence['<field>']`."""
    cand = _bare_candidate()
    cand["program_profile"] = {
        "funding_structure": "pi_grant",  # set, no evidence
    }
    result = _run_audit(tmp_path, _student_profile(), [cand])
    out = json.loads(result.stdout)
    fund_entry = next(
        (e for e in out["repair_queue"]
         if e["signal"] == "program:funding_structure"),
        None,
    )
    assert fund_entry is not None
    assert fund_entry["severity"] == "high"
    assert "program_profile.evidence['funding_structure']" in fund_entry["hint"]


def test_audit_repair_hint_for_opportunity_signal_points_correctly(tmp_path):
    """A set opportunity opt-in field without evidence → repair hint
    must direct the agent at `opportunity_signal.evidence['<field>']`."""
    cand = _bare_candidate()
    cand["opportunity_signal"] = {
        "lab_open_positions": 2,  # set, no evidence
    }
    result = _run_audit(tmp_path, _student_profile(), [cand])
    out = json.loads(result.stdout)
    pos_entry = next(
        (e for e in out["repair_queue"]
         if e["signal"] == "opportunity:lab_open_positions"),
        None,
    )
    assert pos_entry is not None
    assert pos_entry["severity"] == "high"
    assert "opportunity_signal.evidence['lab_open_positions']" in pos_entry["hint"]


# ---- Empty candidates / error handling ----------------------------------

def test_audit_errors_on_empty_candidates(tmp_path):
    result = _run_audit(tmp_path, _student_profile(), [])
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert "error" in out
