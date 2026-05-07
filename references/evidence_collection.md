# Evidence collection — Source adapters + collect_evidence.py (Sprint-3-c1)

The matcher's hardest practical problem is no longer "evaluate the
agent's JSON" — it's "help the agent produce high-quality JSON". The
v1 collection layer drives a **source adapter** to enrich
`CandidateAdvisor` records with evidence + raw facts pulled from real
sources (OpenAlex in v1; PubMed / DBLP / Semantic Scholar in later
sprints).

## Hard architectural rule

**Source adapters produce evidence + raw facts only.** They never
compute scores. The matcher's deterministic scoring (CAPEG + D + O +
research_fit + strategy) stays in `phd_matcher.scoring.*` /
`phd_matcher.matching.strategy`. Pinned by
`test_collect_evidence_does_not_modify_scores`.

## Three modes

```
# 1. Fixture mode — deterministic, offline, used by tests + dry runs
python scripts/collect_evidence.py \
  --profile-file p.json --candidates-file c.json \
  --field physics \
  --fixture-dir tests/fixtures \
  --out enriched.json

# 2. Live mode — real OpenAlex HTTP (opt-in)
python scripts/collect_evidence.py \
  --profile-file p.json --candidates-file c.json \
  --field physics \
  --live --mailto you@example.edu \
  --out enriched.json

# 3. Offline mode — adapter returns nothing; useful for sanity-checking
#    the orchestration without HTTP. (Default when neither flag passed.)
python scripts/collect_evidence.py \
  --profile-file p.json --candidates-file c.json \
  --field physics
```

## Output JSON

```jsonc
{
  "input_field": "physics",
  "field_profile_id": "physics",
  "adapter": "openalex",
  "mode": "fixture" | "live" | "offline",
  "candidates": [<enriched CandidateAdvisor records>],
  "collection_summary": {
    "fields_attempted": 18,
    "fields_filled": 9,
    "fields_unresolved": 7,
    "source_errors": ["openalex fixture miss: ..."],
    "unresolved_repair_queue": [
      {
        "candidate_id": "cand_004",
        "signal": "author_lookup",
        "detail": "adapter=openalex could not find Prof. Z at Stanford"
      }
    ],
    "filled_log": [
      {
        "candidate_id": "cand_001",
        "signal": "research_areas",
        "detail": "set from openalex concepts"
      }
    ]
  }
}
```

## What v1 + c2 fills

The collector attempts these fields (in order, per candidate):

1. **`research_areas`** — from the candidate-author's top concepts
   (OpenAlex `x_concepts`) or aggregated from recent works'
   concept tags. Capped at 5. Skipped if already set by the agent.

2. **`normalized_collab_top20pct`** (Sprint-3-c2) — derived from
   `author.h_index` via `min(1.0, h_index/50)`. Evidence cites the
   author profile URL with the formula in the claim. Skipped if the
   agent already set the value or if the adapter doesn't return
   `h_index`.

3. **`paths_to_advisors[<adv.id>]`** — from coauthored works between
   the candidate and each `student.current_advisors` entry:
   - `small_team_coauthor_5y` = count of coauthored works with
     `author_count ≤ field threshold`
   - `big_collab_papers_5y` = count with `author_count > field threshold`
   - `most_recent_connection_year` = max year across coauthored works
   - **Verified-empty path**: if 0 coauthored works found, an item with
     `supports_fields=["path:<adv_id>"]` is added so strict mode passes
   - Skipped if the agent already populated this advisor's path with
     any edge field

4. **`research_fit` evidence** (Sprint-3-c2) — items only, NOT a score.
   Pulls recent papers (last 3y) and finds those whose title or
   concepts overlap the student's `research_direction` tokens.
   Attaches up to 3 papers as `EvidenceSource` items with
   `supports_fields=["research_fit"]`. Skipped if research_fit
   evidence already exists on the candidate.

   **The collector NEVER sets `research_fit_score`.** That stays an
   agent decision per per-field axes (see `research_fit_v2.md`).
   Pinned by `test_collect_evidence_does_not_compute_research_fit_score`.

Each filled field comes with a structured `EvidenceSource` whose
`source_type="openalex"` and `supports_fields` list the field name(s)
the URL backs.

**Deferred to Sprint-3-c3**: PubMed / DBLP / Semantic Scholar adapters
for field-aware enrichment beyond OpenAlex.

