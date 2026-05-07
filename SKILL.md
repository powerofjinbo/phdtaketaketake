---
name: phdtaketaketake
description: Score a PhD applicant's profile and rank candidate advisors using a connection-first 4.0-scale scoring system. Best-supported for physics / HEP and materials science (MSE), with the scoring engine extensible to chemistry, biology, CS, math, EE, ChemE, earth science (each with field-specific caveats — see references/journal_tiers.md). Use when the user wants to evaluate their PhD application chances, find matching advisors at top US programs, score a CV for graduate school, or compare candidate professors. Also triggers when the user mentions phdtaketaketake or its connection-first philosophy of valuing advisor network over h-index.
---

# phdtaketaketake — Connection-first PhD advisor matcher

## ⚠️ CARDINAL RULE — REAL DATA ONLY

**Every connection edge, every candidate fact, every signal value MUST trace
back to a real source you actually fetched via web search.** Fabrication is
strictly forbidden — students use these rankings to decide where they spend
years of their life. Made-up data is worse than no data.

**The contract:**
- ✅ Verified via web search → record value + structured `EvidenceSource`
  (URL + source_type + claim + supports_fields)
- ✅ Searched but found nothing → leave the field empty / set signal to `"missing"`
- ❌ Guessed from training memory → **NOT ALLOWED**
- ❌ Inferred from name patterns / school proximity / "feels likely" → **NOT ALLOWED**
- ❌ Estimated without any web search → **NOT ALLOWED**

**Two enforcement layers:**

1. **Risk-adjusted ranking** — wide confidence bands move candidates
   *down* the sort order. The agent literally cannot get a top rank with
   unsourced claims; the band widens and `risk_adjusted_strength = strength
   − band/2` drops below better-evidenced peers.

2. **`--strict-evidence` flag** — when run with this flag, `scripts/match.py`
   rejects any candidate that has *unsourced* claims (a value set without an
   `EvidenceEntry`). Missing signals (no value, no evidence) are still
   allowed — they're honest "I couldn't verify" states. Use this when the
   user is making real application decisions.

The matcher's confidence band (±0.2 / 0.4 / 0.6 / 0.8 — see §Confidence
calibration below) handles missing data gracefully, AND the risk-adjusted
ranking subtracts band/2 from the sort key — so wide bands move candidates
down the list. A wide band on **real** data is far more useful than a narrow
band on **made-up** data.

Full allowed-source list and forbidden-behavior catalog:
[`references/data_integrity.md`](references/data_integrity.md). Read it
before doing any connection research.

---

This skill ranks candidate PhD advisors for a student by **network-connection
strength** to the student's current research advisor, on a 4.0 scale across:

- **Connection (C)** — co-author + genealogy + joint collaborations + committee
- **Publication (P)** — journal tier × author position decay (5+ author rule)
- **Experience (E)** — lab × duration × output (output-weighted 50%)
- **GPA (G)** — direct, with multi-system normalization

Final scores tier-adaptively weighted by school competitiveness. Admit
likelihood incorporates the candidate PI's recruiting signal.

## Step 0 — Load the FieldProfile

Before running any deep-research, **load the FieldProfile for the user's
discipline**. This is the per-field calibration layer that tells you
which databases to search, how to bucket papers, and what caveats to
surface. Bundled profiles:

| field id | aliases | notable rules |
|----------|---------|---------------|
| `physics` | `hep`, `hep-ex`, `hep-ph`, `hep-th`, `astrophysics`, `condensed matter` | `journal_first`; big_collab_threshold=10; INSPIRE-HEP primary |
| `mse` | `materials`, `nano`, `nanotechnology` | `journal_first`; big_collab_threshold=8; senior author = last |
| `cs` | `ml`, `machine learning`, `ai`, `nlp`, `cv`, `systems`, `theory`, `hci` | **`conference_first`**; co-first supported; CSRankings, not US News |
| `biology` | `bio`, `genetics`, `neuroscience`, `immunology`, `microbiology`, `biochemistry` | `journal_first`; co-first common; PubMed/bioRxiv; HHMI strong signal |
| `chemistry` | `chem`, `organic`, `inorganic`, `physical chemistry` | `journal_first`; senior author = last |
| `math` | `mathematics`, `applied math`, `pure math`, `statistics` | **`preprint_first`**; arXiv often canonical; Math Genealogy authoritative |

