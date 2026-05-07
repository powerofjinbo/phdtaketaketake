#!/usr/bin/env python3
"""Per-field candidate discovery plan generator (Sprint-2-c4).

Given a target field and a list of schools (+ research keywords),
emits a structured search plan: per-field query recipes (Google Scholar
/ DBLP / INSPIRE / PubMed / etc.), required source list, and exclusion
rules. The agent uses this as a checklist when gathering candidate PIs
to ensure consistent coverage across fields.

Usage:

    python scripts/build_discovery_plan.py \\
        --field cs \\
        --schools '["MIT", "Stanford", "Berkeley"]' \\
        --keywords "multi-agent reinforcement learning"

    # OR with --schools-file for a longer list:
    python scripts/build_discovery_plan.py \\
        --field physics \\
        --schools-file /tmp/top10_physics.json \\
        --keywords "ATLAS Higgs analysis"

Output: JSON plan to stdout. The plan includes:
  - field_profile_id / field_display_name
  - schools / keywords
  - queries: list of {engine, query, purpose} per school × per recipe
  - primary_databases (from FieldProfile)
  - ranking_source_url (from FieldProfile)
  - field_caveats (from FieldProfile)
  - exclusion_rules (universal)
  - field_profile_loaded (bool — false means falling back to generic recipes)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.discovery import build_discovery_plan

# Sprint-3-c5: when installed as a package, data/ ships at repo root
# alongside the phd_matcher/ package. Two parents up from this file
# (phd_matcher/cli/<this>.py → phd_matcher/cli → phd_matcher → repo) is
# the project root.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def _load_schools(args: argparse.Namespace) -> list[str]:
    if args.schools_file:
        data = json.loads(args.schools_file.read_text())
    elif args.schools:
        data = json.loads(args.schools)
    else:
        raise SystemExit("provide --schools (JSON array) or --schools-file")
    if not isinstance(data, list) or not all(isinstance(s, str) for s in data):
        raise SystemExit("--schools must be a JSON array of strings")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Generate a per-field candidate discovery plan for the agent's "
            "deep-research step. Outputs queries / required sources / "
            "exclusion rules as JSON."
        ),
    )
    ap.add_argument("--field", required=True, help="Target STEM field")
    ap.add_argument(
        "--schools", type=str,
        help='Inline JSON array of school names, e.g. \'["MIT", "Stanford"]\'',
    )
    ap.add_argument(
        "--schools-file", type=Path,
        help="Path to a JSON file containing the schools array",
    )
    ap.add_argument(
        "--keywords", required=True,
        help="Research keywords / direction (drives query templates)",
    )
    ap.add_argument(
        "--data-dir", type=Path, default=_DEFAULT_DATA_DIR,
        help="Path to data/ directory (for field profile lookup)",
    )
    args = ap.parse_args()

    try:
        schools = _load_schools(args)
    except (json.JSONDecodeError, SystemExit) as e:
        json.dump({"error": str(e)}, sys.stdout)
        return 2

    if not schools:
        json.dump({"error": "schools list is empty"}, sys.stdout)
        return 1

    field_profile = load_field_profile(args.data_dir, args.field)

    plan = build_discovery_plan(
        field=args.field,
        schools=schools,
        keywords=args.keywords,
        field_profile=field_profile,
    )
    json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
