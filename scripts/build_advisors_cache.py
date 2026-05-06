#!/usr/bin/env python3
"""Build advisors cache from OpenAlex (free, no auth required).

Fetches active PIs at top US PhD programs (per data/schools/us_news_rank.yaml)
in the requested field, populates a CandidateAdvisor JSON record per PI, and
writes to data/advisors/<field>_cache.json. The bundled loader prefers this
real cache over data/advisors/mock_advisors.json when both exist.

Run:
    python scripts/build_advisors_cache.py --field physics
    python scripts/build_advisors_cache.py --field mse --mailto your@email

The --mailto flag opts into OpenAlex's polite pool (faster + more reliable).

Field-strength signals (normalized_collab_top20pct) are computed from each
PI's h-index as a rough proxy. NAS-membership and grad-placement quality
need external data sources and stay at conservative defaults — those
fields are still on the roadmap.

Also: paths_to_advisors stays empty here. Per-(student, candidate) edges
should be computed at match time once the student names their current
advisor (a separate script is on the roadmap; for now Claude can fill
paths_to_advisors inline based on its knowledge or on a quick OpenAlex
co-authorship check).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent

OPENALEX_API = "https://api.openalex.org"
USER_AGENT = "phdtaketaketake/0.1 (https://github.com/powerofjinbo/phdtaketaketake)"

# OpenAlex's author-side concept filter is unreliable, so we fetch top-N
# authors by h-index per institution and post-filter by checking each
# author's `x_concepts` for the expected field keyword(s).
FIELD_CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "physics": ["Physics", "Astrophysics"],
    "mse": ["Materials science", "Nanotechnology"],
    "chemistry": ["Chemistry"],
    "biology": ["Biology", "Genetics", "Cell biology", "Neuroscience", "Microbiology"],
    "cs": ["Computer science"],
    "math": ["Mathematics"],
    "ee": ["Electrical engineering", "Electronics"],
    "earth_science": ["Geology", "Earth science", "Atmospheric sciences", "Oceanography"],
    "chemical_engineering": ["Chemical engineering", "Catalysis"],
}

# Min h-index to be considered an active PI (heuristic).
MIN_PI_H_INDEX = 12

# Authors to fetch per institution before post-filtering by field keyword.
FETCH_PER_INSTITUTION = 100

# Max retained candidates per institution after filtering (cap to avoid one
# huge school dominating the cache).
KEEP_PER_INSTITUTION = 30


def _fetch(path: str, params: dict | None = None, mailto: str | None = None) -> dict:
    p = dict(params or {})
    if mailto:
        p["mailto"] = mailto
    qs = urlencode(p, quote_via=quote)
    url = f"{OPENALEX_API}{path}?{qs}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def search_institution(name: str, mailto: str | None = None) -> str | None:
    try:
        data = _fetch(
            "/institutions",
            params={"search": name, "per-page": 1, "filter": "country_code:us"},
            mailto=mailto,
        )
    except (HTTPError, URLError) as e:
        print(f"  ⚠️  institution search failed for {name!r}: {e}", file=sys.stderr)
        return None
    results = data.get("results", [])
    return results[0]["id"] if results else None


def authors_at_institution(inst_id: str, mailto: str | None = None) -> list[dict]:
    """Fetch the top-N authors at an institution by h-index, regardless of field.
    The caller post-filters by field keyword via the `x_concepts` array."""
    try:
        data = _fetch(
            "/authors",
            params={
                "filter": f"last_known_institutions.id:{inst_id}",
                "per-page": FETCH_PER_INSTITUTION,
                "sort": "summary_stats.h_index:desc",
            },
            mailto=mailto,
        )
    except (HTTPError, URLError) as e:
        print(f"  ⚠️  author fetch failed for {inst_id}: {e}", file=sys.stderr)
        return []
    return data.get("results", [])


def matches_field(author: dict, keywords: list[str]) -> bool:
    """True if any of the author's top concepts matches one of the field keywords."""
    if not keywords:
        return True
    top_concepts = {
        c.get("display_name", "") for c in (author.get("x_concepts") or [])[:5]
    }
    return any(k in top_concepts for k in keywords)


