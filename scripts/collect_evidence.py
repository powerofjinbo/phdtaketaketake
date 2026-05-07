#!/usr/bin/env python3
"""Evidence collection CLI (Sprint-3-c1).

Drives a `SourceAdapter` (OpenAlex in v1) to enrich candidate JSONs
with evidence + raw facts: research_areas, paths_to_advisors edges,
most_recent_connection_year. The adapter never invents scores —
the matcher's deterministic scoring stays in `phd_matcher.scoring.*`.

Modes:
  - **Default (offline-safe)**: no `--live` and no `--fixture-dir` →
    adapter returns nothing; the script reports unresolved everything.
    Useful for sanity-checking the orchestration without HTTP.
  - **Fixture mode** (`--fixture-dir <path>`): adapter reads pre-baked
    JSONs from disk. Used by tests and dry runs.
  - **Live mode** (`--live` + optional `--mailto <email>`): real OpenAlex
    HTTP calls. Opt-in only.

Usage:

    # Live enrichment of a real batch:
    python scripts/collect_evidence.py \\
        --profile-file profile.json \\
        --candidates-file cands.json \\
        --field physics \\
        --live --mailto you@example.edu \\
        --out enriched.json

    # Offline / fixture dry-run for tests:
    python scripts/collect_evidence.py \\
        --profile-file profile.json \\
        --candidates-file cands.json \\
        --field physics \\
        --fixture-dir tests/fixtures \\
        --out /tmp/enriched.json

Output JSON shape:

    {
      "input_field": "physics",
      "field_profile_id": "physics",
      "adapter": "openalex",
      "mode": "live" | "fixture" | "offline",
      "candidates": [<enriched CandidateAdvisor records>],
      "collection_summary": {
        "fields_attempted": N,
        "fields_filled": M,
        "fields_unresolved": K,
        "source_errors": [...],
        "unresolved_repair_queue": [...],
        "filled_log": [...]
      }
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from phd_matcher.data.loaders import load_field_profile  # noqa: E402
from phd_matcher.matching.evidence_collector import EvidenceCollector  # noqa: E402
from phd_matcher.models import CandidateAdvisor, StudentProfile  # noqa: E402
from phd_matcher.sources.openalex import OpenAlexAdapter  # noqa: E402


def _load_profile(args: argparse.Namespace) -> dict:
    if args.profile_file:
        return json.loads(args.profile_file.read_text())
    if args.profile_json:
        return json.loads(args.profile_json)
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    raise SystemExit("provide --profile-file, --profile-json, or pipe via stdin")


def _load_candidates(args: argparse.Namespace) -> list[CandidateAdvisor]:
    if args.candidates_file:
        data = json.loads(args.candidates_file.read_text())
    elif args.candidates_json:
        data = json.loads(args.candidates_json)
    else:
        raise SystemExit("--candidates-file or --candidates-json required")
    return [CandidateAdvisor(**c) for c in data]


def _build_adapter(args: argparse.Namespace) -> tuple[OpenAlexAdapter, str]:
    """Return (adapter, mode_string)."""
    if args.fixture_dir:
        return (
            OpenAlexAdapter(fixture_dir=args.fixture_dir),
            "fixture",
        )
    if args.live:
        return (
            OpenAlexAdapter(live=True, mailto=args.mailto),
            "live",
        )
    return (OpenAlexAdapter(), "offline")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Enrich candidate JSONs with evidence collected from external "
            "sources (OpenAlex in v1). Default mode is offline-safe; pass "
            "--live for real HTTP or --fixture-dir for deterministic test "
            "data."
        ),
    )
    ap.add_argument("--profile-file", type=Path, help="Profile JSON file")
    ap.add_argument("--profile-json", type=str, help="Inline profile JSON")
    ap.add_argument("--field", required=True, help="Target STEM field")
    ap.add_argument(
        "--candidates-file", type=Path,
        help="JSON array of CandidateAdvisor records",
    )
    ap.add_argument(
        "--candidates-json", type=str,
        help="Inline JSON array of CandidateAdvisor records",
    )
    ap.add_argument(
        "--out", type=Path,
        help="Optional output file (defaults to stdout)",
    )
    ap.add_argument(
        "--data-dir", type=Path, default=REPO_ROOT / "data",
        help="Path to data/ directory (for field profile lookup)",
    )
    ap.add_argument(
        "--fixture-dir", type=Path,
        help="Read fixture JSON files from this directory (offline)",
    )
    ap.add_argument(
        "--live", action="store_true",
        help="Enable live HTTP calls to OpenAlex (opt-in)",
    )
    ap.add_argument(
        "--mailto", type=str,
        help=(
            "Email for OpenAlex polite-pool tagging (recommended for "
            "live mode)"
        ),
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

    field_profile = load_field_profile(args.data_dir, args.field)
    if field_profile and student.field != field_profile.id:
        student.field = field_profile.id

    adapter, mode = _build_adapter(args)
    collector = EvidenceCollector(
        adapter, field_profile=field_profile,
    )
    for cand in candidates:
        collector.collect_for_candidate(student, cand)

    output = {
        "input_field": args.field,
        "field_profile_id": field_profile.id if field_profile else None,
        "adapter": adapter.name,
        "mode": mode,
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "collection_summary": collector.summary(),
    }

    if args.out:
        args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    else:
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
