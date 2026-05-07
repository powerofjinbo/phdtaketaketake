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
- ✅ Verified via web search → record + cite the source URL in the explanation
- ✅ Searched but found nothing → leave the field empty / set signal to `"missing"`
- ❌ Guessed from training memory → **NOT ALLOWED**
- ❌ Inferred from name patterns / school proximity / "feels likely" → **NOT ALLOWED**
- ❌ Estimated without any web search → **NOT ALLOWED**

The matcher's confidence band (±0.3 / 0.5 / 0.7) handles missing data
gracefully. A wide band on **real** data is far more useful than a narrow
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
- `papers[]` — `{title, journal, journal_tier, author_position, year}`.
  Without this, P score floors at 3.0. **Paper inclusion convention**: list
  every paper the user expects to have on their CV by the application
  deadline. Don't distinguish between `published` / `accepted` / `submitted`
  / `in prep` — the user has self-selected papers they're confident about,
  trust that listing.
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

### Step 2 — Determine target programs

Ask the user where they want to apply. Acceptable inputs:
- Specific schools (e.g., MIT, Stanford, Princeton)
- A tier ("top 10 physics", "top 30 chemistry")
- Specific professors they have in mind ("I'm interested in Prof. X")
- Open-ended ("show me the best matches")

If they give a tier, use your knowledge of US News PhD program rankings to
enumerate target schools (~10–20). If they give specific schools, use those.

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

Search **at least one** of:

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

**Record sources for every edge** in the edges dict's `sources` list:

```jsonc
"paths_to_advisors": {
  "adv_001": {
    "small_team_coauthor_5y": 3,
    "big_collab_papers_5y": 12,
    "same_working_group": true,
    "sources": [
      "https://scholar.google.com/citations?user=<advisor_id>&...",
      "https://inspirehep.net/authors/<candidate>/...",
      "https://atlas-glance.cern.ch/atlas/analysis/<group>/conveners"
    ],
    "note": "3 small-team co-authored papers (2022-2024); 12 ATLAS bulk papers; both H→cc subgroup conveners 2021-2023"
  }
}
```

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

If no edge found via search: `paths_to_advisors[advisor_id] = {}` is the
correct value. The C score reduces cleanly to field strength only.

### Step 5 — Field-strength signals (per candidate)

Properties of the candidate themselves. Each must be sourced:

- `normalized_collab_top20pct` (0–1): proxy via candidate's h-index from
  Google Scholar or OpenAlex. Formula: `min(1.0, h_index / 50)`. Cite the
  profile URL.
- `collab_with_nas` (bool): set to true **only if** you found a specific
  recent co-author who is a verified NAS / HHMI member (search the official
  NAS / HHMI directories for confirmation). If you didn't verify, leave
  it `false`.
- `grad_placement_quality` (0–1): only set if you found and read the lab
  page's "alumni" / "former students" section. Top faculty placements: 0.8+,
  mix of academia + industry: 0.5–0.7, mostly post-docs: 0.4. **If the lab
  page doesn't have alumni info, set this to 0.5 (neutral default) and
  note "no alumni page" in the explanation — don't fabricate based on
  vibes.**

**No guessing.** If you didn't actually look it up, the conservative
defaults are: `0.5 / false / 0.5`. Note in the explanation that these are
defaults so the user knows the confidence is lower for that candidate.

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

### Step 7 — Run matcher

Build the candidates JSON array, write to a temp file, then:

```bash
python scripts/match.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> --top-k 10
```

Output is a JSON list of MatchResult records (candidate, c/p/e/g sub-scores,
match_score, application_strength, confidence_band, label, explanation).

### Step 8 — Present results

Format conversationally:

```
Top N matches for <field>:

#1  Prof. <Name> — <Institution>  [<Label>]
    Match: <X>/4.0 · Strength: <Y>/4.0 (±<band>)
    C: <c>  P: <p>  E: <e>  G: <g>
    <explanation, with sources cited inline>
```

`Strength` is `application_strength` — a relative-fit index, **not a probability**.
Mention this explicitly in the result presentation if a user asks "what's my chance?"

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
- ✅ "lab alumni page not available; placement signal at 0.5 default"

Then ask the user what they want next:
- See more candidates?
- Refine the field / subfield?
- Drill into a specific candidate (their lab page, recent papers, students)?
- Adjust profile?

Always close with the standard caveat:

> Estimates use only public academic-network signals I gathered via web
> search. Does not include SOP / recommendation letters / interviews. Real
> admission decisions depend on factors beyond what this tool models.

## Confidence calibration

Your `confidence_band` (set indirectly via `missing_signals` count in the
matcher) should reflect how much of the data was verifiable vs. estimated:

| Coverage | Band | When |
|----------|------|------|
| ±0.3 | Tight | All connection edges verified via web search; PI signal confirmed; field-strength signals checked |
| ±0.5 | Moderate | Some edges inferred from indirect evidence; one signal missing |
| ±0.7 | Wide | Most edges guessed; multiple signals missing |

Be honest in the result presentation about what you verified vs. estimated.

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
- `docs/scoring.md` — full formula details, edge cases
- `references/profile_schema.md` — strict schema for StudentProfile and
  CandidateAdvisor (the latter is what you build per candidate)
- `references/journal_tiers.md` — cross-field journal tier table
- `references/lab_tiers.md` — extended lab prestige criteria

For a worked end-to-end example: `docs/example_session.md`.
