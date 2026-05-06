---
name: phdtaketaketake
description: Score a PhD applicant's profile and rank candidate advisors using a connection-first 4.0-scale scoring system. Use when the user wants to evaluate their PhD application chances, find matching advisors at top US programs, score a CV for graduate school, compare candidate professors, or asks for help with US PhD applications in physics / HEP or materials science (MSE). Also triggers when the user mentions phdtaketaketake or its connection-first philosophy of valuing advisor network connections over h-index.
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

Current coverage: HEP / Physics + Materials Science & Engineering (MSE).

## Workflow

### Step 1 — Gather profile

You need to assemble a profile JSON.

**Required** fields (cannot run match without these — must ask if missing):

- `field` — `"physics"` or `"mse"`
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

These mappings need careful inference:

**`gpa_scale`** options:
- `"4.0"` — US 4.0 system
- `"4.3"` — some Canadian / Asian universities
- `"4.5"` — some Chinese tech schools (e.g., HUST)
- `"100"` — Chinese percentage (e.g., 88/100)
- `"uk"` — UK honours classifications (`"first"`, `"high_2_1"`, `"low_2_1"`, `"2_2"`, `"third"`)

**`journal_tier`** quick reference (full table in `references/journal_tiers.md`):

| Tier | Score | Examples |
|------|-------|----------|
| `"S"` | 4.0 | Nature, Science, Cell main |
| `1` | 4.0 | PRL, Nature Physics, JACS, Nature Materials, Adv Materials, Nano Lett |
| `2` | 3.7 | PRX, JHEP, ApJL, Adv Funct Mater, ACS Nano, Materials Today |
| `3` | 3.3 | PRD, PRA-E, Chem Mater, J Mater Chem A/B/C, Nanoscale |
| `4` | 2.8 | PR Applied, J Appl Phys, J Mater Sci, Materials Letters |
| `5` | 2.3 | weaker SCI / workshops |
| `0` | 0 | retracted / predatory |

When uncertain about a journal, default to tier `4` (conservative).

**`lab_tier`** options:
- `"world_class"` — HHMI / Max Planck / NAS member / Top 10 US PI / national lab
- `"top_us"` — Top 11–40 US PI
- `"strong_us_or_top_cn"` — Top 41–70 US PI / Tsinghua / PKU / Fudan / SJTU / C9 prominent PI
- `"good_us_or_985"` — Top 71–100 US / 985 regular PI
- `"211_or_overseas"` — 211 schools / overseas regular school
- `"other"` — rest

**`output_type`** options:
- `"paper"` — already counted in pub score; assign here when experience produced a paper
- `"conference_oral"` — invited talk / contributed talk
- `"conference_poster"` — poster presentation
- `"honors_thesis"` — undergraduate thesis or research project report
- `"participation_only"` — RA without quantifiable output

**`author_position`** for big-collaboration papers (ATLAS / CMS / large consortia):
use the **actual position** (often 100+). The 5+ rule downstream handles this
correctly without inversion at lower-tier journals.

### Step 3 — Run the matcher

The repo's `scripts/match.py` is the entry point. Three invocation styles
(any of them works):

```bash
# Style A — pass JSON inline (escape carefully)
python scripts/match.py --profile-json '<JSON>' --field physics --top-k 10

# Style B — write profile to a temp file first (cleaner for big profiles)
echo '<JSON>' > /tmp/profile.json
python scripts/match.py --profile-file /tmp/profile.json --field physics --top-k 10

# Style C — pipe via stdin
echo '<JSON>' | python scripts/match.py --field physics --top-k 10
```

Output is JSON to stdout: a list of MatchResult records (candidate, all four
sub-scores, match_score, admit_likelihood, confidence_band, label, explanation).

You typically want `--top-k 10` for an initial overview.

### Step 4 — Present results

Format conversationally, not as a JSON dump. Suggested template:

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
- Try a different field (physics / mse)?
- Adjust profile (add a paper, fix a tier mapping)?
- Drill into a specific candidate (read their `research_areas`, `paths_to_advisors`)?

End with the standard caveat:

> Estimates use public academic-network signals only. Does not include
> SOP / recommendation letters / interview factors. Real admission outcome
> depends on factors beyond what this tool models.

## When to skip the matcher

- **Field outside coverage** (anything not physics or mse): tell the user the
  current coverage. Optionally: still score their profile dimensionally
  (`scripts/score_profile.py` if you only want the four sub-scores without
  ranking against advisors). Or offer to extend `data/journals/<field>.yaml`
  and `data/advisors/mock_advisors.json` for that field — community PRs
  welcome.
- **Profile too thin to score meaningfully**: if user has no GPA, no papers,
  no advisor, no clear direction — ask for at least field + GPA + research
  direction before running.

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

## Useful references

When the user asks deeper questions, read the relevant doc:

- `docs/scoring.md` — full formula details, edge cases, design rationale
- `references/profile_schema.md` — strict schema with examples
- `references/journal_tiers.md` — extended journal tier table
