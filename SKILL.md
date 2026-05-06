---
name: phdtaketaketake
description: Score a PhD applicant's profile and rank candidate advisors using a connection-first 4.0-scale scoring system. Works for any STEM discipline (HEP, physics, chemistry, biology, materials, CS, math, EE, etc). Use when the user wants to evaluate their PhD application chances, find matching advisors at top US programs, score a CV for graduate school, compare candidate professors, or asks for help with US PhD applications. Also triggers when the user mentions phdtaketaketake or its connection-first philosophy of valuing advisor network over h-index.
---

# phdtaketaketake — Connection-first PhD advisor matcher

This skill ranks candidate PhD advisors for a student by **network-connection
strength** (co-author graph, academic genealogy, joint collaborations) rather
than by h-index or paper count. All four dimensions are scored on a 4.0 scale
(matching GPA):

- **Connection (C)** — paths between candidate ↔ student's current advisor
- **Publication (P)** — journal tier × author position decay (5+ author rule)
- **Experience (E)** — lab × duration × output (output-weighted 50%)
- **GPA (G)** — direct, with multi-system normalization

Final scores are tier-adaptively weighted by school competitiveness, and admit
likelihood incorporates the candidate PI's recruiting signal.

## Field coverage — works for ANY STEM discipline

The deterministic scoring engine is **field-agnostic** — same math runs for any
field. Two paths depending on whether a verified candidate cache is bundled:

| Path | Fields | How |
|------|--------|-----|
| **Bundled cache** | `physics`, `mse` | `scripts/match.py` loads candidates from `data/advisors/`. |
| **Generated candidates** | Any other field (chemistry, biology, CS, math, EE, …) | You (Claude) generate plausible candidate advisors from your training knowledge, pass them via `--candidates-json` / `--candidates-file`. |

**For fields outside the bundled cache**, your job is to construct a JSON array
of `CandidateAdvisor` records using your knowledge of:
- Top US PhD programs in that field (US News rankings, departmental reputation)
- Active PIs whose research direction matches the user's
- Each PI's `school_tier` (top_10 / top_11_30 / top_31_60 / top_60_plus per
  field-specific ranking, not overall university ranking)
- Each PI's `research_areas` (3–5 short tags)
- For **`paths_to_advisors`** — only fill in if you have specific knowledge
  that the user's current advisor has co-authored / shares genealogy / is in
  the same big-collab as the candidate. **Don't invent these edges.**
- `normalized_collab_top20pct`, `collab_with_nas`, `grad_placement_quality` —
  estimate from 0–1 based on what you know about the PI's prominence
- `pi_signal` — `"missing"` unless you specifically know the PI's recent
  recruiting pattern

When generating candidates for an uncovered field, **state in the result
presentation that the candidates were generated from training knowledge, so
confidence is lower than for `physics`/`mse` (which use a cached set)**.

## Workflow

### Step 1 — Gather profile

You need to assemble a profile JSON.

**Required** fields (cannot run match without these — must ask if missing):

- `field` — any STEM discipline as a string (e.g., `"physics"`, `"chemistry"`,
  `"biology"`, `"mse"`, `"cs"`, `"math"`, `"ee"`, `"chemical_engineering"`)
- `undergrad_institution`
- `gpa_raw` + `gpa_scale`
- `research_direction` — short paragraph (≥30 words is best)

**Recommended** fields — **proactively ask for these even if the user didn't
mention them**, because each one materially changes the ranking:

- `current_advisors[]` — `{id, name, institution}`. Without this, the entire
  Connection score collapses to candidate's field strength only — losing the
  core IP of this skill. **Always ask if not provided.**
- `papers[]` — `{title, journal, journal_tier, author_position, year}`.
  Without this, P score floors at 3.0. **Always ask** if the user gave a CV
  but you couldn't extract papers, or if they only described themselves
  in prose.
- `experiences[]` — `{lab_pi_name, lab_tier, duration_months, output_type}`.
  Without this, E score defaults to 2.0. **Always ask.**
- `master_institution` (optional, only if applicable)
- `name` (optional)

### Source priority

