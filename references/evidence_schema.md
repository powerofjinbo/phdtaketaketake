# Evidence schema

The matcher's hallucination-resistance lives here. Every claim the agent
makes about a candidate must trace back to a real URL, bound to the
specific signal it supports — so a reviewer can verify each claim
individually instead of guessing which URL backs which number.

## EvidenceSource — the atom

```jsonc
{
  "url": "https://scholar.google.com/citations?user=<author_id>",
  "source_type": "google_scholar",
  "claim": "h_index = 35 (checked 2026-05-06)",
  "supports_fields": ["normalized_collab_top20pct"],
  "quote_or_snippet": "h-index: 35   citations: 6,210",  // optional
  "last_checked": "2026-05-06"                             // optional
}
```

Pydantic-strict (`extra="forbid"`). `source_type` is an enum — see
`phd_matcher/models.py:EvidenceSourceType` for the full list (lab_page,
faculty_page, google_scholar, openalex, inspire, pubmed, europe_pmc,
semantic_scholar, arxiv, biorxiv, dblp, openreview, csrankings,
mathscinet, math_genealogy, us_news, nas, hhmi, nih_reporter,
clinicaltrials_gov, genealogy, paper, cv, other).

The **`supports_fields`** list is the binding contract: it names the
signals this URL is allowed to verify. A google_scholar profile URL
might support `normalized_collab_top20pct` but NOT `school_tier`. The
matcher's per-claim audit checks this binding.

## EvidenceEntry — sources for one signal

```jsonc
"evidence": {
  "school_tier": {
    "items":   [ EvidenceSource, ... ],   // preferred
    "sources": [ "https://...", ... ],    // legacy bare URLs
    "note":    "freeform note",
    "last_checked": "2026-05-06"
  },
  "research_areas":  { "items": [ ... ] },
  "research_fit":    { "items": [ ... ] }
}
```

Two formats:

- **`items` (preferred)** — structured `EvidenceSource` records with
  `supports_fields`. **Required in `--strict-evidence` mode.**
- **`sources` (legacy)** — bare URL strings. Accepted in default mode
  for back-compat; **rejected in strict mode** as claim-level proof.

Empty both → the signal counts as unverified.

## PathEdge — connection edges with their own evidence

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "small_team_coauthor_5y": 3,
    "big_collab_papers_5y":  12,
    "same_working_group":    true,
    "items": [
      {
        "url": "https://scholar.google.com/...",
        "source_type": "google_scholar",
        "claim": "3 co-authored papers 2022-2024 with ≤10 authors",
        "supports_fields": ["small_team_coauthor_5y"]
      },
      {
        "url": "https://inspirehep.net/authors/<candidate>/...",
        "source_type": "inspire",
        "claim": "12 ATLAS publications co-authored 2020-2024",
        "supports_fields": ["big_collab_papers_5y"]
      },
      {
        "url": "https://atlas-glance.cern.ch/.../conveners",
        "source_type": "lab_page",
        "claim": "both listed as H→cc̄ working-group conveners 2021-2023",
        "supports_fields": ["same_working_group"]
      }
    ],
    "note": "3 small-team, 12 ATLAS bulk, both H→cc̄ conveners"
  }
}
```

A PathEdge is verified iff **every set sub-field has its own evidence**
(an `items` entry whose `supports_fields` includes that sub-field name).
Setting `small_team_coauthor_5y=3` and `big_collab_papers_5y=12` means
the agent needs evidence for *both*; one shared item with
`supports_fields=["small_team_coauthor_5y", "big_collab_papers_5y"]`
also works.

## Verified-empty — "I searched, found nothing"

When a search comes up empty, do NOT leave the path missing. Record the
search itself with `supports_fields=["path:<advisor_id>"]`:

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "items": [{
      "url": "https://scholar.google.com/citations?user=...&q=Wang+candidate",
      "source_type": "google_scholar",
      "claim": "searched 2020-2024: 0 co-authored papers, no shared lineage",
      "supports_fields": ["path:adv_001"]
    }],
    "note": "also checked Math Genealogy Project — neither party in DB"
  }
}
```

