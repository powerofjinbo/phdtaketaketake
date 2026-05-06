#!/usr/bin/env python3
"""Build advisors cache from OpenAlex (WIP).

The current repo uses bundled mock advisor data
(`data/advisors/mock_advisors.json`). This script will eventually replace
that with real OpenAlex-backed records.

Planned flow:
  1. Read schools list from data/schools/us_news_rank.yaml
  2. For each (school, field), query OpenAlex for active PIs
  3. Pull recent papers (5y), co-author graph, institutional affiliation
  4. Build paths_to_advisors via genealogy + co-author + collaboration matching
  5. Optionally scrape lab pages to estimate pi_signal (recent PhD count)
  6. Write to data/advisors/<field>_cache.json (or .sqlite)

Run: python scripts/build_advisors_cache.py --field physics --limit 100
"""

from __future__ import annotations

import argparse
import sys


def build(field: str, limit: int | None = None) -> int:
    raise NotImplementedError(
        "Advisor cache builder is not yet implemented. "
        "Use bundled mock data: data/advisors/mock_advisors.json"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True, help="Any STEM field name")
    ap.add_argument("--limit", type=int, default=None, help="Cap number of PIs (for dev)")
    args = ap.parse_args()
    sys.exit(build(args.field, args.limit))
