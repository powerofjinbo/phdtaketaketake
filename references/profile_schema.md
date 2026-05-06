# Profile + CandidateAdvisor JSON schema

Canonical shapes of the inputs the matcher expects. See `phd_matcher/models.py`
for the Pydantic source of truth; this file is the human-readable reference.

## StudentProfile (input to the matcher)

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

`field` accepts any string (e.g., `"physics"`, `"chemistry"`, `"biology"`,
`"mse"`, `"cs"`, `"math"`, `"ee"`, `"chemical_engineering"`, `"earth_science"`).
Bundled candidate cache exists for `physics` and `mse`; for other fields
generate candidates via `--candidates-json` (see
[`SKILL.md`](../SKILL.md) for the workflow).

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
  "id": "adv_001",                       // generate sequentially
  "name": "Prof. Lisa Wang",
  "institution": "Tsinghua University"
}
```

The `id` is what the matcher uses to look up `paths_to_advisors[id]` on each
candidate.

### `papers[]`

```jsonc
{
  "title": "Search for new physics in dijet events with the ATLAS detector",
  "journal": "Physical Review D",
  "journal_tier": 3,                     // REQUIRED — 0 | "S" | 1 | 2 | 3 | 4 | 5
  "author_position": 312,                // REQUIRED — 1-indexed; ATLAS/CMS papers can be 100+
  "year": 2024,                          // optional
  "doi": null                            // optional
}
```

Tier mapping is universal across STEM — see
[`references/journal_tiers.md`](journal_tiers.md).

**Paper inclusion convention**: list every paper the user expects to have on
their CV by the PhD application deadline. The skill does **not** distinguish
between `published` / `accepted` / `in press` / `submitted` / `in prep`. This
is intentional simplification — the user is responsible for only listing
papers they're confident will appear by application time, and the matcher
trusts that listing.

### `experiences[]`

```jsonc
{
  "lab_pi_name": "Prof. Lisa Wang",
  "lab_tier": "strong_us_or_top_cn",     // see lab_tiers.md
  "duration_months": 18,                 // integer; convert any duration to months
  "output_type": "honors_thesis"         // see enum below
}
```

`lab_tier` enum: see [`references/lab_tiers.md`](lab_tiers.md).

`output_type` enum:

| Value | Notes |
|-------|-------|
| `"paper"` | already counted in pub_score; assign 3.7 here so experience isn't penalized |
| `"conference_oral"` | invited or contributed talk |
| `"conference_poster"` | poster |
| `"honors_thesis"` | undergrad thesis / project report |
| `"participation_only"` | RA without measurable output |

The matcher takes the **strongest single experience** (no stacking) — the user's
best lab × duration × output combination drives E.

### Minimal valid example

```jsonc
{
  "field": "biology",
  "undergrad_institution": "Some University",
  "gpa_raw": 3.5,
  "gpa_scale": "4.0",
  "research_direction": "single-cell transcriptomics in cancer immunology"
}
```

This works. Pub / experience / connection will all use defaults (no-paper
floor, base experience, field-only connection). For a meaningful match,
include at least one current advisor and one paper.

### Full examples

See `data/samples/sample_student_physics.json` and
`data/samples/sample_student_mse.json` in the repo.

---

## CandidateAdvisor (input via `--candidates-json` for non-bundled fields)

When you (Claude) generate candidates for a field outside the bundled cache
(physics, mse), each candidate is a JSON object of this shape:

```jsonc
{
  "id": "cand_001",                          // any unique string
  "name": "Prof. Jane Doe",
  "institution": "Stanford University",
  "school_tier": "top_10",                   // top_10 | top_11_30 | top_31_60 | top_60_plus
  "field": "chemistry",                      // must match student.field
  "research_areas": [                        // 3–5 short tags
    "homogeneous catalysis",
    "C-H activation",
    "transition metal complexes"
  ],
  "recent_papers": [],                       // optional; can leave empty

  "paths_to_advisors": {                     // KEY field — see below
    "adv_001": {
      "coauthor_papers_5y": 3,
      "collaboration_overlap_years": 4
    }
  },

  "normalized_collab_top20pct": 0.6,         // 0–1 — fraction of candidate's collaborators that are top-20% PIs in field
  "collab_with_nas": false,                  // true if candidate has co-authored with NAS / HHMI member
  "grad_placement_quality": 0.7,             // 0–1 — quality of recent PhD graduates' placements

  "pi_signal": "normal",                     // strong | normal | shrinking | missing | not_recruiting
  "recent_phd_count": 4                      // optional; integer or null
}
```

### `paths_to_advisors` — the connection graph edges

Keys are the `id`s of the student's `current_advisors`. Values are dicts with
any subset of these edge types (the matcher takes the **max strength**, no
stacking):

| Edge field | Type | Meaning |
|------------|------|---------|
| `coauthor_papers_5y` | int | How many papers the student's advisor and the candidate co-authored in the last 5 years |
| `genealogy_relation` | string | `"same_advisor"` (siblings) / `"uncle_nephew"` / `"two_hop"` |
| `collaboration_overlap_years` | float | Years they've been jointly in the same big collaboration / consortium |
| `committee_co_member` | bool | Whether they sit / sat on the same editorial board / NSF panel / PC |
| `same_period` | bool | If `committee_co_member` is true: whether they overlapped in time |

**For uncovered fields where you (Claude) are generating candidates**: only
fill `paths_to_advisors` if you have specific knowledge that the user's
advisor and the candidate are connected. **Don't fabricate edges.** Empty
`paths_to_advisors: {}` is fine — the C score will reduce to field strength
only, and the explanation will surface that.

### Field-strength fields (estimate from your knowledge)

| Field | Range | Estimation guidance |
|-------|-------|---------------------|
| `normalized_collab_top20pct` | 0–1 | What fraction of this PI's collaborators are top-20% PIs in their field? Famous PI: 0.7+. Mid-career: 0.4–0.6. Junior: 0.2–0.4. |
| `collab_with_nas` | bool | Has co-authored with NAS / HHMI / equivalent within last ~5 years |
| `grad_placement_quality` | 0–1 | Where do their recent PhD graduates end up? Top faculty placements: 0.8+. Industry top labs: 0.7. Mixed: 0.5–0.6. Mostly post-docs: 0.4. |

### `pi_signal`

How actively the PI is recruiting PhD students:

| Value | Meaning | Adjustment |
|-------|---------|------------|
| `strong` | ≥2 new PhDs/yr in last 3 yr | +0.2 |
| `normal` | 1–2 new PhDs/yr | 0 |
| `shrinking` | <1 new PhDs/yr | −0.4 |
| `missing` | unknown / data not available | −0.1 |
| `not_recruiting` | explicitly not taking students | force admit_likelihood = 0 |

**For uncovered fields**: default to `"missing"` unless you specifically know
the PI's recent recruiting pattern.

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

The rest default to safe values: empty paths, 0 field-strength signals,
`pi_signal: "missing"`. The result will rank low (no connection signal, no
NAS, no placement signal) — for a useful ranking, populate the field-strength
fields with your best estimates.
