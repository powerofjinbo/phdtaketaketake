# Candidate discovery — finding PIs and verifying connections

The deep-research half of the skill. The matcher runs deterministically
once candidates are JSON-ready; this file covers the half that depends
on the agent actually fetching pages.

> **Cardinal rule**: every value comes from a real URL the agent fetched
> via web search. No guessing from training memory.
> See [`data_integrity.md`](data_integrity.md).

## Step 3 detail — finding candidate PIs

For each target program, query:

```
<school> <department> "<user research keywords>" faculty
```

For each PI, capture the minimum:

- `id` — any unique string (e.g., `cand_001`)
- `name`, `institution`
- `school_tier` — from the **field-specific** ranking page (top_10 /
  top_11_30 / top_31_60 / top_60_plus)
- `field` — same as student.field
- `research_areas` — 3–5 short tags from faculty profile / recent papers

Quality bar:
- ≥1 paper in last 3 years matching the direction
- skip emeriti, deans, full pivots to admin/industry
- aim for 10–30 candidates per query (the matcher caps at top-K)

## Step 4 detail — connection edges

The high-leverage step. Differentiate **small-team** (real working
relationship) from **big-collab** (alphabetical author-list co-membership)
using the FieldProfile threshold:

| field | big_collab_threshold (>N authors) |
|-------|-----------------------------------|
| physics | 10 (ATLAS-aware) |
| mse / cs | 8 |
| biology / chemistry | 6 |
| math | 4 |

Use `classify_coauthorship(total_authors, field_profile)` in
`phd_matcher/scoring/pub.py` to bucket consistently.

### Database recipes (per-field priority)

```
- Google Scholar:    "<advisor full name>" "<candidate full name>"
                     site:scholar.google.com

- OpenAlex API:      https://api.openalex.org/works?filter=
                     authorships.author.id:<advisor_id>,
                     authorships.author.id:<candidate_id>

- INSPIRE-HEP:       https://inspirehep.net/search?p=a+<advisor>+a+<candidate>
                     (preferred for physics)

- PubMed:            https://pubmed.ncbi.nlm.nih.gov/?term=<a>+AND+<b>
                     (biology/medicine)

- Semantic Scholar:  https://api.semanticscholar.org/graph/v1/paper/search?...
                     (CS pairs)

- DBLP:              https://dblp.org/search?q=<a>+<b>
                     (CS publication graph)

- arXiv:             https://arxiv.org/a/<author_id>
                     (math, theoretical CS, physics theory)

- Math Genealogy:    https://www.genealogy.math.ndsu.nodak.edu/?id=...
                     (PhD lineage — gold standard for math, useful for physics/bio)
```

Field-specific priorities live in `FieldProfile.primary_databases`. Use
those before generic Scholar.

### Per-edge evidence (structured items)

For each co-authored paper found, **check the author count first**:

- ≤ threshold → `small_team_coauthor_5y` (full strength, max 1.0 at n=5+)
- > threshold → `big_collab_papers_5y` (heavily discounted, max 0.4)

Record evidence per signal with `supports_fields` binding. See
[`evidence_schema.md`](evidence_schema.md) for the full pattern.

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "small_team_coauthor_5y": 3,
    "big_collab_papers_5y": 12,
    "same_working_group": true,
    "items": [
      { "url": "...", "source_type": "google_scholar",
        "claim": "3 ≤10-author papers 2022-2024",
        "supports_fields": ["small_team_coauthor_5y"] },
      { "url": "...", "source_type": "inspire",
        "claim": "12 ATLAS bulk publications 2020-2024",
        "supports_fields": ["big_collab_papers_5y"] },
      { "url": "...", "source_type": "lab_page",
        "claim": "both H→cc̄ working-group conveners 2021-2023",
        "supports_fields": ["same_working_group"] }
    ]
  }
}
```

### Connection-v2 edges (Sprint-2-c1 — additive)

Beyond the v1 edges (small_team / big_collab / working_group / analysis_contact /
genealogy / collaboration_overlap / committee_co_member), v2 adds:

| Edge | When to set | Cite |
|------|-------------|------|
| `shared_grant_count_5y` | NSF/NIH/DOE shared grant in last 5y | NIH RePORTER, NSF Award Search, DOE Office of Science |
| `co_mentored_student_count` | Both PIs co-supervised a student (committee co-mentorship counts) | dissertation acknowledgements, lab alumni page, committee composition page |
| `committee_or_exam_overlap` | Both served on the same PhD committee or qualifying exam | dissertation cover page, department exam records |
| `same_center_or_institute` | Both members of the same NSF ERC / NIH center / DOE national lab / interdisciplinary institute | center website member list, institute affiliations on faculty pages |
| `prior_institution_overlap_years` | Years both at the same institution before either's current role | CVs, faculty bios |
| `conference_session_overlap_5y` | Conferences in last 5y where both presented at the same session/track | conference programmes, OpenReview, DBLP author pages |
| `most_recent_connection_year` | Year of last direct interaction — drives the **recency multiplier** | derived from the year on the strongest cited edge (latest co-authored paper, latest shared grant, etc.) |

Each set field needs evidence with `supports_fields=[<field>]` (or one
verified-empty `supports_fields=["path:<id>"]`). The recency year is
metadata derived from already-cited evidence — no separate evidence
needed.

### Big-collaboration patterns (HEP, large clinical trials, consortia)

If shared papers are all big-collab (alphabetical), look for stronger
signals before claiming a real connection:

- `same_working_group: true` — both documented as ATLAS subgroup /
  convener team (verify via INSPIRE-HEP or working-group page)
- `analysis_contact_overlap: true` — both listed as analysis contacts
  on a specific paper / internal note (paper-specific contact list)

Estimate overlap years from documented join/leave dates →
`collaboration_overlap_years` (float).

### Academic genealogy

```
- Mathematics Genealogy Project (gold standard for math, useful elsewhere)
  https://www.genealogy.math.ndsu.nodak.edu/