The matcher resolves aliases (e.g., user types `"hep"` → loads
`physics.yaml`). The resolved profile flows into the result as
`field_profile_id` and `field_caveats`; **always surface the caveats in
your result presentation** — they are how the matcher tells the user
"this discipline has the following gotchas".

For an unbundled field (e.g., `"materials_chemistry"`), the matcher
returns `field_profile_id: null` — fall back to the cross-field guidance
in `references/journal_tiers.md` and your domain knowledge, and tell the
user explicitly "no profile bundled for this field".

## Architecture: no static cache, always real-time research

There is **no bundled candidate cache**. PhD advisor data is too dynamic
(people change institutions, retire, take new students, pivot subfields) and
too vast (millions of PIs across STEM) for any static dataset to be useful.

Instead, the split:

- **You (the agent)** — do the deep research. Use web search + page fetch +
  whatever tools you have to find candidates and verify connection edges.
- **`scripts/match.py`** — pure Python. Takes the profile + candidates you
  built and runs the deterministic scoring (Pub/GPA/Experience/Connection
  combination, tier-adaptive weights, application_strength with confidence band).

This makes the skill universal across STEM fields and always-fresh.

## Workflow

### Step 1 — Gather student profile

Required fields (must ask if missing):

- `field` — any STEM string (`"physics"`, `"chemistry"`, `"biology"`, etc.)
- `undergrad_institution`
- `gpa_raw` + `gpa_scale`
- `research_direction` — short paragraph (≥30 words is best)

Recommended (each materially changes ranking — **proactively ask**):

- `current_advisors[]` — `{id, name, institution}`. Without this, the entire
  Connection score collapses to candidate's field strength only.
- `papers[]` — `{title, journal, journal_tier, author_position, status, year}`.
  Without this, P score floors at 3.0.

  **Paper-status weights**: `published` / `accepted` / `in_press` get full
  credit; `submitted` / `preprint` get 0.7×; `in_prep` gets 0.3×. List
  status honestly. Default is `"published"`. **Schema is strict** —
  unknown status values raise. Field-specific overrides apply (e.g.,
  math sets `preprint=0.9` because arXiv is often the canonical record).

  **Optional P1 fields** (use when you can):
    - `venue_type`: `journal` / `conference` / `workshop` / `preprint` /
      `clinical_trial` — useful for CS where conferences = top venues
    - `author_role`: `first` / `co_first` / `middle` / `senior` /
      `corresponding` / `consortium`. When set, **`co_first` /
      `corresponding` / `senior` are scored as 1st-author equivalent
      regardless of byline position**. Use `co_first` for biology
      "These authors contributed equally" cases.
    - `total_authors`: total author count on the paper. Use the
      `classify_coauthorship(total_authors, field_profile)` helper to
      bucket `path_edge.small_team_coauthor_5y` vs `big_collab_papers_5y`
      with the right per-field threshold (physics 10, mse/cs 8,
      biology/chemistry 6, math 4).
- `experiences[]` — `{lab_pi_name, lab_tier, duration_months, output_type}`.
  Without this, E score defaults to 2.0.

Source priority:
1. CV / resume pasted or attached → parse it, then **show the inferred
   profile back to the user for confirmation** before continuing.
2. Existing profile JSON → use directly.
3. Prose description → ask brief targeted batches for missing fields. Don't
   dump a 10-question list at once.

For mappings (`gpa_scale`, `journal_tier`, `lab_tier`, `output_type`,
`author_position` for big-collab papers): see `references/profile_schema.md`
and `references/journal_tiers.md`. When uncertain about a journal tier,
ask the user or default to tier `4`.

### Step 2 — Determine target programs (with cited ranking source)

Ask the user where they want to apply. Acceptable inputs:
- Specific schools (e.g., MIT, Stanford, Princeton)
- A tier ("top 10 physics", "top 30 chemistry")
- Specific professors they have in mind ("I'm interested in Prof. X")
- Open-ended ("show me the best matches")

**Per the cardinal data-integrity rule**, school tier is now a sourced
signal — not memorized. **Fetch the field-appropriate ranking page**.
The right source depends on field; use the loaded FieldProfile's
`ranking_source_url_template` first:

| field | preferred ranking source |
|-------|--------------------------|
| `physics` / `mse` / `chemistry` / `biology` / `math` | US News field-specific page (URL template in profile) |
| `cs` | **CSRankings** (`https://csrankings.org/`) — community-maintained, more reliable than US News for CS subfields |

