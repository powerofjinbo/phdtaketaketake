# Example: Physics / HEP applicant — full pipeline

This is a **complete end-to-end run** of the four CLIs against a
fictional physics / HEP applicant. All inputs and outputs are checked
in so you can read the JSONs without running anything; the
`run_example.sh` script reproduces them deterministically using the
bundled OpenAlex fixtures (no network access).

> ⚠️ **All names below are fictional.** This demo shows the *shape*
> of the matcher's output, not actual ranking claims about real PIs.

## The applicant

[`profile.json`](profile.json):

- **Tsinghua University** undergrad, GPA 3.85 / 4.0
- Direction: **ATLAS Higgs precision (H→cc̄ / VH cross-section)** with detector-side ML
- Current advisor: **Prof. Lisa Wang** (Tsinghua)
- 2 ATLAS papers (PRL position 456 + PRD position 312 — typical big-collab signature)
- 18-month honors-thesis lab experience

Student wants top-10 US physics PhD programs.

## The 3 candidates ([`candidates_raw.json`](candidates_raw.json))

| ID | Name | Institution | Notes |
|---|---|---|---|
| `cand_hartman_mit` | Prof. Alex Hartman | MIT | Higgs / ATLAS / detector ML — **strong topical overlap** |
| `cand_chen_berkeley` | Prof. Riley Chen | UC Berkeley | ATLAS, but BSM / dark matter — partial overlap |
| `cand_lin_stanford` | Prof. Casey Lin | Stanford | Theoretical EFT — **no ATLAS detector overlap** |

These are the **minimal** records the agent might write after a
discovery-plan-driven web search. None of the deeper signals (paths,
research areas, h-index, opportunity, program profile) are filled —
that's what the rest of the pipeline does.

## Run

```bash
# from the repo root, with the package installed (`pip install -e .`):
bash examples/physics_hep_strict/run_example.sh
```

The 4 stages overwrite their respective output JSONs in this directory.

---

## Stage 1 — discovery plan ([`discovery_plan.json`](discovery_plan.json))

```bash
phdtaketaketake-discovery-plan \
  --field physics \
  --schools '["MIT", "UC Berkeley", "Stanford"]' \
  --keywords "ATLAS Higgs precision"
```

Generates **5 search recipes × 3 schools = 15 query strings** the
agent should run via its own web-search tools (Google Scholar /
INSPIRE / arXiv / faculty pages / ATLAS Glance), plus the universal
exclusion rules (skip emeriti, etc.) and the field's caveats.

Sample queries the plan produces:

```jsonc
{"engine": "google_scholar", "query": "\"MIT\" \"ATLAS Higgs precision\" site:scholar.google.com", ...}
{"engine": "inspire",        "query": "ATLAS Higgs precision site:inspirehep.net", ...}
{"engine": "atlas_glance",   "query": "ATLAS Higgs precision site:atlas-glance.cern.ch", ...}
```

This is the **agent-driven** half of the search. The agent then writes
the `candidates_raw.json` we already have above.

## Stage 2 — auto-collect evidence ([`candidates_enriched.json`](candidates_enriched.json))

```bash
phdtaketaketake-collect-evidence \
  --profile-file profile.json \
  --candidates-file candidates_raw.json \
  --field physics \
  --fixture-dir fixtures/ \
  --out candidates_enriched.json
```

This is the **skill-driven** half. The collector hits OpenAlex
(here in fixture mode for reproducibility) for each candidate +
the student's advisor, and auto-fills:

- **`research_areas`** from author concepts
- **`normalized_collab_top20pct`** from `min(1.0, h_index/50)`
- **`paths_to_advisors[adv_001]`** from coauthored works between
  candidate and advisor — automatically split into
  `small_team_coauthor_5y` (≤ 10 authors) vs `big_collab_papers_5y`
  (> 10 authors), with `most_recent_connection_year`
- **Verified-empty path** when 0 coauthored works are found (with
  `supports_fields=["path:adv_001"]` so strict mode passes)
- **`research_fit` evidence items** (URLs only — no score) from
  recent papers whose title/concepts overlap the student's
  `research_direction`

Resulting differentiation:

| Candidate | small_team | big_collab | most_recent |
|---|---|---|---|
| Hartman (MIT) | 3 | 2 | 2024 |
| Chen (Berkeley) | 0 | 1 | 2023 |
| Lin (Stanford) | — | — | — (verified-empty path) |

