# Research fit — tie-breaker, NOT a pillar

Research fit is a 0–1 alignment score between the student's
`research_direction` and the candidate's actual recent work. It is
**not** part of the match formula — it does not move `match_score` or
`application_strength`. It only breaks ties in the sort order when two
candidates land at the same `risk_adjusted_strength`.

The connection-first thesis is preserved by construction: research fit
**cannot** beat clearly stronger risk-adjusted strength.

> The score lives on `CandidateAdvisor`, so it must be filled in **before**
> the matcher runs. You can't compute it after-the-fact.

## When to use it

- You have multiple candidates with similar evidence quality and
  similar risk-adjusted scores, and you want to surface the one whose
  recent papers most clearly align with the student's direction.
- You want the result card to honestly say "this PI's last 8 papers are
  on H→cc̄" vs "this PI's recent work is mostly EFT theory".

When unsure, **leave it null**. A null fit is not counted in evidence
coverage and does not widen the band — it just shows as "not computed"
in the result card. Don't write a fake 0.5 placeholder; that becomes an
unsourced claim and hurts the candidate.

## Schema

```jsonc
{
  "research_fit_score": 0.78,
  "research_fit_summary": "5 of last 8 papers on H→cc̄, primary detector matches",
  "research_fit_axes": {
    "subfield":              0.95,
    "detector_or_technique": 1.0,
    "process_or_topic":      0.8,
    "experiment_vs_theory":  1.0,
    "collaboration":         0.5
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

Pydantic enforces axis values are in `[0, 1]`; out-of-range fails
validation.

## Per-field axes

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

Axis keys not declared by the active FieldProfile produce a warning in
`input_warnings` (the score still scores; the warning flags drift —
e.g., a CS-field candidate using `detector_or_technique`, which is a
physics axis).

## Strict mode

| Case | Behavior |
|------|----------|
| `research_fit_score: null` | allowed; not counted in coverage; shows "not computed" in card |
| `research_fit_score: 0.7` + `evidence["research_fit"].items` with `supports_fields=["research_fit"]` | **verified** |
| `research_fit_score: 0.7` + no item / wrong supports_fields | **rejected** in strict mode (unsourced claim) |
| Axis value outside `[0, 1]` | **rejected** at Pydantic time (before scoring) |
| Axis key not in FieldProfile | warning in `input_warnings`; score still goes through |

## Sort key (where research fit appears)

```
descending priority:
  1. risk_adjusted_strength
  2. research_fit_score              ← here, only as tie-breaker
  3. direction_relevance             (keyword overlap)
  4. application_strength            (raw)
  5. lower_bound
```

Two candidates at the same `risk_adjusted_strength`: higher
`research_fit_score` wins. Two candidates at different
`risk_adjusted_strength`: research fit doesn't matter — the higher
risk-adjusted candidate ranks first regardless of fit.

`research_fit_score = None` sorts as `−∞` against any non-null score, so
a candidate with even a low fit set will outrank one with no fit set
when `risk_adjusted_strength` ties.

## Why this is a tie-breaker, not a pillar

A naive 6th pillar that re-weighted the match formula would dilute the
connection-first thesis: you could have a "perfect-fit but no-connection"
candidate beat a "verified-strong-connection but slightly off-topic"
candidate. That's the wrong answer for a PhD application — what
matters is the recommendation letter and the network, both of which
hinge on Connection.

By making research fit a **pure tie-breaker** (and excluding null fits
from evidence coverage entirely so they don't sneak in via the band),
the score remains honest: research fit is information, not weight.

## How to compute it

The matcher does not score research fit for you — the agent fills it
in based on actual research direction × candidate's recent papers.
Reasonable axis-level scoring guidance:

- **1.0**: direct match (same subfield, same technique, same problem)
- **0.7–0.9**: clear overlap (e.g., same broad subfield, adjacent
  technique)
- **0.4–0.6**: tangential (some shared keywords, different focus)
- **0.0–0.3**: unrelated (different subfield or methodology)

Aggregate to `research_fit_score` however suits the field — equal mean,
weighted mean, min, etc. The scoring is honest as long as the axes are
honestly populated and the evidence URL points at the agent's actual
read of the candidate's recent papers.

## Don't game it

- Setting `research_fit_score = 0.9` on every candidate so they all
  outrank a no-fit candidate doesn't help anyone — strict mode rejects
  unsourced fits, and the per-axis breakdown surfaces in the explanation.
- Setting `research_fit_score = 0.0` to "drop" a candidate also doesn't
  work — the matcher still sorts by `risk_adjusted_strength` first; fit
  only changes ties.