def build_candidate(author: dict, school_name: str, school_tier: str, field: str) -> dict:
    stats = author.get("summary_stats", {})
    h_index = int(stats.get("h_index", 0))

    # Top-5 concepts by score → research_areas
    research_areas = [
        c["display_name"]
        for c in (author.get("x_concepts") or [])[:5]
        if c.get("display_name")
    ]

    # Rough field-strength proxy from h-index. Calibrated so a top-tier PI
    # (h ≈ 50) lands in bucket 0.8–1.0, mid-career (h ≈ 25) in 0.4–0.6.
    normalized_collab = min(1.0, h_index / 50.0)

    return {
        "id": author["id"].split("/")[-1],
        "name": author["display_name"],
        "institution": school_name,
        "school_tier": school_tier,
        "field": field,
        "research_areas": research_areas,
        "recent_papers": [],
        "paths_to_advisors": {},      # filled at match time
        "normalized_collab_top20pct": round(normalized_collab, 2),
        "collab_with_nas": False,     # roadmap: needs NAS member list
        "grad_placement_quality": 0.5,  # roadmap: needs PhD placement tracking
        "pi_signal": "missing",       # roadmap: lab-page LLM scrape
        "recent_phd_count": None,
        "h_index": h_index,
        "openalex_id": author["id"],
    }


def build(
    field: str,
    limit: int | None = None,
    mailto: str | None = None,
    output_path: Path | None = None,
    schools_per_tier: int | None = None,
) -> int:
    schools_yaml = REPO_ROOT / "data" / "schools" / "us_news_rank.yaml"
    schools = yaml.safe_load(schools_yaml.read_text())

    if field not in schools:
        print(f"Error: no schools listed for field={field!r}.", file=sys.stderr)
        print(f"Available fields: {sorted(schools.keys())}", file=sys.stderr)
        return 1

    keywords = FIELD_CONCEPT_KEYWORDS.get(field, [])
    if not keywords:
        print(
            f"Warning: no concept keywords for {field!r}; will not filter by field",
            file=sys.stderr,
        )

    candidates: list[dict] = []
    seen_ids: set[str] = set()

    tier_order = ["top_10", "top_11_30", "top_31_60", "top_60_plus"]
    for tier_name in tier_order:
        if tier_name not in schools[field]:
            continue
        school_list = schools[field][tier_name]
        if schools_per_tier:
            school_list = school_list[:schools_per_tier]

        for school_name in school_list:
            print(f"  ↳ {tier_name:<12} {school_name}", file=sys.stderr, flush=True)

            inst_id = search_institution(school_name, mailto=mailto)
            if not inst_id:
                print(f"      ⚠️  institution not found", file=sys.stderr)
                continue

            time.sleep(0.2)

            authors = authors_at_institution(inst_id, mailto=mailto)
            kept = 0
            for author in authors:
                h = (author.get("summary_stats") or {}).get("h_index") or 0
                if h < MIN_PI_H_INDEX:
                    continue
                if not matches_field(author, keywords):
                    continue
                aid = author["id"].split("/")[-1]
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                candidates.append(build_candidate(author, school_name, tier_name, field))
                kept += 1
                if kept >= KEEP_PER_INSTITUTION:
                    break
            print(f"      kept {kept} active PIs", file=sys.stderr)

            time.sleep(0.4)

            if limit and len(candidates) >= limit:
                break
        if limit and len(candidates) >= limit:
            break

    out = output_path or REPO_ROOT / "data" / "advisors" / f"{field}_cache.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(candidates, indent=2, ensure_ascii=False))
    print(f"\n✓ Wrote {len(candidates)} candidates → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--field", required=True, help="STEM field name")
    ap.add_argument("--limit", type=int, default=None, help="Cap total candidates")
    ap.add_argument(
        "--schools-per-tier",
        type=int,
        default=None,
        help="Cap schools per tier (e.g., 3 for a quick smoke test)",
    )
    ap.add_argument("--mailto", help="Email for OpenAlex polite pool (optional)")
    ap.add_argument("--output", type=Path, help="Output JSON path")
    args = ap.parse_args()
    sys.exit(
        build(
            args.field,
            limit=args.limit,
            mailto=args.mailto,
            output_path=args.output,
            schools_per_tier=args.schools_per_tier,
        )
    )