1. **CV / resume pasted or attached** → parse it yourself, then **show the
   user the inferred profile and ask them to confirm or correct** before
   running the match. CV parsing always involves judgment calls
   (`journal_tier`, `lab_tier`, exact author position) — never proceed
   silently.

2. **Existing profile JSON** → use directly (skip parsing). Still spot-check
   for missing recommended fields and ask if any are absent.

3. **User describes themselves in prose** → extract what you can, then
   **actively ask for the missing required and recommended fields, one
   focused batch at a time** (don't dump a 10-question list at once).

### How to ask when info is missing

Be brief and structured. Group questions logically. Example:

> Got it — to give you good matches I need a bit more. Three quick things:
>
> 1. Who's your current research advisor? (name + institution)
> 2. Any publications? If yes, list each as: journal name + your author position.
> 3. Any research experience beyond classes? (lab PI + how many months + what output — paper / poster / thesis / talk)

If the user says "no advisor / no papers / no experience", that's a valid
answer — just record it and proceed (the matcher handles missing data with
sensible defaults). **Don't refuse to run the match**; just note in the
result presentation which signals were missing and how that affects the
confidence band.

### When NOT to ask

- The user explicitly says "skip optional fields, just run with what I gave"
- The user has already provided a complete profile JSON
- This is a follow-up turn and you've already asked once — don't keep
  pestering for the same info

If you decided to run the match without asking, **mention in the result
presentation which fields were missing and that filling them would improve
the ranking accuracy**.

### Step 2 — Map fuzzy fields to schema enums

These mappings need careful inference.

**`gpa_scale`** options:
- `"4.0"` — US 4.0 system
- `"4.3"` — some Canadian / Asian universities
- `"4.5"` — some Chinese tech schools (e.g., HUST)
- `"100"` — Chinese percentage (e.g., 88/100)
- `"uk"` — UK honours classifications (`"first"`, `"high_2_1"`, `"low_2_1"`, `"2_2"`, `"third"`)

**`journal_tier`** — the tier scale is universal across STEM, the journals are
field-specific. Always map by the journal's prestige *within its field*. Quick
cross-field anchors (full table in `references/journal_tiers.md`):

| Tier | Score | Anchors |
|------|-------|---------|
| `"S"` | 4.0 | Nature / Science / Cell main |
| `1` | 4.0 | **Field flagship** — PRL (physics), JACS / Angew Chem / Nat Chem (chem), Cell subs / Nature subs / eLife (bio), NeurIPS / ICML / JMLR (CS), Annals of Math / Inventiones / JAMS (math) |
| `2` | 3.7 | Upper specialty — PRX (physics), Chem Sci / ACS Catal (chem), PNAS / Nat Comm (bio), CVPR / ACL (CS) |
| `3` | 3.3 | Mid specialty — PRD/PRA-E (physics), Chem Mater / J Mater Chem (chem), J Cell Bio / Bioinformatics / NAR (bio) |
| `4` | 2.8 | General SCI |
| `5` | 2.3 | Weak / workshop |
| `0` | 0 | Retracted / predatory |

**For a journal you don't recognize**: ask the user, or default conservatively
to tier `4`. **Never guess tier `1`** — that demands strong evidence of
flagship status in the field.

**`lab_tier`** options (universal across STEM):
- `"world_class"` — HHMI / Max Planck / NAS member / Top 10 US PI / national lab (e.g., LBNL, ANL, FNAL, JPL, NIST)
- `"top_us"` — Top 11–40 US PI
- `"strong_us_or_top_cn"` — Top 41–70 US PI / Tsinghua / PKU / Fudan / SJTU / C9 prominent PI
- `"good_us_or_985"` — Top 71–100 US / 985 regular PI
- `"211_or_overseas"` — 211 schools / overseas regular school
- `"other"` — rest

`school_tier` for the candidate PI uses the same 4-bucket scheme but applied
to the **field-specific** US News PhD program ranking, not university overall.

**`output_type`** options:
- `"paper"` — already counted in pub score; assign here when experience produced a paper
- `"conference_oral"` — invited talk / contributed talk
- `"conference_poster"` — poster presentation
- `"honors_thesis"` — undergraduate thesis or research project report
- `"participation_only"` — RA without quantifiable output

**`author_position`** for big-collaboration papers (ATLAS / CMS / large
consortia / multi-institution biology trials): use the **actual position**
(often 100+). The 5+ rule downstream handles this correctly without inversion
at lower-tier journals.

### Step 3 — Run the matcher

Three invocation patterns depending on whether the field is in the bundled
cache:

**(a) Bundled fields (`physics`, `mse`)** — load from cache:

```bash
python scripts/match.py --profile-json '<JSON>' --field physics --top-k 10
```

**(b) Other STEM fields** — generate candidates yourself and pass them:

```bash
python scripts/match.py \
  --profile-json '<PROFILE_JSON>' \
  --field chemistry \
  --candidates-json '<CANDIDATES_JSON_ARRAY>' \
  --top-k 10
```

The candidates JSON is a list of `CandidateAdvisor` records — see
`references/profile_schema.md` for the candidate schema. Generate 10–20
candidates spanning top_10, top_11_30, and top_31_60 schools, all matching
the user's research direction.

**(c) Field outside coverage AND user doesn't want to generate candidates** —
fall back to dimensional self-score:

```bash
python scripts/score_profile.py --profile-json '<JSON>'
```

This returns just P / G / E (no Connection, no ranking) — useful for the user
to see how their profile rates dimensionally even without specific candidates.

For long profiles or candidates JSON, write to a temp file first:

```bash
echo '<JSON>' > /tmp/profile.json
echo '<CANDIDATES_JSON>' > /tmp/cands.json
python scripts/match.py \
  --profile-file /tmp/profile.json \
  --candidates-file /tmp/cands.json \
  --field chemistry --top-k 10
```

Output is JSON to stdout: a list of MatchResult records (candidate, all four
sub-scores, match_score, admit_likelihood, confidence_band, label, explanation).

### Step 4 — Present results

Format conversationally, not as a JSON dump:

```
Top N matches for <field> at top US programs:

#1  Prof. <Name> — <Institution>  [<Label>]
    Match: <X>/4.0 · Admit: <Y>/4.0 (±<band>)
    C: <c>  P: <p>  E: <e>  G: <g>
    <explanation>

#2  …
```

Then ask the user what they want next:
- See more candidates?
- Refine field (focused subdiscipline)?
- Adjust profile (add a paper, fix a tier mapping)?
- Drill into a specific candidate (their `research_areas`, paths)?

End with the standard caveat:

> Estimates use public academic-network signals only. Does not include
> SOP / recommendation letters / interview factors. Real admission outcome
> depends on factors beyond what this tool models.

For uncovered fields, **add a confidence caveat**:

> The candidates above were generated from my general knowledge of <field>,
> not a verified cache. Treat the absolute numbers as rough; the relative
> ranking and per-dimension breakdown are the more reliable signals.

## Important constraints

1. **The bundled advisor cache is mock / synthetic.** It produces plausible
   rankings for demonstration but the named PIs are not real faculty. Always
   disclose this fact in the response. The roadmap is OpenAlex-backed real
   cache (`scripts/build_advisors_cache.py`, currently WIP).

2. **Don't fabricate journal tiers.** If you don't recognize a journal,
   either ask the user or default to tier `4`. Don't guess at tier `1`.

3. **Don't double-count school prestige.** It's already encoded in
   `connection_score` and `lab_tier`. Don't invent a separate "school score"
   bonus on top.

4. **Output positional integers, not ranges.** `author_position: 1` not
   `"first author"`; `author_position: 312` not `"author #300"`.

5. **For uncovered-field candidates you generate**, don't fabricate
   `paths_to_advisors` edges (co-authorship / genealogy / collaboration)
   unless you have specific knowledge. Empty `paths_to_advisors` is fine —
   the Connection score will reduce to field strength, with the caveat
   surfaced in the explanation.

## Useful references

When the user asks deeper questions, read the relevant doc:

- `docs/scoring.md` — full formula details, edge cases, design rationale
- `references/profile_schema.md` — strict schema with examples (incl. CandidateAdvisor)
- `references/journal_tiers.md` — extended journal tier table by field
- `references/lab_tiers.md` — extended lab prestige criteria