This counts as **verified-empty** (0 unverified for that path) — strictly
better than no entry (1 missing) or a bare-URL `sources: [...]` (which
fails strict mode).

The same pattern applies to other signals — when you searched a directory
and confirmed no membership, set the value to `false` (or 0.0) and cite
the directory page with `supports_fields=[<signal_name>]`.

## Per-claim audit

A signal is verified iff at least one `EvidenceSource` in its
`EvidenceEntry.items` (or in `PathEdge.items` for path edges) lists that
signal's field name in `supports_fields`.

**Don't game this** — attaching unrelated URLs doesn't help. The
`explain_match()` output filters items per claim, so a small_team
co-authorship URL won't show up next to a big-collab claim, even if both
items are in the same list.

| Signal | Verified means |
|--------|----------------|
| `path:<adv.id>` | every set sub-field on `PathEdge` has an item with that sub-field in `supports_fields`; OR (for verified-empty) one item with `supports_fields=["path:<adv.id>"]` |
| `school_tier` | `evidence["school_tier"].items` contains an item with `"school_tier"` in `supports_fields` |
| `research_areas` | same rule, `"research_areas"` in `supports_fields` |
| `normalized_collab_top20pct` / `collab_with_nas` / `grad_placement_quality` / `active_funding_quality` | per-field rule, signal name in `supports_fields` |
| `pi_signal` | value is non-`"missing"` AND `evidence["pi_signal"].items` has matching `supports_fields` |
| `research_fit` | (only counted when `research_fit_score` is non-null) `evidence["research_fit"].items` has `"research_fit"` in `supports_fields` |

## Confidence band — driven by evidence coverage

| Unverified count | Band |
|------------------|------|
| 0 (everything sourced) | ±0.2 |
| 1–2 | ±0.4 |
| 3–4 | ±0.6 |
| 5+ (mostly unsourced) | ±0.8 |

`unverified = missing + unsourced`. The split matters:

- **missing** — value not set, no evidence (an honest information gap).
- **unsourced** — value set but no item with matching `supports_fields`
  (a claim without proof; high hallucination risk).

Strict mode rejects **unsourced** claims; missing signals are still
allowed (they're a legitimate "I couldn't verify" state).

## Default vs strict mode

```bash
# Strict — for real application decisions
python scripts/match.py --profile-file ... --candidates-file ... \
  --field <FIELD> --strict-evidence

# Default — for first-pass exploration
python scripts/match.py --profile-file ... --candidates-file ... \
  --field <FIELD>
```

| | Default | Strict |
|---|---|---|
| Bare `sources` URL | accepted | rejected |
| Verified-empty path with bare URL | accepted | rejected |
| Verified-empty path with `supports_fields=["path:<id>"]` item | accepted | accepted |
| Item with no matching `supports_fields` | counted only as generic evidence (default mode), but NOT for the specific claim | rejected for that claim |
| Missing signal (no value, no evidence) | allowed (counts as missing) | allowed |
| Set value with no matching item | allowed (counts as unsourced; widens band) | **fails** with structured error pointing at the field |

The strict-mode error tells the agent exactly which field needs which
kind of evidence (see `_FIX_HINTS` in `phd_matcher/matching/ranker.py`).

## Why this design

- A 4.0 candidate with 0 cited URLs has **±0.8** band → risk-adjusted
  drops by 0.4. A well-sourced 3.0 ±0.2 candidate (risk-adjusted 2.9)
  outranks 3.2 ±0.8 (risk-adjusted 2.8).
- Per-claim binding (`supports_fields`) prevents URL-stuffing — citing
  the same Google Scholar profile to "verify" school_tier doesn't work.
- Verified-empty closes the loop on negative results: searching and
  finding nothing is valuable evidence the agent should record.