Generic US News science page is a fallback only when no profile applies.

Record the URL in `evidence["school_tier"].items` for every candidate
you generate, with `supports_fields=["school_tier"]`:

```jsonc
"evidence": {
  "school_tier": {
    "items": [{
      "url": "https://www.usnews.com/best-graduate-schools/...",
      "source_type": "us_news",
      "claim": "MIT physics ranked top 10 in 2024",
      "supports_fields": ["school_tier"]
    }]
  }
}
```

Without claim-level evidence (or in strict mode without items at all),
`school_tier` counts as unverified and the candidate's confidence band
widens.

If the user gives a tier, use the **fetched ranking** to enumerate target
schools (~10–20). Don't enumerate from training memory — rankings change
year-to-year and your training data may be stale.

### Step 3 — Find candidate PIs (research direction match)

For each target program, web-search for active PIs whose research matches the
user's `research_direction`:

```
<school> <department> "<user research keywords>" faculty
```

For each PI you find, capture:
- `id` — any unique string (e.g., `cand_001`)
- `name`, `institution`
- `school_tier` — based on the **field-specific** US News PhD ranking
  (`top_10` / `top_11_30` / `top_31_60` / `top_60_plus`)
- `field` — same as student.field
- `research_areas` — 3–5 short tags from their faculty profile / recent papers

Quality bar: PI should have ≥1 paper in last 3 years matching the direction.
Skip emeriti, deans, and people who've fully pivoted to admin / industry.

Aim for 10–30 candidates per query. The matcher caps at top-K anyway.

### Step 4 — Compute connection edges (THE core IP)

For **each** candidate, search for verifiable connection signals to the
user's `current_advisors`. **Re-read the cardinal rule above** — every
edge must be backed by an actual web-search result, with a URL you can
cite. No guessing from training memory.

**Direct co-authorship — DIFFERENTIATE small-team vs big-collab.** This
distinction matters: co-authoring a 5-person condensed-matter paper is
real evidence of working together; co-name on an alphabetical 3000-author
ATLAS paper is just shared collaboration membership.

The threshold for "big collab" is **field-specific** — see the loaded
FieldProfile's `big_collab_threshold`:

| field | threshold (>N authors → big collab) |
|-------|-------------------------------------|
| physics | 10 (ATLAS-aware) |
| mse / cs | 8 |
| biology / chemistry | 6 |
| math | 4 |

Use the right threshold per field instead of always assuming 10.

Search the FieldProfile's `primary_databases` first (e.g., INSPIRE-HEP
for physics, DBLP for CS, PubMed for biology). Generic Google Scholar is
a fallback. Specifically:

```
- Google Scholar:  "<advisor full name>" "<candidate full name>"
                   site:scholar.google.com
- OpenAlex API:    https://api.openalex.org/works?filter=
                   authorships.author.id:<advisor_id>,
                   authorships.author.id:<candidate_id>
- INSPIRE-HEP:     https://inspirehep.net/search?p=a+<advisor>+a+<candidate>
                   (preferred for physics)
- PubMed:          for biology/medicine pairs
- Semantic Scholar: for CS pairs
```

For each co-authored paper found, **check author count** before tallying:

- ≤ 10 authors → counts toward `small_team_coauthor_5y` (full strength)
- > 10 authors → counts toward `big_collab_papers_5y` (heavily discounted)

If the candidate-advisor relationship is in a big-collab field (HEP, large
clinical trials, BICEP / LIGO, etc.) and you find shared papers but they're
all big-collab, look for **stronger evidence** before claiming connection:
- `same_working_group: true` if both are documented members of the same
  ATLAS subgroup / convener team (verify via INSPIRE-HEP or working-group
  page)
- `analysis_contact_overlap: true` if both are listed as analysis contacts
  on a specific paper / internal note (verify via published authorship page
  or paper-specific contact list)

