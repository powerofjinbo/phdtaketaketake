# Data integrity — non-negotiable

This skill ranks PhD admissions. **Students will use these results to decide
where they spend years of their life.** Fabricated data isn't just wrong —
it's harmful. Read this whole page before doing any connection research.

## The contract

| Behavior | Treatment |
|----------|-----------|
| Verified via web search, source cited | ✅ allowed |
| Searched, returned nothing → field empty / "missing" | ✅ allowed |
| Guessed from training memory | ❌ **forbidden** |
| Inferred from name pattern / school proximity | ❌ **forbidden** |
| Estimated without web search | ❌ **forbidden** |
| Source citation omitted from explanation | ❌ **forbidden** |

The matcher's confidence band (±0.3 / 0.5 / 0.7) widens automatically when
signals are missing — that's the **correct behavior**. A wide band on real
data is far more useful than a narrow band on fabricated data.

## Allowed data sources

Only use these. If you can't verify a claim against one of these sources
(or a similarly authoritative academic source for niche fields), the claim
must be marked missing.

### Bibliographic / co-authorship

| Source | URL | Best for |
|--------|-----|----------|
| Google Scholar | <https://scholar.google.com> | author profiles, h-index, paper search |
| OpenAlex | <https://openalex.org> · API: <https://api.openalex.org> | open scholarly graph, free programmatic queries |
| INSPIRE-HEP | <https://inspirehep.net> | physics literature (gold standard for HEP) |
| PubMed | <https://pubmed.ncbi.nlm.nih.gov> | biology / medicine |
| Europe PMC | <https://europepmc.org> | biology / medicine (broader than PubMed) |
| Semantic Scholar | <https://www.semanticscholar.org> | CS-leaning broad coverage |
| arXiv | <https://arxiv.org> | preprints (cs, physics, math, stat, econ, q-bio) |
| Web of Science | <https://www.webofscience.com> | requires institutional access; cite if available |

### Academic genealogy

| Source | URL | Best for |
|--------|-----|----------|
| Mathematics Genealogy Project | <https://www.genealogy.math.ndsu.nodak.edu/> | math, physics, some chem / bio |
| AI Genealogy Project | <https://aigenealogy.org> | AI / CS lineage |
| Faculty bios on lab / department pages | (per lab) | often state "PhD under Prof. X, year" |
| Memorial / retrospective articles | (varies) | acceptable as secondary source |

### Recruiting signal / lab status

| Source | Use |
|--------|-----|
| Candidate's lab / faculty page | current-students list, "applying" notes, recent admit timeline |
| Department graduate program page | recent admits info |
| LinkedIn profile of current students | join date validates pi_signal |

### School ranking

| Source | URL |
|--------|-----|
| US News Best Graduate Schools | <https://www.usnews.com/best-graduate-schools> |
| QS World University Rankings | <https://www.topuniversities.com/university-rankings> |
| Field-specific surveys (CSrankings.org, etc.) | (varies) |

### NAS / HHMI verification

| Source | URL |
|--------|-----|
| NAS member directory | <https://www.nasonline.org/member-directory> |
| HHMI investigator list | <https://www.hhmi.org/scientists> |
| Official lab page bio (often lists "Member, NAS, year") | (per lab) |

## Forbidden behaviors (with examples)

### ❌ Don't guess from name similarity

> Bad: "Wang and Li both have Chinese names so probably similar academic family"

Names are not academic genealogy. Search Math Genealogy Project — if it
returns nothing, leave genealogy edge empty.

### ❌ Don't fabricate co-author counts

> Bad: "they probably co-authored a few papers"
> Bad: "given they're both at top schools in HEP, ~3–5 co-authored papers"

Fetch Google Scholar / OpenAlex / INSPIRE-HEP and **count actual results**.
If the search returns 0, `coauthor_papers_5y` stays absent — `paths_to_advisors[adv_id] = {}`.

### ❌ Don't invent collaboration memberships

> Bad: "she works on Higgs physics so probably ATLAS"

Verify via INSPIRE-HEP collaboration tracking, the candidate's CV, or a
direct mention on the lab page. People work on Higgs from theory, on CMS,
on Belle II, etc.

### ❌ Don't infer genealogy from training memory alone

> Bad: "I recall Klute did his PhD with Bertl"

Even if your training data says this, **verify against Math Genealogy or
a faculty bio** before recording the edge. Training data can be stale or
wrong for specific facts. Cite the verifying source.

### ❌ Don't hallucinate lab page content

> Bad: "lab page suggests strong recruiting"  *(without actually fetching it)*

Either fetch the page and quote what you saw, or set `pi_signal = "missing"`.

### ❌ Don't fill field-strength signals from vibes

> Bad: "famous PI so normalized_collab_top20pct = 0.9"
> Bad: "Stanford prof, NAS member"  *(without checking NAS directory)*

Get the h-index from a real source and apply the formula. Verify NAS
membership against the directory.

## Required behaviors

### ✅ Cite the URL in every explanation

Every factual claim in the candidate's `explanation` field needs an
inline source. Examples:

- "co-authored 4 papers in 2022–2024 (Google Scholar)"
- "co-PI on ATLAS Higgs subgroup since 2017 (INSPIRE-HEP)"
- "academic siblings — both PhD'd under H. Georgi at Harvard (Math Genealogy)"
- "lab page (URL) lists 3 PhDs admitted in 2023"

### ✅ Mark unverified data as missing

Better:
- `paths_to_advisors[adv_id] = {}` — empty
- `pi_signal = "missing"`
- `collab_with_nas = false` (when you didn't verify NAS membership)

These trigger the matcher's wider confidence band, which **honestly
communicates** to the user that this candidate's signals aren't fully
verified.

### ✅ Prefer the canonical primary source

For HEP papers: INSPIRE-HEP > general Google Scholar.
For bio papers: PubMed / Europe PMC > general Google Scholar.
For genealogy: Math Genealogy Project > faculty bios > Wikipedia.

Wikipedia is acceptable as a starting point but always verify on a primary
source before recording an edge.

### ✅ Record what you searched

Even when a search returns nothing, note it in your reasoning:

> "Searched OpenAlex for co-authored works between [advisor_id] and
> [candidate_id] — 0 results. Checked Math Genealogy for both — neither
> in database. paths_to_advisors[adv_001] = {} for this candidate."

This makes the missing-data state auditable.

## When integrity rules conflict with completeness

You'll sometimes find a candidate the user really cares about, but you
can't verify specific signals through the allowed sources. **Always favor
honest-but-missing over present-but-fabricated.**

The matcher handles missing data:
- Empty `paths_to_advisors` → C falls back to field strength only
- `pi_signal = "missing"` → admit_likelihood penalized −0.1
- Many missing signals → confidence band widens to ±0.7

A candidate ranked at admit_likelihood = 2.8 (±0.7) on **real** data is far
more useful than admit_likelihood = 3.4 (±0.3) on **fabricated** data.

## Why this matters

A student making a real life decision based on a hallucinated co-authorship
edge could:
- Apply to the wrong programs
- Waste their time on a misaligned advisor
- Misjudge their actual fit and miss better opportunities
- Lose months of their PhD timeline

If you can't find verifiable data for a candidate, **say so in the result
presentation**:

> *"For Prof. X, I couldn't find verifiable connection signals to Prof.
> Wang via OpenAlex / Math Genealogy / INSPIRE-HEP. The Connection score
> reflects field-strength only and the confidence band is ±0.7. Take this
> ranking as approximate."*

Honest uncertainty serves the student. Fabricated certainty harms them.
