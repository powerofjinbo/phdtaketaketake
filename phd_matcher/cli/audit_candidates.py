#!/usr/bin/env python3
"""Audit a candidate batch's evidence quality (roadmap #5/#6a).

Standalone CLI that surfaces what's wrong with a candidates JSON
*before* the matcher runs — so the agent can fix evidence in one pass
rather than learning about it from a strict-evidence rejection.

Three groups of output:

  - `blocking_issues` — strict-mode rejections (per-candidate, with
    a fix hint pointing at the right evidence location).
  - `repair_queue`    — every signal that needs work, with severity:
      * `high`   — unsourced (set value with no `supports_fields` proof)
      * `medium` — missing required signal (information gap; widens band)
  - `coverage_summary` — portfolio-level rollup so the user sees how
    deep the gaps go before drilling into any one candidate.

The output JSON also propagates `input_warnings` (paper-role conventions
that don't match the field, axis-key drift in research_fit) so all the
"why this batch isn't ready yet" data lives in one place.

Usage:

    python scripts/audit_candidates.py \
        --profile-file profile.json \
        --candidates-file cands.json \
        --field physics \
        [--strict-evidence]

`--strict-evidence` toggles whether legacy bare `sources` URLs count
as proof. Same semantics as `scripts/match.py --strict-evidence`. When
the flag is set, `strict_ready=true` requires zero unsourced claims
across all candidates and the script exits non-zero if not ready.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.ranker import (
    EvidenceCoverage,
    evidence_coverage,
    repair_hint_for,
    strict_validate,
    validate_research_fit_axes,
)
from phd_matcher.models import (
    CandidateAdvisor,
    StudentProfile,
)
from phd_matcher.scoring.pub import validate_paper_roles

Severity = Literal["high", "medium"]
IssueKind = Literal["unsourced", "missing"]



# Sprint-3-c5: when installed as a package, data/ ships at repo root
# alongside the phd_matcher/ package. Two parents up from this file
# (phd_matcher/cli/<this>.py → phd_matcher/cli → phd_matcher → repo) is
# the project root.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def _load_profile(args: argparse.Namespace) -> dict:
    if args.profile_file:
        return json.loads(args.profile_file.read_text())
    if args.profile_json:
        return json.loads(args.profile_json)
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    raise SystemExit(
        "provide --profile-file, --profile-json, or pipe profile JSON via stdin"
    )


def _load_candidates(args: argparse.Namespace) -> list[CandidateAdvisor]:
    if args.candidates_file:
        data = json.loads(args.candidates_file.read_text())
    elif args.candidates_json:
        data = json.loads(args.candidates_json)
    else:
        raise SystemExit(
            "candidates required: pass --candidates-file or --candidates-json"
        )
    return [CandidateAdvisor(**c) for c in data]


def _build_repair_entries(
    candidate_id: str, cov: EvidenceCoverage
) -> list[dict]:
    """Per-candidate issues, each with severity + repair hint.

    Severity is `high` for unsourced (strict-mode blocker, hallucination
    risk) and `medium` for missing required (won't block strict but
    widens band). Opt-in fields don't appear here when not set —
    they're only in coverage when the agent has actually filled them.
    """
    out: list[dict] = []
    for name in cov.unsourced_names:
        out.append({
            "candidate_id": candidate_id,
            "signal": name,
            "severity": "high",
            "kind": "unsourced",
            "hint": repair_hint_for(name),
        })
    for name in cov.missing_names:
        out.append({
            "candidate_id": candidate_id,
            "signal": name,
            "severity": "medium",
            "kind": "missing",
            "hint": repair_hint_for(name),
        })
    return out


def _build_coverage_summary(
    cands_with_cov: list[tuple[str, EvidenceCoverage]],
) -> dict:
    """Portfolio-level rollup: how many candidates are strict-ready,
    how many have unsourced claims, how the per-signal coverage stacks."""
    total = len(cands_with_cov)
    strict_ready_count = sum(1 for _, c in cands_with_cov if c.unsourced == 0)
    with_unsourced = sum(1 for _, c in cands_with_cov if c.unsourced > 0)
    with_missing = sum(1 for _, c in cands_with_cov if c.missing > 0)

    # Per-signal aggregate (same signal name across candidates → tally
    # verified / missing / unsourced). Useful for spotting "every
    # candidate has the same gap" patterns.
    by_signal: dict[str, dict[str, int]] = {}
    for _, cov in cands_with_cov:
        verified_set: set[str] = set()
        # cov doesn't store verified_names directly; we reconstruct from
        # total minus the missing/unsourced names.
        all_names: set[str] = set(cov.missing_names) | set(cov.unsourced_names)
        # Total rather than per-name reconstruction — we know cov.verified
        # and the names of the non-verified, but not the names of the
        # verified themselves. For the by_signal rollup we add to the
        # missing/unsourced columns and infer verified from totals later.
        for n in cov.missing_names:
            by_signal.setdefault(n, {"verified": 0, "missing": 0, "unsourced": 0})
            by_signal[n]["missing"] += 1
        for n in cov.unsourced_names:
            by_signal.setdefault(n, {"verified": 0, "missing": 0, "unsourced": 0})
            by_signal[n]["unsourced"] += 1
        # Verified names aren't tracked individually on EvidenceCoverage,
        # so we can't fill the verified column here without re-walking.
        # That's a follow-up if needed; for now leave verified at 0 and
        # let the consumer compute it as `total_candidates - missing -
        # unsourced` for any specific signal name.
        _ = verified_set
        _ = all_names

    return {
        "candidates_total": total,
        "candidates_strict_ready": strict_ready_count,
        "candidates_with_unsourced": with_unsourced,
        "candidates_with_missing": with_missing,
        "total_signals_audited": sum(c.total for _, c in cands_with_cov),
        "verified_count": sum(c.verified for _, c in cands_with_cov),
        "missing_count": sum(c.missing for _, c in cands_with_cov),
        "unsourced_count": sum(c.unsourced for _, c in cands_with_cov),
        "by_signal": by_signal,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Audit a candidate batch's evidence quality before running "
            "the matcher. Surfaces blocking issues, a per-signal repair "
            "queue, and a portfolio-level coverage summary."
        ),
    )
    ap.add_argument("--profile-file", type=Path, help="Path to a profile JSON file")
    ap.add_argument("--profile-json", type=str, help="Inline profile JSON string")
    ap.add_argument(
        "--field", required=True,
        help="Target STEM field (e.g. physics, chemistry, biology, cs)",
    )
    ap.add_argument(
        "--candidates-file", type=Path,
        help="Path to a JSON array of CandidateAdvisor records",
    )
    ap.add_argument(
        "--candidates-json", type=str,
        help="Inline JSON array of CandidateAdvisor records",
    )
    ap.add_argument(
        "--strict-evidence", action="store_true",
        help=(
            "Use strict-mode evidence rules (bare `sources` URLs do not "
            "count). Sets the script's exit code to 2 if not all "
            "candidates are strict-ready."
        ),
    )
    ap.add_argument(
        "--data-dir", type=Path, default=_DEFAULT_DATA_DIR,
        help="Path to the data/ directory (for field profile lookup).",
    )
    args = ap.parse_args()

    try:
        profile_dict = _load_profile(args)
    except (json.JSONDecodeError, SystemExit) as e:
        json.dump({"error": f"profile: {e}"}, sys.stdout)
        return 2

    profile_dict.setdefault("field", args.field)

    try:
        student = StudentProfile(**profile_dict)
    except Exception as e:
        json.dump({"error": f"profile validation: {e}"}, sys.stdout)
        return 2

    try:
        candidates = _load_candidates(args)
    except SystemExit as e:
        json.dump({"error": str(e)}, sys.stdout)
        return 2
    except Exception as e:
        json.dump({"error": f"candidates: {e}"}, sys.stdout)
        return 2

    if not candidates:
        json.dump({"error": "candidates list is empty"}, sys.stdout)
        return 1

    # Resolve field profile + canonicalize fields (same logic as match.py)
    field_profile = load_field_profile(args.data_dir, args.field)
    input_field = student.field
    if field_profile and student.field != field_profile.id:
        student.field = field_profile.id
    if field_profile:
        for cand in candidates:
            if cand.field == field_profile.id:
                continue
            cand_profile = load_field_profile(args.data_dir, cand.field)
            if cand_profile and cand_profile.id == field_profile.id:
                cand.field = field_profile.id

    # Input-level warnings (paper roles + research_fit axis-key drift)
    input_warnings = validate_paper_roles(
        [pp.model_dump() for pp in student.papers],
        field_profile=field_profile,
    )
    input_warnings.extend(
        validate_research_fit_axes(candidates, field_profile=field_profile)
    )

    # Per-candidate audit
    cands_with_cov: list[tuple[str, EvidenceCoverage]] = []
    blocking_issues: list[str] = []
    repair_queue: list[dict] = []

    for cand in candidates:
        cov = evidence_coverage(student, cand, strict=args.strict_evidence)
        cands_with_cov.append((cand.id, cov))

        if args.strict_evidence:
            blocking_issues.extend(strict_validate(student, cand))

        repair_queue.extend(_build_repair_entries(cand.id, cov))

    coverage_summary = _build_coverage_summary(cands_with_cov)
    strict_ready = (
        coverage_summary["candidates_strict_ready"]
        == coverage_summary["candidates_total"]
    )

    output = {
        "input_field": input_field,
        "field_profile_id": field_profile.id if field_profile else None,
        "strict_evidence_mode": args.strict_evidence,
        "strict_ready": strict_ready,
        "blocking_issues": blocking_issues,
        "repair_queue": repair_queue,
        "coverage_summary": coverage_summary,
        "input_warnings": input_warnings,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    if args.strict_evidence and not strict_ready:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