**Record sources for every edge.** Use the structured `items` field
(preferred) so each URL is bound to a specific claim:

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "small_team_coauthor_5y": 3,
    "big_collab_papers_5y": 12,
    "same_working_group": true,
    "items": [
      {
        "url": "https://scholar.google.com/citations?user=<id>&...",
        "source_type": "google_scholar",
        "claim": "3 co-authored papers in 2022-2024 with ≤10 authors",
        "supports_fields": ["small_team_coauthor_5y"]
      },
      {
        "url": "https://inspirehep.net/authors/<candidate>/...",
        "source_type": "inspire",
        "claim": "12 ATLAS publications co-authored 2020-2024",
        "supports_fields": ["big_collab_papers_5y"]
      },
      {
        "url": "https://atlas-glance.cern.ch/atlas/analysis/<group>/conveners",
        "source_type": "lab_page",
        "claim": "both listed as H→cc̄ working group conveners 2021-2023",
        "supports_fields": ["same_working_group"]
      }
    ],
    "note": "3 small-team co-authored papers, 12 ATLAS bulk, both H→cc̄ conveners"
  }
}
```

The legacy `sources: list[str]` (bare URLs) is still accepted for
backward compatibility but **prefer the structured `items` form** — it
makes claims auditable: each URL is bound to a specific `supports_fields`
list, so a reviewer can verify each claim individually rather than
guessing which URL backs which signal.

**Joint big-collaboration** (ATLAS, CMS, BICEP, LIGO, multi-institution
clinical trials, large genome consortia):

Verify membership via the consortium's published author list, the
candidate's CV / lab page, or INSPIRE-HEP collaboration tracking — **not
training memory**. Estimate overlap years from documented join/leave
dates → `collaboration_overlap_years` (float).

**Academic genealogy** (PhD lineage shared):

```
- Mathematics Genealogy Project: https://www.genealogy.math.ndsu.nodak.edu/
  (authoritative for physics, math, some bio)
- Faculty bios on the candidate's lab / department page
  (often state "PhD under Prof. X, year")
