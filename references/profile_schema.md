# Profile JSON schema

Canonical shape of the input the skill expects. See `phd_matcher/models.py` for
the Pydantic source of truth; this file is the human-readable reference.

## Top-level

```jsonc
{
  "name": "Optional display name",
  "field": "physics",                    // REQUIRED — "physics" | "mse"
  "undergrad_institution": "...",        // REQUIRED
  "master_institution": null,            // optional
  "gpa_raw": 3.82,                       // REQUIRED — number or string
  "gpa_scale": "4.0",                    // REQUIRED — see below
  "research_direction": "...",           // REQUIRED — short paragraph

  "current_advisors": [ ... ],           // recommended
  "papers":           [ ... ],           // recommended
  "experiences":      [ ... ]            // recommended
}
```

## `gpa_scale` enum

| Value | System |
|-------|--------|
| `"4.0"` | US 4.0 |
| `"4.3"` | Some Canadian / Asian |
| `"4.5"` | Some Chinese tech schools |
| `"100"` | Chinese percentage (`gpa_raw` is 0–100) |
| `"uk"` | UK honours (`gpa_raw` is `"first"` / `"high_2_1"` / `"low_2_1"` / `"2_2"` / `"third"`) |

## `current_advisors[]`

```jsonc
{
  "id": "adv_001",                       // generate sequentially
  "name": "Prof. Lisa Wang",
  "institution": "Tsinghua University"
}
```

The `id` is what the matcher uses to look up `paths_to_advisors[id]` on each
candidate — it does not need to be globally unique, just consistent within
this profile.

## `papers[]`

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

Tier mapping quick ref (full table in `references/journal_tiers.md`):

- `"S"` (4.0): Nature / Science / Cell main
- `1` (4.0): PRL, Nature Phys, JACS, Nature Mater, Adv Mater, Nano Lett
- `2` (3.7): PRX, JHEP, ApJL, Adv Funct Mater, ACS Nano, Materials Today
- `3` (3.3): PRD, PRA-E, Chem Mater, J Mater Chem A/B/C, Nanoscale
- `4` (2.8): PR Applied, J Appl Phys, J Mater Sci
- `5` (2.3): weak / workshop
- `0`: retracted / predatory (zero-out)

## `experiences[]`

```jsonc
{
  "lab_pi_name": "Prof. Lisa Wang",
  "lab_tier": "strong_us_or_top_cn",     // see enum below
  "duration_months": 18,                 // integer; convert any duration to months
  "output_type": "honors_thesis"         // see enum below
}
```

`lab_tier` enum:

| Value | Criteria |
|-------|----------|
| `"world_class"` | HHMI / Max Planck / NAS member / Top 10 US PI / national lab |
| `"top_us"` | Top 11–40 US PI |
| `"strong_us_or_top_cn"` | Top 41–70 US PI / Tsinghua / PKU / Fudan / SJTU / C9 prominent PI |
| `"good_us_or_985"` | Top 71–100 US / 985 regular PI |
| `"211_or_overseas"` | 211 schools / overseas regular school |
| `"other"` | rest |

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

## Minimal valid example

```jsonc
{
  "field": "physics",
  "undergrad_institution": "Some University",
  "gpa_raw": 3.5,
  "gpa_scale": "4.0",
  "research_direction": "experimental high energy physics"
}
```

This works. Pub / experience / connection will all use defaults (no-paper
floor, base experience, field-only connection). For a meaningful match,
include at least one current advisor and one paper.

## Full example

See `data/samples/sample_student_physics.json` and
`data/samples/sample_student_mse.json` in the repo.