- Faculty bios (often state "PhD under Prof. X, year")
```

| `genealogy_relation` | strength |
|---------------------|----------|
| `same_advisor` (academic siblings) | 1.0 |
| `uncle_nephew` (advisor's PhD sibling) | 0.7 |
| `two_hop` (advisors' advisors crossed paths) | 0.4 |

**Don't infer from name patterns or institutional history alone.** If
Math Genealogy returns nothing and the bio doesn't mention the lineage,
leave the edge empty.

### Editorial / committee co-membership

Weak signal — only count when documented (journal masthead, NSF panel
report, conference PC list):

```jsonc
"committee_co_member": true,
"same_period": true   // 0.8 if true, 0.3 if different periods
```

### Verified-empty path (the honest negative)

When you searched and found no edges, record the search itself:

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "items": [{
      "url": "https://scholar.google.com/citations?user=...&q=Wang+candidate",
      "source_type": "google_scholar",
      "claim": "searched 2020-2024: 0 co-authored papers, no shared lineage",
      "supports_fields": ["path:adv_001"]
    }],
    "note": "also checked Math Genealogy — neither party in DB"
  }
}
```

Strict mode requires this `supports_fields=["path:<id>"]` form for
verified-empty. See [`evidence_schema.md`](evidence_schema.md) for why.

The C score reduces cleanly to its lowest bucket (2.3) when no path is
verified — PI prestige is captured separately in the A pillar.

## Step 5 detail — advisor-influence signals (A dimension)

Properties of the candidate themselves — *not* about your connection to
them. These feed the **A pillar** in CAPEG. Three-state semantics:

| State | Means | Pattern |
|-------|-------|---------|
| **Verified** | searched, found a value | set value + `evidence[<field>].items` with `supports_fields=[<field>]` |
| **Verified-empty** | searched, found nothing | leave value at default (`null` / `false` / 0) + cite the search with `supports_fields=[<field>]` |
| **Missing** | didn't search | leave value `null`; no evidence — counts as missing, widens band |

A composite (sum to 1.0):

- 0.30 · influence (h-index proxy)
- 0.20 · elite_status (NAS / HHMI / NAE / field fellow)
- 0.20 · active_funding_quality
- 0.20 · grad_placement_quality
- 0.10 · recruiting_health (derived from `pi_signal`)

### `normalized_collab_top20pct` (0–1)

Proxy via h-index from Google Scholar / OpenAlex. Formula:
`min(1.0, h_index / 50)`.

```jsonc
"normalized_collab_top20pct": 0.7,
"evidence": {
  "normalized_collab_top20pct": {
    "items": [{
      "url": "https://scholar.google.com/citations?user=<author_id>",
      "source_type": "google_scholar",
      "claim": "h_index = 35 (checked 2026-05-06)",
      "supports_fields": ["normalized_collab_top20pct"]
    }]
  }
}
```

### `collab_with_nas` (bool)

Three-state, **strict semantics**:

- `null` — didn't search → **missing**
- `false` + sources → searched, no recent NAS / HHMI co-author
  (**verified-empty**)
- `true` + sources → found a specific co-author in the official directory

### `grad_placement_quality` (0–1)

Read the lab's "alumni" / "former students" page:

| range | placement profile |
|-------|-------------------|
| 0.8+  | top faculty |
| 0.5–0.7 | academia + industry mix |
| 0.4   | mostly post-docs |

If no alumni page, leave `null`. **Do not** fall back to 0.5 — fake
defaults pretend to be real signals.

### `active_funding_quality` (0–1)

Cite NIH RePORTER / NSF Award Search / DOE Office of Science / ERC /
DARPA grant records:

| value | profile |
|-------|---------|
| 0.85  | active R01 + NSF CAREER (or equivalent) |
| 0.4   | single small grant |
| 0.0 + sources | searched, no active grants found (verified-empty) |
| `null` | didn't search → missing |

### Discipline-specific elite signals

Use `collab_with_nas=true` and cite:

- **biology**: HHMI investigator, NAS / NAM membership
- **CS**: ACM / IEEE Fellow, OpenReview reviewer profile, top-venue track record
- **physics**: APS Fellow, DOE Office of Science principal, big-collab convener
- **chemistry / MSE**: ACS / RSC / MRS / NAE membership
- **math**: AMS Fellow, ICM invited speaker, Sloan / Packard Fellow

## Step 6 detail — `pi_signal` (recruiting health)

**Fetch** the lab / faculty page (don't assume from memory). Read the
current-students list / "join the lab" page / "applying" notes:

| value | meaning |
|-------|---------|
| `"strong"` | ≥2 new PhDs/yr last 3y |
| `"normal"` | 1–2/yr |
| `"shrinking"` | <1/yr or many recent graduations without admits |
| `"missing"` | page didn't load / no list / status unclear (default — never guess) |
| `"not_recruiting"` | explicitly stated. **Forces application_strength = 0.** |

`pi_signal` feeds two distinct uses (NOT double-counting):

- A's `recruiting_health` term (lab health signal)
- `application_strength`'s `pi_adj` (admit-cycle availability)

Different questions, separate outputs.

## Don't fill in fake defaults

A 0.5 written into the JSON without sources counts as unverified — same
as `null` without sources — but pretends to be a real signal. The
matcher's confidence band widens either way; honesty in the JSON helps
the user read the result.