```

Match types:
- Same PhD advisor (academic siblings) → `"same_advisor"` (1.0)
- Advisor is PhD sibling / nephew of candidate → `"uncle_nephew"` (0.7)
- Two-hop (advisors' advisors crossed paths) → `"two_hop"` (0.4)

**Don't infer from name patterns / institutional history alone.** If
Mathematics Genealogy returns nothing and the faculty bio doesn't mention
the lineage, leave the genealogy edge empty.

**Editorial / committee co-membership** (weaker signal): only count when
you've found documented evidence (a journal masthead, NSF panel report,
conference PC list). → `committee_co_member: true`, `same_period: bool`

**Take the MAX of these edges, do NOT sum.** The matcher treats them as
mutually exclusive (avoids double-counting).

If no edge found via search, **record what you searched** with a
`supports_fields=["path:<advisor_id>"]` item — strict mode requires this
verified-empty form (bare URLs in `sources` won't pass strict):

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

The C score reduces cleanly to field strength only when no edges are
found. **An empty `paths_to_advisors[adv_id] = {}` is missing data**
(silently penalized) — prefer the verified-empty form above so the
matcher can credit you for searching.

### Step 5 — Advisor influence signals (per candidate, drive the A dimension)

Properties of the candidate themselves — *not* about your connection to
them. These feed the **A pillar** in the 5-dim CAPEG match formula
(roadmap #3). **Three-state semantics**: each field is either
verified-with-sources, verified-empty (value remains `null`/`false`
+ sources documenting the search), or omitted (no value, no sources →
counts as unverified).

The A composite (sum to 1.0):
- 0.30 · influence (h-index proxy)
- 0.20 · elite_status (NAS / HHMI / NAE / field fellow)
- 0.20 · active_funding_quality
- 0.20 · grad_placement_quality
- 0.10 · recruiting_health (derived from pi_signal)

Fields:

- `normalized_collab_top20pct` (0–1, default `null`): proxy via candidate's
  h-index from Google Scholar or OpenAlex. Formula: `min(1.0, h_index / 50)`.
  Cite the profile URL in `evidence["normalized_collab_top20pct"].items`
  with `supports_fields=["normalized_collab_top20pct"]`:

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
- `collab_with_nas` (bool, default `null`): three-state, **strict** about
  semantics:
    - `null` (default) — you didn't search the NAS / HHMI directory; no
      claim. The signal counts as missing.
    - `false` — you searched and confirmed no recent NAS / HHMI co-author.
      Record evidence with `supports_fields=["collab_with_nas"]` citing
      the searched directory pages; this counts as **verified-empty**.
    - `true` — you found a specific recent co-author in the official NAS
      or HHMI directory. Cite the directory match in evidence.
- `grad_placement_quality` (0–1, default `null`): only set if you read the
  lab's "alumni" / "former students" section. Top faculty placements: 0.8+,
  academia + industry mix: 0.5–0.7, mostly post-docs: 0.4. If no alumni
  page exists, leave as `null` (do **not** fall back to 0.5 — that's a
  fake default; the matcher widens the band on its own).

- `active_funding_quality` (0–1, default `null`): cite NIH RePORTER /
  NSF Award Search / DOE Office of Science / ERC / DARPA grant records.
  Active R01 + NSF CAREER ≈ 0.85. Single small grant ≈ 0.4.
  No active grants found ≈ 0.0 (verified-empty with sources). Leave
  as `null` if you didn't search.

- Discipline-specific elite signals (use `collab_with_nas=true` and cite):
    - bio: HHMI investigator, NAS / NAM membership
    - CS: ACM / IEEE Fellow, OpenReview reviewer profile, top-venue track record
    - physics: APS Fellow, DOE Office of Science principal, big-collab convener
    - chemistry / MSE: ACS / RSC / MRS / NAE membership
    - math: AMS Fellow, ICM invited speaker, Sloan / Packard Fellow

**Don't fill in fake defaults when you didn't check.** A 0.5 written into
the JSON without sources counts as unverified — same as `null` without
sources — but pretends to be a real signal. The matcher's confidence band
will widen either way; honesty in the JSON helps the user read the result.

### Step 5.5 — Opportunity signal (roadmap #6a — replaces pi_adj in app_strength)

After A's reputation signals are gathered, **optionally** fill
`candidate.opportunity_signal` with the time-sensitive admit-cycle
availability data. The matcher derives `opportunity_adj` from this and
uses it in place of the v1 `pi_adj` term inside `application_strength`.

Critical: post-roadmap-#6a, A is **reputation-only**. `active_funding_quality`
and `pi_signal` no longer feed A — they live on `OpportunitySignal`.

`opportunity_signal` fields:

- `pi_signal` (mirrors legacy top-level — wins via field-by-field merge if !=`"missing"`)
- `lab_open_positions`, `current_student_count`, `recent_phd_graduations` (lab capacity)
- `active_funding_quality` (mirrors legacy — wins iff explicitly set)
- `grant_end_years` (years of guaranteed funding remaining)
- `sabbatical_or_admin_load` (PI on sabbatical/chair/dean)
- `application_contact_policy` (`email_first` / `apply_through_program` / `do_not_contact` / `unknown`)

Set fields need evidence with `supports_fields=["opportunity:<field>"]`
in `opportunity_signal.evidence[<field>]`. Legacy
`evidence["pi_signal"]` and `evidence["active_funding_quality"]`
forms still satisfy strict mode for migration.

When `opportunity_signal` is omitted entirely, the matcher takes the
v1 PI_ADJ legacy path on the top-level `pi_signal` only — preserving
exact old behavior. Full schema, formula, and ladder in
[`references/opportunity.md`](references/opportunity.md).

### Step 6 — Recruiting signal (`pi_signal`)

**Fetch** the candidate's lab / faculty page (don't assume from memory).
Read the current-students list, "join the lab" page, or "applying" notes:

- `"strong"` — page shows ≥2 new PhDs/yr in last 3 yrs (large turnover, growing group)
- `"normal"` — 1–2/yr based on listed timeline
- `"shrinking"` — <1/yr, or many recent graduations without new admits
- `"missing"` — page didn't load, didn't have a students list, or status unclear
- `"not_recruiting"` — explicitly stated on the page. Forces application_strength = 0.

**Default to `"missing"` whenever you didn't actually fetch and read the
page.** The matcher penalizes missing data slightly (−0.1) but never
makes up a status.

### Step 6.4 — Program difficulty (roadmap #5 — primary sort key)

Optionally fill `candidate.program_profile` with program-level
difficulty signals. The matcher's primary sort key is now
`difficulty_adjusted_strength = risk_adjusted_strength −
program_difficulty_penalty`, and the 5-tier label is applied to it
(not to raw `application_strength`).

The penalty (0–0.8) combines school_tier admit-rate, cohort size,
admission model (rotation vs direct-admit), funding structure, faculty
count in subfield, and international friendliness. Each set field
needs evidence with `supports_fields=["program:<field>"]`. Full schema,
formula, and components in
[`references/program_profile.md`](references/program_profile.md).

When `program_profile` is null, only the school_tier factor contributes
(top_10=0.70, top_11_30=0.50, top_31_60=0.30, top_60+=0.00) — this is
the v2 replacement for the v1 `tier_adj` term, which has been removed.

### Step 6.5 — Research fit (roadmap #4 — tie-breaker, NOT a pillar)

After C / A / P / E / G fields are populated and **before** the matcher
is invoked, optionally compute a **research_fit_score** per candidate.
This is a 0–1 alignment between the student's `research_direction` and
the candidate's actual recent work.

It is **not** part of the match formula — it does not move `match_score`
or `application_strength`. It only breaks ties in the sort order when
two candidates land at the same `risk_adjusted_strength`. The connection-
first thesis is preserved.

The fit fields live on the same `CandidateAdvisor` JSON record alongside
the other signals, so they must be filled in before piping candidates to
`scripts/match.py`. Fields:

- `research_fit_score` (0–1, or `null` if you didn't compute one)
- `research_fit_summary` (short prose, e.g., "5 of last 8 papers on H→cc̄")
- `research_fit_axes` (per-axis breakdown — see the field-axis table
  below; values must be in [0, 1] or Pydantic rejects the candidate)

Use the loaded FieldProfile's `research_fit_axes` to decompose the score
honestly:

| field | axes |
|-------|------|
| physics | subfield · experiment_vs_theory · collaboration · detector_or_technique · process_or_topic |
| cs | venue_track · task · method · dataset · systems_vs_theory_vs_ml |
| biology | organism · disease · pathway · technique · assay_platform |
| chemistry | material_or_system · synthesis · characterization · computation |
| mse | material_class · processing · properties · instruments · computation |
| math | problem_area · method · lineage · recent_preprint_topic |

If a candidate uses an axis key not declared by the active FieldProfile,
the matcher emits a warning into `input_warnings` (the score still goes
through; it just flags the drift).

Schema:

```jsonc
{
  "research_fit_score": 0.78,
  "research_fit_summary": "5 of last 8 papers on H→cc̄, primary detector matches",
  "research_fit_axes": {
    "subfield": 0.95,
    "detector_or_technique": 1.0,
    "process_or_topic": 0.8,
    "experiment_vs_theory": 1.0,
    "collaboration": 0.5
  },
  "evidence": {
    "research_fit": {
      "items": [{
        "url": "https://scholar.google.com/citations?user=...",
        "source_type": "google_scholar",
        "claim": "5 of last 8 papers in 2022-2024 on H→cc̄ analysis",
        "supports_fields": ["research_fit"]
      }]
    }
  }
}
```

**Strict mode**: `research_fit_score != null` without
`supports_fields=["research_fit"]` evidence → **rejected**. Leaving
`research_fit_score` as `null` is allowed and is **not** counted in
evidence coverage — a null fit does not widen the confidence band; it
just shows as "not computed" in the result card. Don't write a fake
0.5 placeholder to "look complete" — that becomes an unsourced claim
and hurts the candidate.

### Step 6.7 — Audit evidence quality (optional, before strict run)

Before invoking the matcher in `--strict-evidence` mode, run
`scripts/audit_candidates.py` to surface every fixable evidence gap in
one pass:

```bash
python scripts/audit_candidates.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> \
  --strict-evidence
