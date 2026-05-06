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

Output: JSON list of MatchResult records to stdout.
Errors: JSON object { "error": "..." } to stdout, non-zero exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from phd_matcher.matching.ranker import rank_advisors  # noqa: E402
from phd_matcher.models import CandidateAdvisor, StudentProfile  # noqa: E402


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
            "Run the phdtaketaketake matcher and print ranked candidates as JSON. "
            "Both profile and candidates must be provided — there is no static cache."
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

    results = rank_advisors(student, candidates, top_k=args.top_k)
    output = [r.model_dump(mode="json") for r in results]
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
