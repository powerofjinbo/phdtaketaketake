# Profile + CandidateAdvisor JSON schema

Canonical shapes of the matcher's inputs. See `phd_matcher/models.py` for the
Pydantic source of truth; this file is the human-readable reference.

## StudentProfile

```jsonc
{
  "name": "Optional display name",
  "field": "physics",                    // REQUIRED — any STEM field as string
  "undergrad_institution": "...",        // REQUIRED
  "master_institution": null,            // optional
  "gpa_raw": 3.82,                       // REQUIRED — number or string
  "gpa_scale": "4.0",                    // REQUIRED — see below
  "research_direction": "...",           // REQUIRED — short paragraph

  "current_advisors": [ ... ],           // recommended (drives Connection)
  "papers":           [ ... ],           // recommended (drives Pub)
  "experiences":      [ ... ]            // recommended (drives Experience)
}
```

`field` accepts any string. **No bundled candidate cache** for any field —
the agent generates candidates per query (see SKILL.md). The bundled
`data/journals/<field>.yaml` exists only for **physics + mse** as the project's
authoritative tier opinion; for other fields the agent uses its training
knowledge anchored on `references/journal_tiers.md`.

### `gpa_scale` enum

| Value | System |
|-------|--------|
| `"4.0"` | US 4.0 |
| `"4.3"` | Some Canadian / Asian |
| `"4.5"` | Some Chinese tech schools |
| `"100"` | Chinese percentage (`gpa_raw` is 0–100) |
| `"uk"` | UK honours (`gpa_raw` is `"first"` / `"high_2_1"` / `"low_2_1"` / `"2_2"` / `"third"`) |

### `current_advisors[]`

```jsonc
{
  "id": "adv_001",
  "name": "Prof. Lisa Wang",
  "institution": "Tsinghua University"
}
```

### `papers[]`

```jsonc
{
  "title": "Search for new physics in dijet events with the ATLAS detector",
  "journal": "Physical Review D",
  "journal_tier": 3,                     // REQUIRED — 0 | "S" | 1 | 2 | 3 | 4 | 5
  "author_position": 312,                // REQUIRED — 1-indexed; ATLAS/CMS papers can be 100+
  "status": "published",                 // see status enum
  "year": 2024,                          // optional
  "doi": null                            // optional
}
```

#### `status` enum (post-review)

| Value | Weight | Meaning |
|-------|--------|---------|
| `"published"` | 1.0 | Already in print / online with DOI |
| `"accepted"` | 1.0 | Editor's accept letter received |
| `"in_press"` | 1.0 | Production stage |
| `"submitted"` | 0.7 | Under review at the named journal |
| `"preprint"` | 0.7 | On arXiv / bioRxiv etc., not yet under review or pre-submission |
| `"in_prep"` | 0.3 | Drafting; not yet a real submission |

The weight multiplies the tier × position score. Default is `"published"` —
match the assumption that the user lists papers they expect on their CV by
application time. Use the lower weights honestly when the user says "I'm
submitting in October" or "we're still drafting".

Tier mapping is universal across STEM — see
[`references/journal_tiers.md`](journal_tiers.md), with field-specific caveats
(CS is conference-driven, biology has co-first conventions, math journals have
different pace, etc.).

### `experiences[]`

```jsonc
{
  "lab_pi_name": "Prof. Lisa Wang",
  "lab_tier": "strong_us_or_top_cn",     // see lab_tiers.md
  "duration_months": 18,
  "output_type": "honors_thesis"
}
```