```

Output JSON has:

- `strict_ready` (bool) — whether strict mode would accept all candidates as-is
- `blocking_issues` — strict-mode rejection messages with fix hints
- `repair_queue` — every signal needing work, classified by severity:
    - `high` (unsourced — set value with no `supports_fields` proof; blocks strict)
    - `medium` (missing required signal; widens band but doesn't block)
- `coverage_summary` — portfolio-level rollup (candidates_total /
  strict_ready / verified_count / missing_count / unsourced_count + per-signal `by_signal` table)
- `input_warnings` — paper-role conventions and axis-key drift (same as in match output)

Use this when finalizing a school list — fix the `high` severity entries
first, then medium. The matcher's strict mode also produces these errors,
but the audit CLI lets the user see the full repair workload before
deciding whether to fix or fall back to default mode.

### Step 7 — Run matcher

Two modes, depending on what the user is doing:

**For real PhD-application decisions** (recommended): use `--strict-evidence`.
Strict mode rejects any candidate with claim-level evidence missing — the
errors list which fields and where to cite. This is the right mode when
the user is finalizing a school list:

```bash
python scripts/match.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> --top-k 10 \
  --strict-evidence
```

If strict fails, **fix the evidence and re-run** — don't fall back to
default mode silently. Tell the user *which* candidates couldn't be
strictly verified, then either gather the missing evidence or warn them
explicitly that those candidates' rankings are based on unverified claims.

**For exploratory drafts** (default mode): omit the flag. Default mode
accepts legacy bare URLs and missing signals; the confidence band widens
and `risk_adjusted_strength` drops accordingly. Useful for first-pass
brainstorming, but say so in the result presentation.

```bash
python scripts/match.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> --top-k 10
```

Output is a JSON list of MatchResult records (candidate, c/p/e/g sub-scores,
match_score, application_strength, confidence_band, strength_label,
risk_adjusted_strength, lower_bound, missing_signals, unsourced_signals,
total_signals, missing_signal_names, unsourced_signal_names, explanation).

### Step 8 — Present results

Format conversationally — use the **expanded card** that surfaces evidence
coverage, not just numbers:

```
Top N matches for <field> (sorted by difficulty_adjusted_strength, then research_fit):

