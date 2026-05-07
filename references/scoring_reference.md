# Scoring quick-reference

In-context recap of the formulas. **Source of truth is
[`docs/scoring.md`](../docs/scoring.md)** — read that for derivations,
edge cases, and rationale. This file is the cheat-sheet the agent
should keep open while running matches.

## CAPEG — five pillars

```
match_score = w_C·C + w_A·A + w_P·P + w_E·E + w_G·G
```

All five on a 4.0 scale, tier-adaptively weighted by school
competitiveness. **C remains the largest pillar in the top three tiers
(connection-first invariant).** A is bounded so it never outranks C.

| School tier | w_C | w_A | w_P | w_E | w_G |
|-------------|-----|-----|-----|-----|-----|
| Top 10      | 0.38 | 0.17 | 0.27 | 0.10 | 0.08 |
| Top 11–30   | 0.35 | 0.15 | 0.25 | 0.12 | 0.13 |
| Top 31–60   | 0.30 | 0.15 | 0.22 | 0.15 | 0.18 |
| Top 60+     | 0.25 | 0.12 | 0.18 | 0.18 | 0.27 |

| Pillar | What it scores |
|--------|----------------|
| **C** Connection | Max of co-authorship / genealogy / shared-collab / committee edges per (student-advisor, candidate-advisor) pair. Path-only — candidate's own prestige is in A, not here. |
| **A** Advisor Influence | Candidate PI's intrinsic standing: 0.30·influence_percentile + 0.20·elite_status + 0.20·active_funding + 0.20·grad_placement + 0.10·recruiting_health. |
| **P** Publication | Field-aware tier × position decay × status-weight, top-3 weighted aggregate. 5+ author rule: `min(3.5, baseline − 0.45)` floor. |
| **E** Experience | `0.20·lab_prestige + 0.30·duration + 0.50·output`, strongest single experience. |
| **G** GPA | Direct on 4.0; 4.3/4.5/100/UK normalized. |

## Application strength

```
application_strength = clip(match_score + tier_adj + pi_adj, 0, 4.0)
```

Tier adjustments reflect realistic admit rates:

| School tier | tier_adj | reason |
|-------------|----------|--------|
| Top 10      | **−1.0** | top-10 reject ~90–95% |
| Top 11–30   | **−0.5** | |
| Top 31–60   | 0       | baseline |
| Top 60+     | **+0.4** | top-60+ admit ~25–35% |

PI signal adjustments:

| pi_signal | pi_adj |
|-----------|--------|
| strong (≥2 new PhDs/yr) | +0.2 |
| normal (1–2/yr) | 0 |
| shrinking (<1/yr) | −0.4 |
| missing | −0.1 |
| not_recruiting | force application_strength = 0 |

> `application_strength` is **NOT a probability**. It's a 4.0-scale
> relative-fit index. There is no historical admit data behind it.

## Confidence band → risk-adjusted ranking

Band widens with unverified count (see
[`evidence_schema.md`](evidence_schema.md) for the table).

```
risk_adjusted_strength = application_strength − confidence_band / 2
lower_bound            = max(0.0, application_strength − confidence_band)
```

The matcher's **primary sort key is `risk_adjusted_strength`**, not raw
`application_strength`. Wide bands (sparse evidence) move candidates
*down* the list — the agent literally cannot get a top rank with
unsourced numbers.

## Sort key — tie-break ladder (post-roadmap-#4)

```
descending priority:
  1. risk_adjusted_strength
  2. research_fit_score              (None → -∞, sorts last among ties)
  3. direction_relevance             (keyword overlap fallback)
  4. application_strength            (raw)
  5. lower_bound                     (final tiebreak — favors narrower band)
```

Research fit is **not** part of the match formula — it cannot move
`risk_adjusted_strength`. It only breaks ties when two candidates land
otherwise equal. See [`research_fit.md`](research_fit.md).

## 5-tier label (applied to `application_strength`, not risk-adjusted)

| Label | Range |
|-------|-------|
| `Safe`      | ≥ 3.5 |
| `Match`     | 3.0–3.5 |
| `Target`    | 2.5–3.0 |
| `Reach`     | 2.0–2.5 |
| `Far Reach` | < 2.0 |

## Field-aware paper scoring

The scoring engine itself is field-agnostic; FieldProfile drives the
calibration:

- `big_collab_threshold` — total-author count above which a paper is
  big collab (physics 10, mse/cs 8, biology/chemistry 6, math 4).
- `co_first_supported` — whether `author_role: "co_first"` overrides
  byline position (true for cs, biology; false elsewhere — overrides
  silently dropped, with a warning surfaced in `input_warnings`).
- `paper_status_weight_overrides` — e.g., math sets `preprint=0.9`
  (vs default 0.7).
- `senior_author_position` — `last` for chemistry/mse/biology;
  `n/a` for physics/math.

See [`field_profiles.md`](field_profiles.md) for the bundled catalog.