`output_type` enum:
- `"paper"` (already counted in pub_score; carries 3.7 here so experience isn't penalized)
- `"conference_oral"` (3.7) / `"conference_poster"` (3.3)
- `"honors_thesis"` (3.0) / `"participation_only"` (2.5)

The matcher takes the **strongest single experience** (no stacking).

---

## CandidateAdvisor (always agent-generated via web research)

```jsonc
{
  "id": "cand_001",
  "name": "Prof. Jane Doe",
  "institution": "Stanford University",
  "school_tier": "top_10",                  // top_10 | top_11_30 | top_31_60 | top_60_plus
  "field": "chemistry",
  "research_areas": ["catalysis", "C-H activation"],

  "paths_to_advisors": {                    // KEY — see edge schema below
    "adv_001": {
      "small_team_coauthor_5y": 3,
      "sources": [
        "https://scholar.google.com/citations?user=...",
        "https://api.openalex.org/works?filter=..."
      ],
      "note": "3 co-authored papers in 2022–2024 per Scholar"
    }
  },

  "normalized_collab_top20pct": 0.65,
  "collab_with_nas": false,
  "grad_placement_quality": 0.7,

  "pi_signal": "normal",
  "recent_phd_count": 4,

  "evidence": {                             // sources for the field-strength signals
    "normalized_collab_top20pct": {
      "sources": ["https://scholar.google.com/citations?user=..."],
      "note": "h_index=42 (Google Scholar, checked 2026-05-06)"
    },
    "pi_signal": {
      "sources": ["https://lab.stanford.edu/people"],
      "note": "Lab page lists 4 current PhDs joined 2023–2024"
    }
  },

  "searched_sources": [                     // auditability — what was checked, even if empty
    "https://www.genealogy.math.ndsu.nodak.edu/?id=...",
    "https://www.nasonline.org/member-directory/..."
  ]
}
```

### Connection edges (`paths_to_advisors[advisor_id]`)

The matcher reads from these keys (any subset). **All edges should be backed
by entries in the dict's `sources` list per the data-integrity policy** — the
matcher can compute scores without sources, but the confidence band widens
significantly (see `count_unverified_signals` in `phd_matcher/matching/ranker.py`).

| Edge field | Type | Strength | When to record |
|------------|------|----------|----------------|
| `small_team_coauthor_5y` | int | `min(1.0, n/5)` | Distinct co-authored papers in last 5y with **≤10 authors** (real working relationship) |
| `big_collab_papers_5y` | int | `min(0.4, n/25)` | Papers with **>10 authors** where both names appear (alphabetical author list bulk; significantly weaker — co-membership ≠ working relationship) |
| `same_working_group` | bool | 0.7 | Verified subgroup / convener overlap within a larger collaboration |
| `analysis_contact_overlap` | bool | 0.95 | Both listed as analysis contacts on a specific paper / note |
| `genealogy_relation` | string | `same_advisor`=1.0 / `uncle_nephew`=0.7 / `two_hop`=0.4 | Verified via Math Genealogy or faculty bio |
| `collaboration_overlap_years` | float | ≥5y=1.0 / 1–5y=0.6 / <1y=0.3 | Generic shared-collab overlap when finer signals not available |
| `committee_co_member` | bool + `same_period` bool | 0.8 / 0.3 | Documented editorial board / NSF panel / PC overlap |
| `sources` | list[str] | — | URLs backing the above edges |
| `note` | str | — | Freeform — what was searched, what was found |

The matcher takes **max** across these (no stacking).

### Field-strength fields (with `evidence`)

| Field | Range | Estimation |
|-------|-------|------------|
| `normalized_collab_top20pct` | 0–1 | Proxy: `min(1.0, h_index / 50)`. Look up h-index on Google Scholar / OpenAlex. |
| `collab_with_nas` | bool | Set `true` only if you found a specific recent NAS / HHMI co-author and verified them in the official directory. |
| `grad_placement_quality` | 0–1 | Read the lab's alumni page. Top faculty placements: 0.8+, mix academia+industry: 0.5–0.7, mostly post-docs: 0.4. |

Each should have an entry in `candidate.evidence` with sources.

### `pi_signal` enum

| Value | Adjustment | When to use |
|-------|------------|-------------|
| `"strong"` | +0.2 | ≥2 new PhDs/yr last 3y per lab page |
| `"normal"` | 0 | 1–2/yr per lab page |
| `"shrinking"` | −0.4 | <1/yr OR many recent graduations without admits |
| `"missing"` | −0.1 | Page didn't load / didn't have a students list / status unclear (default — never guess) |
| `"not_recruiting"` | force application_strength = 0 | Explicitly stated |

### Minimal valid CandidateAdvisor

```jsonc
{
  "id": "cand_001",
  "name": "Prof. Jane Doe",
  "institution": "Stanford University",
  "school_tier": "top_10",
  "field": "chemistry",
  "research_areas": ["catalysis"]
}
```

Other fields default to safe values (empty paths, 0 / false / "missing"
signals). The matcher will rank this candidate low because so many signals
are unverified — the confidence band will be ≥ ±0.6.

---

## MatchResult (output)

```jsonc
{
  "candidate": { ... },
  "c_score": 3.70,
  "p_score": 3.30,
  "e_score": 3.25,
  "g_score": 3.85,
  "match_score": 3.53,
  "application_strength": 2.53,        // renamed from admit_likelihood
  "confidence_band": 0.40,
  "strength_label": "Target",          // renamed from likelihood_label
  "explanation": "co-authored 3 small-team paper(s) with Prof. Wang in last 5y [https://scholar.google.com/...] · research: catalysis, C-H activation · ...",
  "unverified_signals": 2
}
```

`application_strength` is **NOT a probability**. It's a 4.0-scale relative-fit
index combining match_score with school competitiveness and PI recruiting
signal. See [`docs/scoring.md`](../docs/scoring.md) for the formula.
