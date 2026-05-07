# Research Fit v2 — structured 6-axis score (Sprint-2-c3)

The roadmap-#4 research fit was a single 0–1 score plus a free-form
`research_fit_axes: dict[str, float]`. Sprint-2-c3 adds a fixed-schema
`ResearchFit` submodel that the matcher scores deterministically.

> **Tie-breaker only — sort-key role unchanged.** `research_fit_score`
> is rank #3 in the post-#5 sort ladder; it never overrides
> risk-adjusted strength or difficulty-adjusted strength. The
> connection-first thesis is preserved.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.**

## ResearchFit schema

```jsonc
"research_fit": {
  "topic_fit":             0.95,   // subfield / problem-area alignment
  "method_fit":            0.85,   // methodology / technique alignment
  "system_or_dataset_fit": 0.80,   // system / dataset / material / organism / detector
  "theory_experiment_fit": 0.90,   // mainly physics; stored only, NOT in v1 formula
  "temporal_fit":          0.70,   // is the candidate still publishing on this topic?
  "grant_fit":             0.60,   // active grants align with the area
  "student_background_fit": 0.50,  // student's coursework / prior research prepares them

  "evidence": {
    "research_fit": {
      "items": [{
        "url": "https://scholar.google.com/citations?user=...",
        "source_type": "google_scholar",
        "claim": "5 of last 8 papers on H→cc̄, 2 NIH grants on ATLAS analysis",
        "supports_fields": ["research_fit"]
      }]
    }
  }
}
```

## Scoring formula

```
research_fit_score = 0.30 · topic_fit
                   + 0.20 · method_fit
                   + 0.15 · system_or_dataset_fit
                   + 0.15 · temporal_fit
                   + 0.10 · grant_fit
                   + 0.10 · student_background_fit
```

Weights sum to 1.0. All axes are bounded [0, 1] by Pydantic.

`theory_experiment_fit` is **stored but NOT in the v1 formula**. It's
kept for transparency (especially in physics where the theory ↔
experiment distinction is structural) and may enter as a ±0.05
modifier in a future calibration round.

## Resolution priority

When `compute_match` populates `MatchResult.research_fit_score`:

1. **`candidate.research_fit` (v2 structured) is set** → derive from
   the formula above. Wins over the legacy field.
2. **Else `candidate.research_fit_score` (legacy) is set** → use it
   directly.
3. **Else** → `None` (not computed; not counted in evidence coverage).

## Evidence

Strict mode requires `supports_fields=["research_fit"]` for the score
to be verified. Evidence may live in **either** location for back-compat:

- `candidate.research_fit.evidence["research_fit"]` (v2 location;
  preferred when using the structured submodel)
- `candidate.evidence["research_fit"]` (legacy candidate-level
  location; still accepted)

Either path verifies the `research_fit` coverage entry.

A `research_fit` set without evidence is unsourced (high severity in
`audit_candidates.py`); strict mode rejects it.

## Per-axis interpretation

| Axis | Range guidance |
|------|----------------|
| `topic_fit` | 1.0 = same problem (H→cc̄ × H→cc̄). 0.7 = adjacent (H→cc̄ × H→bb̄). 0.4 = same broad subfield. 0.1 = different. |
| `method_fit` | 1.0 = same technique (BDT × BDT). 0.7 = adjacent (BDT × NN). 0.3 = different paradigm (analysis × theory). |
| `system_or_dataset_fit` | 1.0 = same system (ATLAS × ATLAS). 0.5 = same family (ATLAS × CMS). 0.0 = unrelated. |
| `theory_experiment_fit` | 1.0 = same camp. 0.5 = adjacent (theorist with experimental collaborations). 0.0 = pure other camp. |
| `temporal_fit` | 1.0 = recent papers on the topic. 0.5 = ~5 years ago. 0.1 = pivoted away. |
| `grant_fit` | 1.0 = active grants on the topic. 0.5 = grants in the broader area. 0.0 = different funded direction. |
| `student_background_fit` | 1.0 = student has the prerequisites (coursework / research). 0.5 = needs catching up. 0.0 = mismatch (e.g., no wet-lab for a wet-lab PI). |

## Why not include theory_experiment_fit in the formula

The theory↔experiment distinction is binary in some fields (physics)
and meaningless in others (math, CS theory vs systems is already
captured in `system_or_dataset_fit`). Adding a fixed weight would
under-weight it for physics or over-weight it for fields where it
doesn't apply. Keeping it as display-only data lets future per-field
calibration decide.

## Migration from legacy `research_fit_axes`

The legacy `research_fit_axes: dict[str, float]` (free-form per-field
keys via `FieldProfile.research_fit_axes`) is preserved on
`CandidateAdvisor` for back-compat. When the new structured
`research_fit: ResearchFit` is set, the matcher derives the score from
the v2 formula and ignores the legacy dict.

The roadmap #4 `validate_research_fit_axes` axis-key warning still
applies to the legacy dict — agents transitioning to v2 should clear
both fields rather than mixing.