## Adapter interface

```python
class SourceAdapter:
    name: str           # "openalex" / "pubmed" / "dblp" / etc.
    errors: list[str]   # recoverable per-call errors

    def find_author(name, institution=None) -> AuthorRecord | None: ...
    def recent_works(author_id, since_year=None, limit=50) -> list[WorkRecord]: ...
    def coauthored_works(author_id_a, author_id_b, since_year=None) -> list[WorkRecord]: ...
```

`AuthorRecord` and `WorkRecord` are `dataclass` records — see
`phd_matcher/sources/base.py` for the full schemas.

Adapters track recoverable errors (HTTP failures, missing fixtures) on
`self.errors` so the collector can surface them in
`collection_summary.source_errors`.

## OpenAlex adapter — fixture format

Fixture files live under `<fixture_dir>/openalex/<endpoint>/<key>.json`:

```
fixtures/openalex/
  find_author/
    prof_y__mit.json                                # name + institution
    prof_y.json                                      # fallback (no institution)
  recent_works/
    a_prof_y_mit.json                                # by source-specific id
  coauthored/
    a_prof_y_mit__a_prof_wang_thu.json               # both orderings tried
```

Sanitization: lowercase, non-alphanumeric → `_`, no leading/trailing
underscores. Both id orderings are tried for `coauthored/`.

Example fixture (`find_author/prof_y__mit.json`):

```jsonc
{
  "id": "A_PROF_Y_MIT",
  "name": "Prof. Y",
  "institutions": ["MIT"],
  "profile_url": "https://openalex.org/authors/A_PROF_Y_MIT",
  "h_index": 35,
  "works_count": 87,
  "concepts": ["Higgs boson", "ATLAS", "particle physics"]
}
```

Example coauthored fixture:

```jsonc
[
  {"id": "W1", "title": "...", "year": 2024, "author_count": 6, "concepts": [...]},
  {"id": "W2", "title": "...", "year": 2023, "author_count": 8, "concepts": [...]},
  {"id": "W3", "title": "...", "year": 2022, "author_count": 312, "concepts": [...]}
]
```

## OpenAlex live mode

Live mode hits `https://api.openalex.org` (free, no API key). Per
OpenAlex's polite-pool guidance, pass `--mailto <your-email>` to land
in the polite pool with higher rate limits.

The live adapter calls three endpoints:

  - `/authors?search=<name>&filter=last_known_institutions.display_name.search:<institution>`
  - `/works?filter=author.id:A<author_id>&per-page=50&sort=publication_year:desc`
  - `/works?filter=author.id:A<a>,author.id:A<b>&per-page=50` (both authors → AND)

All errors are appended to `adapter.errors` and surfaced in
`collection_summary.source_errors`.

## Workflow integration

The recommended flow:

1. `scripts/build_discovery_plan.py` → agent runs the search recipes
   manually (or via tool calls) to *find* candidate PIs and write the
   initial JSON.
2. **`scripts/collect_evidence.py`** → enriches the JSON with
   structured evidence (this commit).
3. `scripts/audit_candidates.py` → reports remaining repair queue.
4. `scripts/match.py` → ranks (with `--strict-evidence` for real
   decisions).

Each step writes JSON the next step consumes. Iterate until
`audit_candidates.py --strict-evidence` returns `strict_ready: true`.

## Why fixture-first

- Tests run offline. No flakiness from upstream API outages.
- Reproducible: fixtures pin specific data; tests assert exact counts
  / years.
- Live mode is opt-in for users who explicitly want fresh data;
  fixture mode covers CI and local development.

## What collect_evidence does NOT do

- **Does not fabricate values.** If the adapter returns nothing, the
  field stays unset and the candidate ID + signal land in
  `unresolved_repair_queue`.
- **Does not compute scores.** All filled fields are facts (counts,
  years, concepts) or evidence (URLs, claim strings, supports_fields).
  The matcher's deterministic scoring runs unchanged on the enriched
  JSON.
- **Does not overwrite agent-populated data.** If the agent already set
  `research_areas` or filled `paths_to_advisors[<id>]`, the collector
  records "skipped" and moves on.
- **Does not infer author_position for recent papers.** Filling
  `recent_papers` requires position information the OpenAlex authorship
  list provides; v1 defers this to Sprint-3-c2.
