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

from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.evidence_collector import EvidenceCollector
from phd_matcher.models import CandidateAdvisor, StudentProfile
from phd_matcher.sources import (
    ADAPTER_CLASSES,
    CachedAdapter,
    RateLimitedAdapter,
    default_adapter_for_field,
    select_adapter,
)

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
    raise SystemExit("provide --profile-file, --profile-json, or pipe via stdin")


def _load_candidates(args: argparse.Namespace) -> list[CandidateAdvisor]:
    if args.candidates_file:
        data = json.loads(args.candidates_file.read_text())
    elif args.candidates_json:
        data = json.loads(args.candidates_json)
    else:
        raise SystemExit("--candidates-file or --candidates-json required")
    return [CandidateAdvisor(**c) for c in data]


def _build_adapter(
    args: argparse.Namespace, field_profile_id: str | None,
):
    """Construct the adapter selected by `--source` (or per-field default)
    and return ``(adapter, mode_string, source_name)``."""
    source_name = args.source or default_adapter_for_field(field_profile_id)

    if args.fixture_dir:
        adapter = select_adapter(source_name, fixture_dir=args.fixture_dir)
        mode = "fixture"
    elif args.live:
        adapter = select_adapter(
            source_name, live=True,
            mailto=args.mailto, api_key=args.api_key,
        )
        mode = "live"
        # Wrap with rate-limit + cache for live mode (Sprint-3-c4).
        if args.rate_limit_seconds and args.rate_limit_seconds > 0:
            adapter = RateLimitedAdapter(
                adapter, min_interval_seconds=args.rate_limit_seconds,
            )
    else:
        adapter = select_adapter(source_name)
        mode = "offline"

    if args.cache_dir:
        adapter = CachedAdapter(
            adapter,
            cache_dir=args.cache_dir,
            ttl_seconds=(
                args.cache_ttl_days * 86400
                if args.cache_ttl_days else None
            ),
        )
        # Mode reflects caching layer
        if mode == "live":
            mode = "live+cache"
        elif mode == "offline":
            mode = "offline+cache"
        elif mode == "fixture":
            mode = "fixture+cache"
    return adapter, mode, source_name


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
        "--data-dir", type=Path, default=_DEFAULT_DATA_DIR,
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
    ap.add_argument(
        "--source", type=str, choices=sorted(ADAPTER_CLASSES.keys()),
        help=(
            "Source adapter to use. Defaults to the per-field choice "
            "(openalex for physics/mse/chemistry; pubmed for biology; "
            "semantic_scholar for cs/math)."
        ),
    )
    ap.add_argument(
        "--api-key", type=str,
        help=(
            "Optional API key for sources that support one (PubMed "
            "NCBI, Semantic Scholar). OpenAlex is keyless; use --mailto."
        ),
    )
    ap.add_argument(
        "--cache-dir", type=Path,
        help=(
            "Disk cache directory. Wraps the chosen adapter with "
            "CachedAdapter so identical calls reuse the cached JSON "
            "(speeds up re-runs across portfolios)."
        ),
    )
    ap.add_argument(
        "--cache-ttl-days", type=int,
        help=(
            "Optional TTL for the cache (default: never expires). "
            "Useful for periodic re-runs that pick up newly-published "
            "works without manually flushing."
        ),
    )
    ap.add_argument(
        "--rate-limit-seconds", type=float, default=0.1,
        help=(
            "Minimum seconds between consecutive live HTTP calls. "
            "Default 0.1 (polite-pool friendly). Set to 0 to disable."
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

    adapter, mode, source_name = _build_adapter(
        args, field_profile.id if field_profile else None,
    )
    collector = EvidenceCollector(
        adapter, field_profile=field_profile,
    )
    for cand in candidates:
        collector.collect_for_candidate(student, cand)

    output = {
        "input_field": args.field,
        "field_profile_id": field_profile.id if field_profile else None,
        "adapter": adapter.name,
        "source": source_name,
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
