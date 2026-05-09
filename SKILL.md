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

This skill ranks candidate PhD advisors using a **5-layer deterministic
pipeline** — each layer composes the layer below; every score traces
back to cited evidence:

```
1. CAPEG match_score  = w_C·C + w_A·A + w_P·P + w_E·E + w_G·G
                        (tier-adaptive weights; w_C > w_A in every tier
                         — connection-first invariant)
2. application_strength = clip(match_score + opportunity_adj, 0, 4.0)
3. risk_adjusted_strength       = application_strength − band/2
4. difficulty_adjusted_strength = max(0, risk_adjusted_strength − program_penalty)
                                  ← PRIMARY SORT KEY (post-#5)
5. strategy bucket  = bucket(difficulty_adjusted, evidence, …)
                      → priority / target / reach / only_if_space / drop
                      (purely derivative — never modifies any score)
```

5 CAPEG pillars on a 4.0 scale:

- **Connection (C)** — verified path between candidate PI ↔ student's
  current advisor: small-team coauthor, big-collab paper overlap,
  working group, analysis contact, genealogy, shared grant,
  co-mentored student, committee/exam, same center, prior-institution
  overlap, conference session. v2 aggregation: `strongest +
  0.10·second_strongest`, capped at 1.0, scaled by recency.
- **Advisor influence (A)** — PI **reputation only** (post-#6a):
  `0.40·influence + 0.30·elite_status + 0.30·grad_placement_quality`.
  Funding and recruiting moved to **Opportunity (O)**.
- **Publication (P)** — field-aware tier × author-role × status ×
  recency × contribution-bonus, with big-collab and consortium
  guardrails (`min(0.10, n/100)` cap on alphabetical co-authorship).
- **Experience (E)** — `0.20·lab_prestige + 0.30·duration +
  0.50·output`, strongest single experience.
- **GPA (G)** — direct on 4.0; 4.3 / 4.5 / 100 / UK honours normalized.

3 non-CAPEG dimensions:

- **Opportunity (O)** — admit-cycle availability: `recruiting_health
  + active_funding_quality + lab_capacity + grant_timing +
  availability`. Drives `opportunity_adj` (replaces v1 `pi_adj`);
  `not_recruiting` forces `application_strength=0`.
- **Program difficulty (D)** — per-program penalty 0–0.8 from school-
  tier admit rate + cohort size + admission model + funding structure
  + faculty count + international friendliness. Subtracted from
  `risk_adjusted_strength` to form `difficulty_adjusted_strength`
  (the **primary sort key**, replaces v1 `tier_adj`).
- **Research fit (R)** — structured 6-axis tie-breaker: `0.30·topic
  + 0.20·method + 0.15·system + 0.15·temporal + 0.10·grant +
  0.10·background`. Never a 6th pillar; sorts ties only.

Pipeline diagram: [`docs/scoring_pipeline.md`](docs/scoring_pipeline.md).
Full formulas: [`docs/scoring.md`](docs/scoring.md). Per-feature
references in [`references/`](references/).

## How users actually invoke this skill (natural language)

Users on QClaw / Claude Code / any agent platform will not write JSON
themselves. The expected entry shape is conversational:

> "我是 2027 fall 申请 Physics PhD,方向是 ATLAS Higgs / detector ML。
> 本科 UCI,GPA 3.85/4.0,有两篇 ATLAS big-collab paper,导师是 Prof. X。
> 请帮我找美国 top 10–30 的匹配 PI,并按 phdtaketaketake 的 evidence-first
> 规则给出排序和申请策略。"

> *"I'm applying for biology PhDs this fall, focusing on cancer
> immunology. Berkeley undergrad, GPA 3.9, one first-author Cell paper,
> advisor is Prof. Y. Find me 8 advisors at top US programs."*

**Your job as the agent**: translate this into the structured
StudentProfile + candidate-discovery workflow below. Do **not** ask
the user to fill JSON. Do **not** ask for the schema upfront. Ask for
*missing* facts in plain English, one round at a time.

### Required information to ask for (if not given)

If the user's first message is missing any of these, ask before doing
deep research — running the pipeline without them produces low-confidence
output:

1. **Field / subfield** (e.g. "physics / HEP" → resolves to FieldProfile)
2. **Undergrad institution + GPA** (with scale: `4.0` / `4.3` / `4.5` / `100` / UK honours)
3. **Research direction** (1–2 sentences — the matcher uses this for research_fit)
4. **Current advisor(s)** (name + institution — drives the C pillar; **without this, connection-first matching is degraded** and the matcher prints a stderr warning)
5. **Target school tier or list** (top_10 / top_11_30 / top_31_60 / top_60_plus, OR a list of school names)

### Optional but improves output quality

- **Papers**: title, venue, status (`published` / `accepted` / `submitted` / `preprint` / `in_prep`), author position, total authors. Without this, P pillar floors out; user gets an honest "no publication evidence" rather than a guess.
- **Experiences**: lab name, duration months, output (paper / poster / thesis). Without this, E pillar floors.
- **Specific candidate PIs**: if the user already has a target list, skip Step 3 (discovery_plan) and feed candidates straight to `collect_evidence`. If not, run discovery_plan first.
- **Theory / experiment crossover preferences** (physics-specific): affects research_fit.theory_experiment_fit signal.
- **International friendliness needs** (visa / funding constraints): affects program_difficulty interpretation.

### Minimum viable run

The smallest run that produces useful output:

```
field + undergrad + gpa + research_direction + 1 current_advisor
+ target tier (e.g. "top_10")
```

Even with no candidate list, the agent can run `discovery-plan` to
generate per-school search queries, then `collect-evidence` on
agent-discovered candidates, then `match`. Missing optional fields
widen the confidence band but do not crash.

### Two-layer output contract

What the user sees vs what power users / strict-mode auditors get:

- **Per-candidate cards** (rendered by you, the agent) — the human-
  readable presentation. Format defined in §"How to present results
  to the user" below.
- **Full `match.json`** (raw MatchResult JSON) — kept as power-user
  appendix; never the primary user-facing artifact.

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

### Step 2.5 — Generate per-field discovery plan (optional)

Before running the candidate-discovery deep-research step, run
`scripts/build_discovery_plan.py` to get a structured search plan
(per-field query recipes, primary databases, exclusion rules) — keeps
field coverage consistent and prevents "I forgot to search OpenReview
for ML papers" failure modes:

```bash
python scripts/build_discovery_plan.py \
  --field <FIELD> \
  --schools '["MIT", "Stanford", ...]' \
  --keywords "<research direction>"
```

Output JSON includes per-school query recipes (Google Scholar / DBLP
/ INSPIRE / PubMed / NIH RePORTER / Math Genealogy / etc.), the
loaded `FieldProfile.primary_databases`, the field-specific
`ranking_source_url`, the field caveats, and universal exclusion
rules (skip emeriti, no PhD students, no recent papers, etc.). Use
the queries verbatim during the deep-research step.

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

- ≤ field threshold → counts toward `small_team_coauthor_5y` (full strength, max 1.0 at n=5+)
- > field threshold → counts toward `big_collab_papers_5y` (very weak alone, cap 0.10)

**Sprint-2-c1 added more edge types** beyond co-authorship — record
when verified: `shared_grant_count_5y` (NSF/NIH/DOE shared grants),
`co_mentored_student_count` (jointly supervised students),
`committee_or_exam_overlap` (PhD committee / qualifying exam),
`same_center_or_institute`, `prior_institution_overlap_years`,
`conference_session_overlap_5y`. Also set
`most_recent_connection_year` (year of last interaction) — drives the
recency multiplier (0–2y → 1.0, 3–5y → 0.85, 6–10y → 0.60, 10y+ →
0.35, None → 0.75). See
[`references/connection_v2.md`](references/connection_v2.md) for the
full ladder, aggregation formula, and per-edge evidence guidance.

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

Match types (Connection v2 strengths):
- Same PhD advisor (academic siblings) → `"same_advisor"` (0.65)
- Advisor is PhD sibling / nephew of candidate → `"uncle_nephew"` (0.50)
- Two-hop (advisors' advisors crossed paths) → `"two_hop"` (0.40)

**Genealogy is a meaningful historical signal, but weaker than verified
recent working contact.** This is why v2 lowered same_advisor from
v1's 1.0 to 0.65 — a shared PhD advisor decades ago tells you less than
a small-team coauthored paper in the last 5 years (which saturates at
1.0). Don't over-weight lineage in your narrative to the user.

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

The A composite, **reputation-only** post-roadmap-#6a (sums to 1.0):
- 0.40 · influence (h-index proxy)
- 0.30 · elite_status (NAS / HHMI / NAE / field fellow)
- 0.30 · grad_placement_quality

`active_funding_quality` and `pi_signal` (recruiting health) are no
longer A components — they live on `OpportunitySignal` and feed the
**O dimension** (drives `opportunity_adj`, not the match score). See
**Step 5.5** for where to put those fields.

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

- `active_funding_quality` — **fill on `opportunity_signal`, not the top-
  level candidate** (see Step 5.5). The top-level field is kept for
  backward compatibility but is no longer part of A. Field semantics
  (0–1 scale, NIH RePORTER / NSF Award Search / DOE / ERC / DARPA
  citations, R01+CAREER ≈ 0.85, single small grant ≈ 0.4, verified-
  empty 0.0, `null` if not searched) apply to either location.

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

### Step 6.8 — Auto-collect evidence (optional, post-Sprint-3-c1)

Before invoking `audit_candidates.py` and the matcher, run
`scripts/collect_evidence.py` to auto-fill structured evidence (paths,
research_areas, most_recent_connection_year) from external sources:

```bash
# Live OpenAlex enrichment (recommended for real applications):
python scripts/collect_evidence.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> \
  --live --mailto <your-email> \
  --out /tmp/enriched.json

# Then audit + match the enriched JSON:
python scripts/audit_candidates.py \
  --candidates-file /tmp/enriched.json \
  --field <FIELD> --strict-evidence
```

The collector uses OpenAlex (cross-STEM) and emits structured
`EvidenceSource` items with `supports_fields` so strict mode passes.
See [`references/evidence_collection.md`](references/evidence_collection.md)
for the adapter interface, fixture format, and what v1 fills.

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

This is the user-facing rendering layer. The matcher's JSON is the
source of truth; **you (the agent) translate it into per-candidate
cards**. Cards are short, scannable, and product-grade — not debug
dumps. Power users / strict-mode auditors can still inspect the full
`match.json` separately.

#### The per-candidate card format

Render each ranked candidate using exactly this template (markdown
headings, fixed field order):

```
# <rank>. <Name> — <Institution>
Label: <strength_label>     Strategy: <apply_bucket> / <recommended_action>
difficulty_adjusted: <D>    application_strength: <Y> ±<band>

Why ranked here:
- <2–4 bullets, each citing a real source>

Main risks:
- <plain-English missing/unsourced/blocked signals — see Step 8.5>

Next action:
<one sentence drawn from strategy.outreach_angle / evidence_to_fix /
recommended_action — concrete, actionable>
```

**Real example** (using the `physics_hep_audit_demo` output):

```
# 1. Prof. Alex Hartman — MIT
Label: Reach     Strategy: target / contact_first
difficulty_adjusted: 2.20    application_strength: 3.30 ±0.80

Why ranked here:
- Strong connection: 3 small-team coauthored papers with your advisor
  Prof. Wang in 2022–2024 (OpenAlex)
- Research direction overlaps ATLAS Higgs / detector ML — 5 of last 8
  papers on H→cc̄ topics (OpenAlex recent_works)
- Top-10 program difficulty penalty is high (school_tier=top_10 +0.70)

Main risks:
- school_tier is unsourced (used as input, no ranking page citation)
- pi_signal / grad_placement_quality / active_funding_quality are
  missing (lab and alumni pages not searched)
- Confidence band wide (±0.8) — lower_bound is 2.50

Next action:
Email Prof. Hartman. Lead with the shared small-team coauthorship
through Prof. Wang on the H→cc̄ work — that's your strongest verified
edge. Mention you're applying for fall 2027 and ask whether the lab
is actively recruiting; this fills the missing pi_signal.
```

#### Field-by-field rendering rules

- **Title line**: `# <rank>. <Name> — <Institution>` (markdown H1; the rank is the post-#5 sort order).
- **Label / Strategy line**: `<strength_label>` is applied to `difficulty_adjusted_strength` (not raw `application_strength`); `<apply_bucket>` is the strategy enum (`priority` / `target` / `reach` / `only_if_space` / `drop`); `<recommended_action>` is `apply` / `contact_first` / `investigate_evidence` / `deprioritize` / `skip`.
- **Numbers line**: only show `difficulty_adjusted` (the actual sort key) and `application_strength ±band`. Do **not** dump c/a/p/e/g scores in the user-facing card — they go in the JSON appendix.
- **Why ranked here**: 2–4 bullets, each one citing a real source (URL or named page). Pull from the matcher's `explanation` field but rewrite into product language. Skip pillars that are at floor (no evidence to cite).
- **Main risks**: translate `unsourced_signal_names` / `missing_signal_names` / blocked-source attempts into plain English — see §"How to talk about missing signals to the user" for the canonical template. Always mention band width when ±band ≥ 0.6.
- **Next action**: drawn from `strategy.outreach_angle` (when set) or `strategy.evidence_to_fix` (top item). Always concrete — name the person to contact, the page to fetch, the field to fill.

#### What to put in the card vs the appendix

| Always in the card | In the JSON appendix only |
|---|---|
| name, institution, label, strategy bucket | per-pillar c/a/p/e/g scores |
| difficulty_adjusted_strength | risk_adjusted_strength, lower_bound |
| application_strength ±band | confidence_band exact value |
| 2–4 cited reasons (Why) | full `explanation` string |
| plain-English risks (Main risks) | namespaced `missing_signal_names`, `unsourced_signal_names` |
| one Next action | full `evidence_to_fix` queue |
| field caveats relevant to user's discipline | `field_profile_id`, raw FieldProfile YAML |

Power users invoke `phdtaketaketake-match` directly and read the JSON.
QClaw / Claude Code users see only the cards.

#### Top-of-output portfolio summary

Before the per-candidate cards, surface the portfolio rollup in **one short
paragraph** (drawn from `strategy_summary.portfolio_notes`):

```
N candidates analyzed: <p> priority · <t> target · <r> reach ·
<o> only_if_space · <d> drop. <one-sentence verdict on portfolio shape —
e.g., "no priority bucket fills yet — main blocker is missing pi_signal
across the board".>
```

If the run output's `input_warnings` is non-empty (co_first used in a
field that doesn't recognize the convention, profile-level data
issues), surface them right after the portfolio paragraph, before the
first candidate card.

#### Mandatory product-boundary footer

Every results render — even a one-candidate quick check — must end with this exact disclaimer (zh + en, since the audience spans both):

> **This is a 4.0-scale relative application-strength index, not an
> admission probability. Missing or blocked sources widen the
> confidence band instead of being guessed.**
>
> 这是一个 4.0 制的相对申请强度指数,不是录取概率。证据无法验证或来源被拦截
> 时,confidence band 会变宽,而不是被猜测填充。

Do **not** drop this footer to save tokens. It is the product's most
important boundary statement — it stops users from misreading
`Target / Reach / Match` as actual admit probabilities, and it
explains why some candidates have wide bands.

#### Per-claim source requirement (still hard)

**Every factual claim in the "Why ranked here" bullets must include its source.** This requirement is unchanged from prior versions — the card structure is just a wrapper around evidence-cited prose.

Examples of good vs bad bullet phrasing:

- ✅ "co-authored 4 papers with Prof. Wang in 2022–2024 (OpenAlex; latest: PRL 130, 2023)"
- ✅ "co-PI on ATLAS Higgs subgroup since 2017 (INSPIRE-HEP collaboration tracking)"
- ✅ "academic siblings — both PhD'd under H. Georgi at Harvard (Math Genealogy Project)"
- ✅ "lab page lists 3 PhDs admitted in 2023; pi_signal=strong (URL)"
- ❌ "co-authored 4 papers with Prof. Wang"  *(no source)*
- ❌ "looks like they were both on ATLAS"  *(speculation)*
- ❌ "probably similar academic family"  *(guessed from name/school)*
- ❌ "h_index ≈ 60"  *(no Google Scholar / OpenAlex citation)*

Same for Main risks — be specific about *which* signal is missing and *why*:

- ✅ "no co-authorship found in OpenAlex search; genealogy not in Math Genealogy"
- ✅ "lab alumni page not available; grad_placement_quality left null (missing — not asserted)"
- ❌ "evidence is a bit thin"  *(vague)*

#### Closing follow-up

After the cards + footer, ask the user what they want next:

- See more candidates?
- Refine the field / subfield?
- Drill into a specific candidate (their lab page, recent papers, students)?
- Adjust profile (add a paper, correct GPA scale, swap target tier)?
- Re-run with `--strict-evidence` after fixing the unsourced claims?

### Step 8.5 — How to talk about missing signals to the user

The matcher reports missing / unsourced / verified-empty signals as
namespaced JSON field names (`path:adv_001`, `program:cohort_size_estimate`,
`pi_signal`, etc.). **Do not show those raw field names to QClaw / Claude
Code users.** Translate them into plain English using the template below.

#### The four states (canonical)

| Internal state | What happened | What to tell the user |
|---|---|---|
| **Verified** | searched, found a value, cited URL | (don't surface — implicit when bullet has source) |
| **Verified-empty** | searched, page said "no result" | "I confirmed via <source> that there's no <signal> for this PI" — counts as evidence, narrows the band |
| **Missing** | didn't search this signal | "I haven't checked <source> for <signal> yet — you can ask me to fill it in" |
| **Blocked** (subset of missing) | tried, source unreachable (403 / CAPTCHA / paywall / timeout / login wall) | "I tried to verify <signal> but <source> blocked the request — counts as missing; you can paste the page text or a screenshot" |

The blocked state is **not** a system failure; it's expected — Google
Scholar throws CAPTCHAs, US News has a paywall, some school CDNs
(Cloudflare) refuse fetches. The skill is designed to handle this:
blocked sources widen the confidence band rather than getting filled
with guesses. See [`references/data_integrity.md`](references/data_integrity.md)
§"Blocked / timeout / CAPTCHA is not verified-empty" for the policy.

#### The Main risks template (canonical wording)

When rendering "Main risks:" in a per-candidate card (Step 8), use this
shape — translating namespaced signals to plain English, grouping by
state, and offering the recovery path:

```
Main risks:
- I couldn't verify the following signals — they're counted as missing
  and widen the confidence band:
  • school_tier — ranking page (US News graduate program ranking) was
    blocked by a login wall
  • pi_signal — lab page would not load (Cloudflare challenge / 403)
  • grad_placement_quality — no alumni / "former students" page found
- This is not a negative conclusion; the matcher just has less to go on.
  You can manually paste lab page text, an alumni list, or a screenshot
  of the ranking page and I'll re-run with that as evidence.
```

#### Specific signal → plain-English mapping

| Namespaced signal | Plain English |
|---|---|
| `path:<adv_id>` | "verified path between this PI and your advisor <name>" |
| `school_tier` | "school's program ranking" |
| `pi_signal` | "whether the PI is actively recruiting (lab page check)" |
| `grad_placement_quality` | "alumni placement track record" |
| `active_funding_quality` | "PI's active grants (NIH RePORTER / NSF Award Search)" |
| `collab_with_nas` | "NAS / HHMI co-author" |
| `normalized_collab_top20pct` | "PI's h-index / collaboration percentile" |
| `program:cohort_size_estimate` | "incoming cohort size" |
| `program:admission_model` | "rotation vs direct-admit" |
| `program:funding_structure` | "funding model (guaranteed vs on-paper)" |
| `program:faculty_count_in_area` | "number of faculty in your subfield" |
| `program:international_friendliness` | "international-student friendliness" |
| `research_fit` | "research-direction overlap" |
| `opportunity:lab_open_positions` | "open PhD slots this cycle" |
| `opportunity:application_contact_policy` | "preferred contact channel (email / through program / do-not-contact)" |

#### Three things to never say

- ❌ "Error 403 on lab.stanford.edu" *(raw HTTP error — not user-facing)*
- ❌ "evidence is a bit thin" *(vague; the user can't act on it)*
- ❌ "h_index unavailable, defaulting to 0.5" *(invented default — never; the matcher does not do this)*

#### Three things to always say when surfacing blocked sources

- ✅ name the *signal* in plain English (not the namespaced field)
- ✅ name the *source* that was blocked (so the user knows what to manually provide)
- ✅ name the *recovery* — paste page text, paste a screenshot, give a URL the agent can fetch

This is the canonical user-facing language. Use it consistently across
cards, portfolio rollup, and follow-up questions.

## CV optimization (parallel workflow — Sprint-7)

Beyond advisor matching, the skill ships a **LaTeX CV template + compile pipeline** so the same conversation can produce a polished PhD-application CV. This is a *parallel workflow* to advisor matching — they share the same install but trigger independently.

### When to invoke this workflow

Trigger on any of:

- "帮我做 / 整理 / 优化 / 改进 我的 CV / 简历"
- *"make / improve / format my CV"*
- *"tailor my CV for `<target PI>` / `<target program>`"*
- *"我有一份 match.json,帮我针对前 3 个 PI 做 tailored CV"*
- The user pastes a CV (LaTeX or otherwise) and asks for review / optimization

**Two trigger paths:**

1. **Generic CV** — user wants a clean PhD-application CV, no specific target. Run the template-fill flow; skip tailoring.
2. **Tailored CV** — user provides a `match.json` (or asks to tailor against earlier matching output). Fill the template, then reorder + prune for top-bucket candidates.

If the user invokes "make my CV" without naming a target, **ask once**:

> *Do you have target advisors / programs in mind? If you've already run advisor matching, paste the `match.json` and I can tailor the CV for the top candidates. Otherwise I'll produce a general PhD-app version.*

Don't re-ask. If they say no or skip, proceed with generic.

### Step CV-1 — Read the bundled template

```bash
phdtaketaketake-cv-template --print > cv.tex
# or, just print the path so you can Read / Edit it directly:
phdtaketaketake-cv-template
# /…/phd_matcher/cv/templates/default.tex
```

Read it carefully before editing. Note the contract:

- **Preamble + custom commands** (`\resumeSubheading`, `\resumeItem`, `\resumeItemWithoutTitle`, `\resumeItemListStart/End`, `\resumeSubHeadingListStart/End`) — never edit. The `% DO NOT EDIT` comment marks the boundary.
- **All sections present by default**: Education / Research Experience / Publications & Presentations / Technical Skills / Teaching Experience / Leadership Experience / Honors and Awards. Delete any that don't apply (whole `\section{...}` block + its wrapper). **Empty section headers look worse than missing sections.**
- **`OPTIONAL_BLOCK_START / END` markers** wrap content that's off by default — currently the Relevant Coursework table (under Education) and the multi-affiliation extra-emails block (under Header). Enable by removing the `% ` prefix on each line between the markers.
- **`<angle-bracket>` placeholders** mark every fill-in slot. The as-shipped file compiles to a "demo CV" with placeholders rendered as text — useful to verify your LaTeX install works before personalizing.

### Step CV-2 — Gather user info

Ask in plain English, **section by section, not all at once**. Don't dump the template into the chat — that overwhelms the user. Probe like a CV consultant:

1. **Header**: full name, primary email, secondary emails (multi-affiliated users only), personal website (optional).
2. **Education**: institution(s), degree, GPA + scale, location, dates. Ask: *"Do you want a Relevant Coursework table? It helps for physics / theory CS / applied math; less common for experimental bio / chem."*
3. **Research experience**: per project — title, mentor, institution, dates, 2–4 bullets describing **what you built / proved / measured** + **methods + tools** + **outcome / contribution**. Probe for verbs: avoid "responsible for", prefer "implemented", "demonstrated", "produced", "developed".
4. **Publications**: split into Selected Papers (published / accepted), Work in Progress (drafted / in prep), Posters & Talks. If a sub-category is empty → delete it (don't leave empty headers).
5. **Technical skills**: 2–3 named categories (Programming / Field Software / Languages). Comma-separated lists.
6. **Teaching / Leadership / Honors**: ask if relevant; delete the section entirely if not.

The user may not give everything in one round. That's expected. Fill what you have, leave clearly-marked TODO comments in the `.tex` for empty fields, ask follow-ups for the most important gaps first (Research Experience > Publications > Skills > others).

### Step CV-3 — Fill the template

Use `Edit` / `Write` to produce a populated `cv.tex`. Replace every `<placeholder>`. **LaTeX special-character escaping is required** for user-typed text:

| User text | LaTeX form |
|---|---|
| `&` (ampersand, e.g. "R\&D") | `\&` |
| `%` (percent, e.g. "5\% improvement") | `\%` |
| `_` (underscore, e.g. file names) | `\_` |
| `#` (hash, e.g. "channel \#1") | `\#` |
| `$` (dollar, e.g. "\$8110 award") | `\$` |
| `{` `}` | `\{` `\}` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |
| `\` | `\textbackslash{}` |

URLs inside `\href{}` and `\url{}` already escape correctly — no manual work needed there.

If the user wants the **Relevant Coursework table**: between `OPTIONAL_BLOCK_START: Relevant Coursework` and `OPTIONAL_BLOCK_END: Relevant Coursework`, remove the leading `% ` from every line, then fill the courses. Keep the START / END marker comments themselves so the structure is recoverable.

If a section **doesn't apply** to the user (no Teaching, no Leadership), delete the entire `\section{...}` block including its `\resumeSubHeadingListStart / End` wrapper.

### Step CV-4 — (Optional) Tailor for target PI(s)

Only when the user provided a `match.json` or asked for tailoring against earlier matching output. The full per-section playbook is in [`references/cv_optimization.md`](references/cv_optimization.md) §"Tailoring playbook". Quick summary:

- **Research Experience order** — read top-bucket candidates' `research_areas`. For each user experience, judge overlap. Strong-overlap projects move to the top; weak/none + > 2 years old → consider deleting (ask the user first).
- **Bullets within an experience** — lead with the bullet whose methods / detector / dataset overlap target PI's recent papers.
- **Publications** — same. Lead with paper most overlapping target's subject.
- **Technical skills** — re-order each comma-separated list to put target-lab tools first (e.g. for a Geant4-heavy LDMX-style group, put `Geant4` before `MadGraph5`).

**Tailoring is reordering and pruning, never invention.** Never add an experience, paper, or skill the user didn't actually do.

### Step CV-5 — Compile to PDF

```bash
phdtaketaketake-cv-compile cv.tex
# → cv.pdf in the same directory
```

The compile CLI prefers `latexmk -pdf` (handles cross-reference multi-pass internally); falls back to `pdflatex` running up to 3 passes. Three exit modes:

| Exit code | Status | What to do |
|---|---|---|
| 0 | ok | PDF produced. Show the user the path. |
| 1 | failed (TeX install OK; .tex has an error) | The CLI prints diagnostic lines (`! LaTeX Error:`, `l.<num>`, "Undefined control sequence", etc.) extracted from the `.log`. Most common cause: an unescaped LaTeX special char in user text — re-check the `\&` / `\%` / `\_` / `\#` / `\$` escapes in Step CV-3 and re-run. |
| 2 | tex_not_installed | The CLI prints install hints for macOS / Debian / Fedora / Windows + a note that minimal TeX installs (BasicTeX, TinyTeX) may need `tlmgr install titlesec enumitem`. Always offer Overleaf as the universal fallback — paste the `.tex`, compile in-browser. |
| 3 | input error | File not found, etc. Verify the path. |

**On persistent compile failure, do not try to "fix" the LaTeX by guessing.** Surface the diagnostic to the user, ask them to paste the offending source line back so you can escape it correctly, or hand them the raw `cv.tex` + Overleaf link.

### Step CV-6 — Hand off to the user

Show:

- The `.pdf` path (or, on compile failure, the `.tex` content + Overleaf link)
- A 2–3 sentence summary of any tailoring decisions you made (the user needs to review and may push back on order / deletions)
- A short review checklist:
  - GPA scale matches your records (3.85/4.0 vs 88/100)
  - Paper venues + author orders are current
  - Dates consistent (no overlap that doesn't make sense)
  - Email addresses spelled correctly

Standard product-boundary disclaimer (zh + en, same as advisor matching):

> **This is a CV format + reorder helper, not a content-quality / SoP / recommendation-letter assistant. The substance of your experiences and the strategic narrative of your application are your responsibility.**
>
> 这是一个 CV 排版与重排工具,不是内容质量评估、SoP 撰写或推荐信辅助工具。你研究经历的实质内容和申请的战略叙事是你自己负责的部分。

### What the CV sub-skill does NOT do

- ❌ Does not write or revise SoPs / personal statements / cover letters
- ❌ Does not invent experiences, skills, papers, or awards
- ❌ Does not contact PIs on the user's behalf
- ❌ Does not optimize for industry / ATS resumes (the template is academic-PhD-application style)
- ❌ Does not assess content quality (good experiment vs bad experiment is the user's judgment)

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
- `references/connection_v2.md` — expanded network model: shared grants / co-mentored students / committee-or-exam / same center / prior-institution overlap / conference sessions + recency multiplier (post-Sprint-2-c1)
- `references/publication_v2.md` — recency decay + contribution_role bonus + big-collab guardrail + consortium guardrail + field-aware status weights (post-Sprint-2-c2)
- `references/research_fit_v2.md` — structured `ResearchFit` submodel + 6-axis weighted formula (topic / method / system / temporal / grant / background); `theory_experiment_fit` stored only (post-Sprint-2-c3)
- `references/strategy.md` — apply-bucket precedence (drop / only_if_space / reach / target / priority), recommended-action ladder, outreach-angle rules, portfolio summary (post-Sprint-2-c5)
- `references/evidence_collection.md` — source adapter interface, OpenAlex fixture/live modes, `scripts/collect_evidence.py` enriching candidate JSONs with paths_to_advisors / research_areas / most_recent_connection_year (post-Sprint-3-c1)
- `references/profile_schema.md` — strict schema for `StudentProfile` and `CandidateAdvisor`
- `references/field_profiles.md` — bundled FieldProfile catalog
- `references/journal_tiers.md` — cross-field journal tier table
- `references/lab_tiers.md` — extended lab prestige criteria
- `docs/scoring.md` — formula derivations and edge cases (source of truth)

For a worked end-to-end example: `docs/example_session.md`.