`collection_summary` reports **9 / 24 fields filled**, with the
unresolved ones being signals OpenAlex doesn't cover (`pi_signal`,
`grad_placement_quality`, etc. — the agent fills these via Stage 1
queries on lab pages and alumni pages).

## Stage 3 — audit ([`audit.json`](audit.json))

```bash
phdtaketaketake-audit \
  --profile-file profile.json \
  --candidates-file candidates_for_match.json \
  --field physics
```

Reports the evidence repair queue **before** the matcher runs:

```
strict_ready=False  (3 / 3 candidates have unsourced claims)
total signals audited:  24
  verified: 9   missing: 12   unsourced: 3
```

The repair queue separates **high severity** (set values without
`supports_fields`-bound proof — strict-mode blockers) from **medium**
(missing data — won't block strict mode but widens the band). The
agent should fix high entries before re-running with
`--strict-evidence`.

## Stage 4 — match ([`match.json`](match.json))

```bash
phdtaketaketake-match \
  --profile-file profile.json \
  --candidates-file candidates_for_match.json \
  --field physics --top-k 5
```

The deterministic ranking + strategy:

| Rank | Candidate | C | app_strength | diff_adj | label | strategy |
|---|---|---|---|---|---|---|
| 1 | Hartman (MIT) | 3.7 | 3.3 | **2.2** | Reach | **target** |
| 2 | Chen (Berkeley) | 2.3 | 2.76 | 1.66 | Far Reach | reach |
| 3 | Lin (Stanford) | 2.3 | 2.68 | 1.58 | Far Reach | only_if_space |

Reading the result:

- **Hartman wins on Connection** — 3 verified small-team papers with the student's advisor (`c_score=3.7`). Top of the list.
- **Chen and Lin tie on `c_score=2.3`** — Chen's only coauthored paper is a 3000-author ATLAS bulk paper (heavily discounted under the v2 big-collab cap of 0.10); Lin has no path at all (verified-empty). Both fall to the lowest C bucket.
- **Top-10 program difficulty pulls everyone down** — `program_difficulty_penalty=0.7` (school_tier_factor for top_10 with no `program_profile` to refine it) drops `risk_adjusted` to `difficulty_adjusted` by 0.7 across the board.
- **Strategy buckets diverge** — Hartman lands in `target` (clean enough connection signal); Chen falls to `reach` (high nominal but wide band); Lin lands in `only_if_space` because there's no path AND no strong research fit (the `temporal_fit` axis would be low — pivoted away from ATLAS detector work).

Top-level [`strategy_summary`](match.json) rolls this up:

```jsonc
{
  "priority_candidates":      [],
  "target_candidates":        ["cand_hartman_mit"],
  "reach_candidates":         ["cand_chen_berkeley"],
  "only_if_space_candidates": ["cand_lin_stanford"],
  "drop_candidates":          [],
  "portfolio_notes": [
    "3 candidates: 0 priority · 1 target · 1 reach · 1 only_if_space · 0 drop"
  ]
}
```

Hartman lands in `target` (clean enough connection signal + lowest
risk band) but **misses `priority`** because the priority bucket
requires (a) `unsourced=0`, (b) `risk_adjusted ≥ 2.70`,
(c) `lower_bound ≥ 2.30`, (d) verified strong C or strong fit.
The missing signals (no `pi_signal`, no `grad_placement_quality`,
no `program_profile`) keep the band wide enough that
`risk_adjusted` falls below 2.70. The next iteration of the
agent's work would gather those signals — once the band tightens,
Hartman would migrate from `target` to `priority`.

---

## What's NOT in the demo

To keep the example small + offline, this run does NOT exercise:

- **Live OpenAlex** (use `--live --mailto you@example.edu` instead of `--fixture-dir`)
- **`--strict-evidence`** (would block the audit + match — the demo intentionally has unsourced claims so you can see the repair queue)
- **PubMed / DBLP / Semantic Scholar** adapters (use `--source pubmed|dblp|semantic_scholar`)
- **Cache + rate-limit** wrappers (add `--cache-dir <path>` and `--rate-limit-seconds 0.1` for live runs)
- **Manual evidence fill** for `pi_signal`, `grad_placement_quality`, `active_funding_quality`, `program_profile` — these come from Stage-1 web searches the agent does manually

A "fully ready" candidate would also have these fields filled with
`supports_fields`-bound `EvidenceSource` items pointing at lab
pages, alumni pages, NIH RePORTER / NSF Award Search records,
department admissions pages, etc.
