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
| **A** Advisor Influence | Candidate PI's reputation / field standing / placement record. Post-#6a: `0.40·influence_percentile + 0.30·elite_status + 0.30·grad_placement_quality`. Funding and recruiting moved to **O** (Opportunity). |
| **P** Publication | Field-aware tier × position decay × status-weight, top-3 weighted aggregate. 5+ author rule: `min(3.5, baseline − 0.45)` floor. |
| **E** Experience | `0.20·lab_prestige + 0.30·duration + 0.50·output`, strongest single experience. |
| **G** GPA | Direct on 4.0; 4.3/4.5/100/UK normalized. |
| **O** Opportunity (NOT in match_score) | Time-sensitive admit-cycle availability — recruiting + funding + capacity + accessibility. Feeds `application_strength` via `opportunity_adj` (replaces v1 `pi_adj`). See [`opportunity.md`](opportunity.md). |

## Application strength

```
application_strength = clip(match_score + opportunity_adj, 0, 4.0)
```

- Post-roadmap-#5: `tier_adj` removed (school-tier difficulty moved to
  `program_difficulty_penalty`).
- Post-roadmap-#6a: `pi_adj` replaced by `opportunity_adj`, derived from
  the new Opportunity score (see below). `not_recruiting` still forces
  application_strength=0.

Pure-legacy candidates (no `opportunity_signal`) use the v1 PI_ADJ
table verbatim:

| pi_signal | adj (legacy + v2 mapping) |
|-----------|---------------------------|
| strong | +0.2 |
| normal | 0 |
| shrinking | −0.4 |
| missing | −0.1 |
| not_recruiting | force application_strength = 0 |

Migrated candidates with `opportunity_signal` get the richer adj from
the full O composite.

> `application_strength` is **NOT a probability**. It's a 4.0-scale
> relative-fit index. There is no historical admit data behind it.

## Opportunity (roadmap #6a)

```
O_raw = clip(
    0.30 · recruiting_health(pi_signal)
  + 0.30 · active_funding_quality
  + 0.20 · lab_capacity(open_positions, current_count, recent_grads)
  + 0.10 · funding_timing(grant_end_years)
  + 0.10 · availability(sabbatical_or_admin_load)
, 0, 1)
```

Ladder (replaces pi_adj):

| O range | opportunity_adj |
|---------|-----------------|
| ≥ 0.70 | +0.2 |
| ≥ 0.50 | 0.0 |
| ≥ 0.30 | −0.2 |
| < 0.30 | −0.4 |

`not_recruiting` (effective via field-by-field merge) → force
application_strength=0.

`o_score` and `opportunity_adj` are exposed on `MatchResult`. See
[`opportunity.md`](opportunity.md) for sub-component formulas, the
A vs O split, and migration rules.

## Program difficulty (roadmap #5)

```
program_difficulty_penalty   = clip(sum of components, 0.0, 0.8)
difficulty_adjusted_strength = max(0, risk_adjusted_strength − penalty)
```

| Component | Trigger | Δ |
|-----------|---------|---|
| `school_tier_admit_rate_factor` | top_10 / top_11_30 / top_31_60 / top_60+ | 0.70 / 0.50 / 0.30 / 0.00 |
| `cohort_factor` | <8 / ≥30 | +0.10 / −0.05 |
| `admission_factor` | direct_admit / rotation\|centralized | +0.10 / −0.05 |
| `funding_factor` | pi_grant / guaranteed | +0.10 / −0.05 |
| `area_factor` | ≤1 faculty / ≥5 faculty | +0.10 / −0.05 |
| `intl_factor` | friendliness <0.3 | +0.05 |

`difficulty_adjusted_strength` is the **primary sort key** post-#5; the
5-tier label is applied to it (not to raw `application_strength`). See
[`program_profile.md`](program_profile.md) for the full table and
calibration rationale.

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

## Sort key — tie-break ladder (post-roadmap-#5)

```
descending priority:
  1. difficulty_adjusted_strength    ← primary (post-#5)
  2. risk_adjusted_strength
  3. research_fit_score              (None → -∞, sorts last among ties)
  4. direction_relevance             (keyword overlap fallback)
  5. application_strength            (raw)
  6. lower_bound                     (final tiebreak — favors narrower band)
```

Program difficulty enters the *primary* sort key — a hard top_10
direct-admit small-cohort program is now visibly down-ranked vs an
equally-strong candidate at a broader, rotation-based program.
Research fit remains a pure tie-breaker (rank 3) — fits between
risk-adjusted and direction relevance, never overrides difficulty-
adjusted. See [`research_fit.md`](research_fit.md) and
[`program_profile.md`](program_profile.md).

## 5-tier label (applied to `difficulty_adjusted_strength` post-roadmap-#5)

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
