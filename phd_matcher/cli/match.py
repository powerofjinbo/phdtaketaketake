#!/usr/bin/env python3
"""Run the matcher: profile JSON in + candidates JSON in → ranked JSON out.

This skill has **no static candidate cache**. The agent (Claude / Codex /
Cursor / etc.) gathers candidate advisors via real-time web research,
constructs CandidateAdvisor records inline, and pipes them here. See
`SKILL.md` and `references/profile_schema.md` for the deep-research
workflow and CandidateAdvisor schema.

Three invocation styles:

    python scripts/match.py \\
        --profile-file profile.json \\
        --candidates-file cands.json \\
        --field physics --top-k 10

    python scripts/match.py \\
        --profile-json '{...}' \\
        --candidates-json '[...]' \\
        --field chemistry

    cat profile.json | python scripts/match.py \\
        --candidates-file cands.json --field biology

Strict mode:

    python scripts/match.py ... --strict-evidence

Strict mode rejects any candidate that has *unsourced* claims (a value set
without an EvidenceEntry). Missing signals are still allowed — that's a
legitimate "I couldn't verify this" state. See SKILL.md for full rules.

Output: JSON list of MatchResult records to stdout.
Errors: JSON object { "error": "..." } to stdout, non-zero exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.ranker import (
    rank_advisors,
    strict_validate,
    validate_research_fit_axes,
)
from phd_matcher.matching.strategy import summarize_portfolio
from phd_matcher.models import CandidateAdvisor, StudentProfile
from phd_matcher.scoring.pub import validate_paper_roles

# Sprint-3-c5: when installed as a package, data/ ships at repo root
# alongside the phd_matcher/ package. Two parents up from this file
# (phd_matcher/cli/<this>.py → phd_matcher/cli → phd_matcher → repo) is
# the project root.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def _load_profile(args) -> dict:
    if args.profile_file:
        return json.loads(args.profile_file.read_text())
    if args.profile_json:
        return json.loads(args.profile_json)
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    raise SystemExit(
        "provide --profile-file, --profile-json, or pipe profile JSON via stdin"
    )


def _load_candidates(args) -> list[CandidateAdvisor]:
    if args.candidates_file:
        data = json.loads(args.candidates_file.read_text())
    elif args.candidates_json:
        data = json.loads(args.candidates_json)
    else:
        raise SystemExit(
            "candidates required: pass --candidates-file or --candidates-json. "
            "This skill has no static cache — the agent should gather candidates "
            "via web search per SKILL.md and pass them here as JSON."
        )
    return [CandidateAdvisor(**c) for c in data]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Run the phdtaketaketake matcher and print ranked candidates as JSON."
        )
    )
    ap.add_argument("--profile-file", type=Path, help="Path to a profile JSON file")
    ap.add_argument("--profile-json", type=str, help="Profile JSON string")
    ap.add_argument(
        "--field",
        required=True,
        help="Target STEM field (any string, e.g. physics, chemistry, biology, cs)",
    )
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument(
        "--candidates-file",
        type=Path,
        help="Path to a JSON array of CandidateAdvisor records (gathered via web research)",
    )
    ap.add_argument(
        "--candidates-json",
        type=str,
        help="Inline JSON array of CandidateAdvisor records",
    )
    ap.add_argument(
        "--strict-evidence",
        action="store_true",
        help=(
            "Reject any candidate with unsourced claims (value set without "
            "evidence). Missing signals (no value, no evidence) are still "
            "allowed — they're honest 'I couldn't verify' states."
        ),
    )
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DATA_DIR,
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

    # Resolve field profile (alias-aware) and CANONICALIZE student.field
    # to the profile id, so candidate filtering survives alias inputs
    # like --field hep + candidate.field=physics. (P0 fix.)
    field_profile = load_field_profile(args.data_dir, args.field)
    input_field = student.field
    if field_profile and student.field != field_profile.id:
        student.field = field_profile.id

    # Canonicalize candidate fields too — agents may emit aliases.
    if field_profile:
        for cand in candidates:
            if cand.field == field_profile.id:
                continue
            cand_profile = load_field_profile(args.data_dir, cand.field)
            if cand_profile and cand_profile.id == field_profile.id:
                cand.field = field_profile.id

    # Compute input_warnings BEFORE the strict gate, so they survive a
    # strict-fail return and the agent can fix profile/candidate inputs in
    # the same pass it fixes missing evidence. Two sources:
    #   - paper-role warnings (e.g., co_first used in physics)
    #   - research-fit-axis warnings (axis key not declared by the
    #     active FieldProfile)
    input_warnings = validate_paper_roles(
        [pp.model_dump() for pp in student.papers],
        field_profile=field_profile,
    )
    input_warnings.extend(
        validate_research_fit_axes(candidates, field_profile=field_profile)
    )

    # Strict mode: reject any candidate with unsourced claims.
    if args.strict_evidence:
        all_errors: list[str] = []
        for cand in candidates:
            all_errors.extend(strict_validate(student, cand))
        if all_errors:
            json.dump(
                {
                    "error": "strict-evidence: unsourced claims detected",
                    "details": all_errors,
                    "input_field": input_field,
                    "field_profile_id": field_profile.id if field_profile else None,
                    "input_warnings": input_warnings,
                },
                sys.stdout,
                indent=2,
                ensure_ascii=False,
            )
            sys.stdout.write("\n")
            return 2

    results = rank_advisors(
        student,
        candidates,
        top_k=args.top_k,
        field_profile=field_profile,
    )
    # Sprint-2-c5: portfolio-level strategy summary. Per-candidate
    # `strategy` field is already attached by `compute_match`.
    strategy_summary = summarize_portfolio(results)
    output: dict = {
        "input_field": input_field,
        "field_profile_id": field_profile.id if field_profile else None,
        "field_caveats": field_profile.caveats if field_profile else [],
        "input_warnings": input_warnings,
        "strategy_summary": strategy_summary.model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in results],
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
