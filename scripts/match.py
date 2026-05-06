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
from phd_matcher.models import StudentProfile  # noqa: E402


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


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the phdtaketaketake matcher and print ranked candidates as JSON."
    )
    ap.add_argument("--profile-file", type=Path, help="Path to a profile JSON file")
    ap.add_argument("--profile-json", type=str, help="Profile JSON string")
    ap.add_argument(
        "--field", required=True, choices=["physics", "mse"], help="Target field"
    )
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "data",
        help="Path to bundled data dir (default: <repo>/data)",
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

    candidates = load_advisors(args.data_dir, args.field)
    if not candidates:
        json.dump(
            {"error": f"no candidates loaded for field={args.field}"}, sys.stdout
        )
        return 1

    results = rank_advisors(student, candidates, top_k=args.top_k)
    output = [r.model_dump(mode="json") for r in results]
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
