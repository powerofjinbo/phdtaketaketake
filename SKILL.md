---
name: phdtaketaketake
description: Score a PhD applicant's profile and rank candidate advisors using a connection-first 4.0-scale scoring system. Works for any STEM discipline — physics, chemistry, biology, materials, CS, math, EE, ChemE, earth science, etc. Use when the user wants to evaluate their PhD application chances, find matching advisors at top US programs, score a CV for graduate school, or compare candidate professors. Also triggers when the user mentions phdtaketaketake or its connection-first philosophy of valuing advisor network over h-index.
---

# phdtaketaketake — Connection-first PhD advisor matcher

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
  combination, tier-adaptive weights, admit likelihood with confidence band).

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
  Without this, P score floors at 3.0.
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

For **each** candidate, dig for connection signals to the user's
`current_advisors`. This is what differentiates this skill from h-index
ranking — the depth of your research here drives result quality.

**Direct co-authorship** (strongest signal):

```
Web search: "<student advisor full name>" "<candidate full name>"
            site:scholar.google.com
            
Or: site:openalex.org / site:pubmed.ncbi.nlm.nih.gov / site:inspirehep.net
            (whichever is dominant for the field)
```

Count distinct papers in last 5 years where both names appear as authors:
→ `coauthor_papers_5y` (integer)

**Joint big-collaboration** (e.g., ATLAS, CMS, BICEP, LIGO, multi-institution
clinical trials, large genome consortia):

If both are members of a named experiment / consortium, estimate years of
overlap. Search "<candidate name> ATLAS" / "<advisor> CMS" etc.
→ `collaboration_overlap_years` (float, years)

**Academic genealogy** (PhD lineage shared):

```
Math Genealogy Project: https://www.genealogy.math.ndsu.nodak.edu/
   (best for physics, math, some bio)
   
Or web search: "<advisor name>" "PhD advisor" / "thesis advisor"
              "<candidate name>" "PhD advisor" / "thesis advisor"
```

Match:
- Same PhD advisor (academic siblings) → `"same_advisor"` (1.0 strength)
- Advisor is PhD sibling / nephew of candidate → `"uncle_nephew"` (0.7)
- Two-hop (advisor's advisor and candidate's advisor crossed paths) → `"two_hop"` (0.4)

**Editorial / committee co-membership** (weaker signal):

Search for shared NSF panels, conference PCs, editorial boards. Lower
strength but still counts.

→ `committee_co_member: true`, `same_period: true/false`

**Take the MAX of these edges, do NOT sum** — the matcher treats them as
mutually exclusive (avoids double-counting). Set whatever edge you found
strongest.

If none found: `paths_to_advisors[advisor_id] = {}` is fine — the C score
reduces cleanly to field strength only, and the matcher handles this.

**Critical rule: never fabricate edges.** If your search came up empty,
leave the field empty. Better a missing edge than a hallucinated one.

### Step 5 — Field-strength signals (per candidate)

These are properties of the candidate themselves, not their connection to
the student's advisor:

- `normalized_collab_top20pct` (0–1): candidate's prominence in their field.
  Quick proxy: `min(1.0, h_index / 50)`. Look up h-index via Google Scholar
  / OpenAlex profile.
- `collab_with_nas` (bool): has the candidate co-authored with an NAS / HHMI
  member in the last 5 years? Quick check: search their recent papers, look
  for known NAS members in the author list.
- `grad_placement_quality` (0–1): rough — top faculty placements: 0.8+, mix
  of academia + industry: 0.5–0.7, mostly post-docs: 0.4. Check their lab
  page's "alumni" / "former students" section.

If you don't have time to dig: 0.5 / false / 0.5 as conservatives. Note
this in the candidate's explanation.

### Step 6 — Recruiting signal (`pi_signal`)

Visit the candidate's lab / faculty page. Check current students and recent
admits:

- `"strong"` — ≥2 new PhDs/yr in last 3 yrs (large turnover, growing group)
- `"normal"` — 1–2/yr
- `"shrinking"` — <1/yr, or many recent graduations without new admits
- `"missing"` — couldn't find data (default; don't guess)
- `"not_recruiting"` — explicitly stated. Forces admit_likelihood = 0.

### Step 7 — Run matcher

Build the candidates JSON array, write to a temp file, then:

```bash
python scripts/match.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field <FIELD> --top-k 10
```

Output is a JSON list of MatchResult records (candidate, c/p/e/g sub-scores,
match_score, admit_likelihood, confidence_band, label, explanation).

### Step 8 — Present results

Format conversationally:

```
Top N matches for <field>:

#1  Prof. <Name> — <Institution>  [<Label>]
    Match: <X>/4.0 · Admit: <Y>/4.0 (±<band>)
    C: <c>  P: <p>  E: <e>  G: <g>
    <explanation, citing sources>
```

In the explanation, **cite where you found each connection edge**:
- ✅ "co-authored 4 papers with Prof. Wang in 2022–2024 (per Google Scholar)"
- ❌ "co-authored 4 papers with Prof. Wang"

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

1. **Never fabricate connection edges.** If you searched and found nothing,
   leave the path empty. Empty `paths_to_advisors[id] = {}` is fine.
2. **Cite sources in the explanation** for any verified edge.
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

- `docs/scoring.md` — full formula details, edge cases
- `references/profile_schema.md` — strict schema for StudentProfile and
  CandidateAdvisor (the latter is what you build per candidate)
- `references/journal_tiers.md` — cross-field journal tier table
- `references/lab_tiers.md` — extended lab prestige criteria

For a worked end-to-end example: `docs/example_session.md`.