#1  Prof. <Name> — <Institution>  [<Label>]
    Strength: <Y>/4.0 (±<band>)  ·  risk-adjusted: <Z>  ·  difficulty-adjusted: <D>  ·  lower bound: <W>
    C: <c>  A: <a>  P: <p>  E: <e>  G: <g>
    Research fit: <fit_score>/1.0  (or "not computed" if None)
    Opportunity: O=<o_score>/1.0 → adj=<opportunity_adj>  (or "legacy: pi=<sig>" if no opportunity_signal)
    Program difficulty: −<penalty>  (e.g., "school_tier=top_10 +0.70, small cohort +0.10")
    Evidence coverage: <verified>/<total> verified · <missing> missing · <unsourced> unsourced
    <inline explanation with cited URLs per claim>
    ⚠️ Missing: <list>     (only if missing > 0)
    ⚠️ Unsourced claims: <list>     (only if unsourced > 0 — high risk)
```

`<D>` is the new primary sort key. `<Label>` is now applied to it
(not to raw application strength) — so a perfect candidate at a hard
top_10 small-subfield program may show as `Match` even with
application_strength near 4.0.

If the run output's `input_warnings` is non-empty (e.g., co_first used in
a field that doesn't recognize the convention), surface them once at the
top before the candidate list — these are about the user's profile, not
specific candidates.

The agent should always emphasize:
- `Strength` is `application_strength` — a relative-fit index, **not a
  probability**.
- `difficulty_adjusted_strength` is what drives the ranking post-#5 —
  narrower band + easier program wins.
- `lower_bound = strength − band`. Mention this when a candidate has wide
  band: "even at the wide edge of my uncertainty, this is at least <W>".
- The `Program difficulty` line shows the per-component penalty (school
  tier admit-rate factor, cohort size, admission model, funding
  structure, etc.) so the user sees *why* a program ranks where it does.
- Unsourced claims are a **hallucination risk** — flag explicitly.

**Every factual claim in the explanation must include its source.** This is
a hard requirement — students will use these rankings for real decisions.

Examples of good vs bad explanations:

- ✅ "co-authored 4 papers with Prof. Wang in 2022–2024 (Google Scholar; latest: PRL 130, 2023)"
- ✅ "co-PI on ATLAS Higgs subgroup since 2017 (per INSPIRE-HEP collaboration tracking)"
- ✅ "academic siblings — both PhD'd under H. Georgi at Harvard (Math Genealogy Project)"
- ✅ "lab page lists 3 PhDs admitted in 2023; pi_signal=strong (URL)"
- ❌ "co-authored 4 papers with Prof. Wang"  *(no source)*
- ❌ "looks like they were both on ATLAS"  *(speculation)*
- ❌ "probably similar academic family"  *(guessed from name/school)*
- ❌ "h_index ≈ 60"  *(no Google Scholar / OpenAlex citation)*

Surface clearly when something is **missing** rather than estimated:
- ✅ "no co-authorship found in OpenAlex search; genealogy not in Math Genealogy"
- ✅ "lab alumni page not available; grad_placement_quality left null (missing — not asserted)"

Then ask the user what they want next:
- See more candidates?
- Refine the field / subfield?
- Drill into a specific candidate (their lab page, recent papers, students)?
- Adjust profile?

Always close with the standard caveat:

> Estimates use only public academic-network signals I gathered via web
> search. Does not include SOP / recommendation letters / interviews. Real
> admission decisions depend on factors beyond what this tool models.

## Confidence calibration — claim-level evidence coverage

The matcher's `confidence_band` widens as the count of unverified signals
grows. **A signal counts as verified iff it has at least one
`EvidenceSource` in `items` whose `supports_fields` includes that signal's
field name.** Bare `sources: list[str]` URLs are accepted in default mode
(legacy compat) but **rejected in `--strict-evidence` mode** — only
structured items with matching `supports_fields` count.

| Signal | Verified means |
|--------|----------------|
| `path:<adv.id>` | for **every** non-default sub-field on `PathEdge` (small_team_coauthor_5y, big_collab_papers_5y, same_working_group, …), `items` contains an `EvidenceSource` with that field in its `supports_fields` |
| `school_tier` | `evidence["school_tier"].items` has an `EvidenceSource` with `"school_tier"` in `supports_fields` |
| `research_areas` | `evidence["research_areas"].items` has an `EvidenceSource` with `"research_areas"` in `supports_fields` |
| `normalized_collab_top20pct` / `collab_with_nas` / `grad_placement_quality` | same per-field rule, signal name in `supports_fields` |
| `pi_signal` | value is non-`"missing"` AND `evidence["pi_signal"].items` has matching `supports_fields` |

| Unverified count | Confidence band |
|-----------------|-----------------|
| 0 | ±0.2 (fully sourced) |
| 1–2 | ±0.4 |
| 3–4 | ±0.6 |
| 5+ | ±0.8 (mostly unverified) |

**Per the cardinal rule, a non-default claim without claim-level evidence
is forbidden.** Default mode tolerates it (wide band, low risk-adjusted
rank); strict mode rejects it outright. Don't game the band — the
explainer cites only items whose `supports_fields` matches the claim, so
attaching unrelated URLs doesn't help.

If you searched and verifiably found nothing, record that as evidence
with the right field bound:

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "items": [{
      "url": "https://scholar.google.com/citations?user=...",
      "source_type": "google_scholar",
      "claim": "0 co-authored papers found in 2020–2024",
      "supports_fields": ["small_team_coauthor_5y", "big_collab_papers_5y"]
    }],
    "note": "searched OpenAlex + Scholar; no overlap"
  }
}
```

