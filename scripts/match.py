#!/usr/bin/env python3
"""End-to-end matching: profile JSON in, ranked candidates JSON out.

Invocation styles:

    python scripts/match.py --profile-file profile.json --field physics --top-k 10
    python scripts/match.py --profile-json '{"field":"physics", ...}' --field physics
    cat profile.json | python scripts/match.py --field physics

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

from phd_matcher.data.loaders import load_advisors  # noqa: E402
from phd_matcher.matching.ranker import rank_advisors  # noqa: E402
from phd_matcher.models import CandidateAdvisor, StudentProfile  # noqa: E402


BUNDLED_FIELDS = {"physics", "mse"}


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


def _load_candidates(args) -> list[CandidateAdvisor] | None:
    """Return external candidates (override) if provided, else None for bundled cache."""
    if args.candidates_file:
        data = json.loads(args.candidates_file.read_text())
    elif args.candidates_json:
        data = json.loads(args.candidates_json)
    else:
        return None
    return [CandidateAdvisor(**c) for c in data]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Run the phdtaketaketake matcher and print ranked candidates as JSON. "
            "Bundled cache covers physics + mse. For other fields, supply candidates "
            "via --candidates-file / --candidates-json (Claude can generate these)."
        )
    )
    ap.add_argument("--profile-file", type=Path, help="Path to a profile JSON file")
    ap.add_argument("--profile-json", type=str, help="Profile JSON string")
    ap.add_argument(
        "--field",
        required=True,
        help="Target field (any STEM discipline). Bundled cache: physics, mse.",
    )
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "data",
        help="Path to bundled data dir (default: <repo>/data)",
    )
    ap.add_argument(
        "--candidates-file",
        type=Path,
        help=(
            "Override bundled cache with a JSON array of CandidateAdvisor records. "
            "Use this for fields not in the bundled cache."
        ),
    )
    ap.add_argument(
        "--candidates-json",
        type=str,
        help="Inline JSON array of CandidateAdvisor records.",
    )
    args = ap.parse_args()

    try:
        profile_dict = _load_profile(args)
    except (json.JSONDecodeError, SystemExit) as e:
        json.dump({"error": f"profile load: {e}"}, sys.stdout)
        return 2

    profile_dict.setdefault("field", args.field)

    try:
        student = StudentProfile(**profile_dict)
    except Exception as e:
        json.dump({"error": f"profile validation: {e}"}, sys.stdout)
        return 2

    try:
        external = _load_candidates(args)
    except Exception as e:
        json.dump({"error": f"candidates load: {e}"}, sys.stdout)
        return 2

    if external is not None:
        candidates = external
    else:
        candidates = load_advisors(args.data_dir, args.field)

    if not candidates:
        hint = ""
        if args.field not in BUNDLED_FIELDS:
            hint = (
                f" Field '{args.field}' isn't in the bundled cache "
                f"({sorted(BUNDLED_FIELDS)}). Pass --candidates-file or "
                f"--candidates-json with a JSON array of candidate advisors "
                f"(see references/profile_schema.md for the schema)."
            )
        json.dump(
            {"error": f"no candidates loaded for field={args.field}.{hint}"},
            sys.stdout,
        )
        return 1

    results = rank_advisors(student, candidates, top_k=args.top_k)
    output = [r.model_dump(mode="json") for r in results]
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