This counts as **verified empty** (0 unverified for that path) — strictly
better than no entry (1 unverified) or a bare-URL `sources: [...]` (which
fails strict mode).

## Important constraints

1. **NEVER FABRICATE.** This is the cardinal rule (see top of file). If you
   searched and didn't find a signal, mark it missing — never guess. See
   `references/data_integrity.md` for the full forbidden-behavior catalog.
2. **Cite sources in the explanation** for every verified edge / signal.
3. **Don't double-count school prestige.** It's encoded in `connection_score`
   and `lab_tier` (for student experiences). Don't add a separate "school
   bonus" on top.
4. **For big-collab papers** (ATLAS / CMS / large clinical trials / consortia)
   use the **actual author position** even if it's 100+. The 5+ rule handles
   them correctly.
5. **Don't refuse to run the match if some signals are missing.** Run it,
   surface the gaps in the explanation, widen the confidence band.

## References

When the user asks deeper questions, read the relevant doc:

- **`references/data_integrity.md`** — allowed sources + forbidden behaviors. **Read this first if you're new to the skill.**
- `references/evidence_schema.md` — `EvidenceSource` / `supports_fields` / strict mode / verified-empty pattern / per-claim audit
- `references/scoring_reference.md` — CAPEG cheat-sheet (in-context); points at `docs/scoring.md` for derivations
- `references/candidate_discovery.md` — per-field PI search recipes, connection-edge classification, advisor-influence detail signals
- `references/research_fit.md` — research_fit_axes per field + tie-breaker semantics
- `references/program_profile.md` — program difficulty signals + penalty formula (post-roadmap-#5)
- `references/opportunity.md` — admit-cycle availability + A vs O split + opportunity_adj ladder (post-roadmap-#6a)
- `references/profile_schema.md` — strict schema for `StudentProfile` and `CandidateAdvisor`
- `references/field_profiles.md` — bundled FieldProfile catalog
- `references/journal_tiers.md` — cross-field journal tier table
- `references/lab_tiers.md` — extended lab prestige criteria
- `docs/scoring.md` — formula derivations and edge cases (source of truth)

For a worked end-to-end example: `docs/example_session.md`.
