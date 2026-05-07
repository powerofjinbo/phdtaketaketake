# Scoring formulas — v0.3 (post-review)

> All four dimensions on a 4.0 scale (matching GPA), tier-adaptively weighted
> by school competitiveness. **Real-data-only** — see
> [`references/data_integrity.md`](../references/data_integrity.md).

## Dimensions

### 1. Pub Score (P)

Per paper:

```
paper_score = (baseline(tier) − decrement(position)) × status_weight(status)
```

Position 5+: replace `(baseline − decrement)` with `min(3.5, baseline − 0.45)` —
big-collab credit without inversion at lower tiers.

**Tier baselines:**

| Tier | Baseline | Examples |
|------|----------|----------|
| `"S"` | 4.0 | Nature, Science, Cell |
| `1` | 4.0 | PRL, JACS, Nat Materials, Cell subs |
| `2` | 3.7 | PRX, Adv Materials, Nano Letters, eLife |
| `3` | 3.3 | PRD, Chem Mater, J Mater Chem A |
| `4` | 2.8 | PR Applied, J Appl Phys |
| `5` | 2.3 | weak SCI / workshops |
| `0` | 0 | retracted / predatory |

**Position decrement:** 1 → 0, 2 → 0.10, 3 → 0.25, 4 → 0.45.

**Status weights** (post-review #8):

| Status | Weight | Meaning |
|--------|--------|---------|
| `published` / `accepted` / `in_press` | 1.0 | already on (or guaranteed on) the CV |
| `submitted` / `preprint` | 0.7 | on arXiv or under review |
| `in_prep` | 0.3 | drafting, not real submission |

Unknown status raises an error (no silent default to 1.0).

**Multi-paper aggregation** (top-3 weighted):
- 0 papers → `3.0` (floor)
- 1 paper → that paper's score
- 2 papers → `0.7 · best + 0.3 · 2nd_best`
- 3+ papers → `0.5 · best + 0.3 · 2nd + 0.2 · 3rd` (only top-3)

### 2. GPA Score (G)

Multi-system normalization (see `references/profile_schema.md` for the full
table). Direct on 4.0; percentage and 4.3 / 4.5 / UK-honours systems all
mapped.

### 3. Experience Score (E)

```
E = 0.20 · lab_prestige + 0.30 · duration + 0.50 · output
```

Strongest single experience, no stacking. Lab tiers in
[`references/lab_tiers.md`](../references/lab_tiers.md).

### 4. Connection Score (C) — per (student, candidate) pair

Differentiated edges (post-review #5). The matcher takes **max** strength
across present edge types — no stacking — to avoid double-counting overlapping
evidence.

**Roadmap-#3 split**: C used to mix path strength with the candidate's own
network signals (h-index proxy / NAS / placement). Those now live in the
A dimension; C is path-only. Without a `current_advisor`, C falls to the
lowest bucket (2.3).

**Co-authorship edges:**

| Edge | Strength formula |
|------|------------------|
| `small_team_coauthor_5y` (≤10 authors) | `min(1.0, n/5)` |
| `big_collab_papers_5y` (>10 authors) | `min(0.4, n/25)` — discounted: alphabetical author list ≠ working relationship |

**Subgroup / analysis-level edges** (high-strength big-collab evidence):

| Edge | Strength |
|------|----------|
| `same_working_group` (verified subgroup / convener overlap) | 0.7 |
| `analysis_contact_overlap` (shared analysis-contact role) | 0.95 |

**Genealogy:**

| `genealogy_relation` | Strength |
|---------------------|----------|
| `same_advisor` (academic siblings) | 1.0 |
| `uncle_nephew` (advisor's PhD sibling) | 0.7 |
| `two_hop` (advisors' advisors crossed paths) | 0.4 |

**Other:**

| Edge | Strength |
|------|----------|
| `collaboration_overlap_years` (generic shared collab when finer signals unavailable) | ≥5y → 1.0, 1–5y → 0.6, <1y → 0.3 |
| `committee_co_member` (`same_period: true`) | 0.8 |
| `committee_co_member` (`same_period: false`) | 0.3 |

**Field strength** (candidate's own network, advisor-independent):

```
C_field = 0.4 · normalized_collab_top20pct
        + 0.3 · (1.0 if collab_with_nas else 0.0)
        + 0.3 · grad_placement_quality
```

Three-state semantics (post-review): each input field can be `None`
(not checked) — None contributes 0 to scoring (conservative; pushes the
agent to actually verify).

**Composite (post-roadmap-#3)**:

```
C_raw = max_path_strength
```

(Field-strength terms moved out to the A dimension.) Without a current
advisor: `C_raw = 0` → bucket 2.3 (lowest).

**0–1 → 4.0 mapping:** ≥0.8 → 4.0, 0.6–0.8 → 3.7, 0.4–0.6 → 3.3, 0.2–0.4 → 2.8, <0.2 → 2.3

### 4b. Advisor Influence Score (A) — per candidate, post-roadmap-#3

The A dimension answers "is this PI strong, active, and a good place to
invest 5–6 years?" — separate from C, which answers "do I have a real
connection to them?".

```
A_raw = 0.30 · influence_percentile  (h-index proxy)
      + 0.20 · elite_status          (NAS / HHMI / NAE / field-specific fellow)
      + 0.20 · active_funding_quality
      + 0.20 · grad_placement_quality
      + 0.10 · recruiting_health     (from pi_signal: strong=1.0, normal=0.7,
                                       shrinking=0.3, missing=0.5,
                                       not_recruiting=0.0)
```

`A` then maps 0–1 → 4.0 via the same `raw_to_4_0` buckets as C.

`pi_signal` feeds two distinct uses (NOT double-counting):
- A's `recruiting_health` term (lab health signal)
- `application_strength`'s `pi_adj` (admit-cycle availability)

These ask different questions — same input, separate outputs.

## Final scores

### Match score (tier-adaptive, 5-pillar CAPEG post-roadmap-#3)

```
match = w_C · C + w_A · A + w_P · P + w_E · E + w_G · G
```

| School tier | w_C | w_A | w_P | w_E | w_G |
|-------------|-----|-----|-----|-----|-----|
| Top 10 | 0.38 | 0.17 | 0.27 | 0.10 | 0.08 |
| Top 11–30 | 0.35 | 0.15 | 0.25 | 0.12 | 0.13 |
| Top 31–60 | 0.30 | 0.15 | 0.22 | 0.15 | 0.18 |
| Top 60+ | 0.25 | 0.12 | 0.18 | 0.18 | 0.27 |

C remains the largest pillar in the top three tiers (connection-first); at
top_60+, GPA edges above C (consistent with the original CPEG calibration's
"lower tier weights GPA more"). **A is bounded so it never outranks C** —
the A pillar measures the candidate PI's intrinsic strength, but doesn't
get to dilute the connection-first thesis.

### Application strength

> **Important**: `application_strength` is **NOT a probability**. It's a
> 4.0-scale relative-fit index. There's no historical admission data behind
> it — calibration is qualitative.

```
application_strength = clip(match + pi_adj, 0, 4.0)
```

Post-roadmap-#5: school-tier difficulty no longer enters
`application_strength` directly. Its admit-rate role moved into
`program_difficulty_penalty`'s `school_tier_admit_rate_factor`
component, and the matcher now exposes
`difficulty_adjusted_strength = risk_adjusted_strength − penalty` as
the primary sort key. See [`references/program_profile.md`](../references/program_profile.md).

| PI signal | pi_adj |
|-----------|--------|
| strong (≥2 new PhDs/yr) | +0.2 |
| normal (1–2/yr) | 0 |
| shrinking (<1/yr) | −0.4 |
| missing data | −0.1 |
| not recruiting | force to 0 |

`pi_adj` stays inside `application_strength` for v2 commit 1; commit 2
(Opportunity / A refactor) will reorganize this boundary.

### Confidence band (driven by evidence coverage)

| Unverified signal count | Band |
|-------------------------|------|
| 0 (everything sourced) | ±0.2 |
| 1–2 | ±0.4 |
| 3–4 | ±0.6 |
| 5+ (mostly unsourced) | ±0.8 |

### Program difficulty (post-roadmap-#5)

```
program_difficulty_penalty   = clip(school_tier_factor + cohort_factor + admission_factor
                                    + funding_factor + area_factor + intl_factor, 0.0, 0.8)
difficulty_adjusted_strength = max(0.0, risk_adjusted_strength − program_difficulty_penalty)
```

`difficulty_adjusted_strength` is the **primary sort key** post-#5. The
5-tier label is now applied to it (not to `application_strength`). See
[`references/program_profile.md`](../references/program_profile.md) for
the per-component table and calibration rationale.

### Sort order (tie-break ladder, post-roadmap-#5)

The ranker uses this descending priority:

1. `difficulty_adjusted_strength` — **primary key (post-#5)**
2. `risk_adjusted_strength` (= `application_strength − band/2`)
3. `research_fit_score` (None → −∞, ranked last among ties)
4. `direction_relevance` (keyword overlap fallback)
5. `application_strength` (raw)
6. `lower_bound` (final tiebreak — favors narrower band)

Research fit is **not** part of the match formula — it cannot move
`risk_adjusted_strength` and (since #5) cannot move
`difficulty_adjusted_strength` either. It only breaks ties when two
candidates are otherwise equal. The connection-first thesis is preserved.

To make this airtight, `research_fit` is excluded from evidence
coverage when `research_fit_score is None` — otherwise a missing fit
would count as one extra missing signal, widen the band, and indirectly
lower `risk_adjusted_strength`. Counted only when set; verified when
sourced; unsourced (and rejected by strict mode) when set without
`supports_fields=["research_fit"]` evidence. The same opt-in pattern
applies to ProgramProfile signals — only set fields enter coverage.

A signal counts as unverified unless an `EvidenceSource` in
`EvidenceEntry.items` (or `PathEdge.items`) lists that signal's field
name in `supports_fields`. Default mode also accepts the legacy
`sources: list[str]` form as a fallback; **strict mode does not**. Counts
against:
- each path to a current advisor (missing entirely or unsourced)
- `school_tier` (post-review: ranking source must be cited)
- `research_areas` (faculty page or recent paper abstracts)
- `normalized_collab_top20pct`, `collab_with_nas`,
  `grad_placement_quality`, `active_funding_quality` (regardless of
  value — None / default / non-default all need sources)
- `pi_signal == "missing"` OR non-missing without sources
- `research_fit` — **only when `research_fit_score` is set** (a null
  score is not counted at all, so a missing fit cannot widen the band
  and cannot indirectly move `risk_adjusted_strength`; this preserves
  the tie-breaker-only invariant)

Default values without sources count the same as `None` — both treated as
"didn't verify".

### Risk-adjusted ranking (post-review)

The matcher's primary sort key is `risk_adjusted_strength`, not raw
`application_strength`:

```
risk_adjusted_strength = application_strength − confidence_band / 2
```

Half the band is subtracted as a downside discount. A well-sourced 3.0 ±0.2
candidate (risk-adjusted 2.9) outranks a loosely-claimed 3.2 ±0.8 candidate
(risk-adjusted 2.8). This means **the agent literally can't get a top rank
by writing nice numbers without sources** — the band would widen and the
risk-adjusted score would drop.

### 5-tier label (applied to `difficulty_adjusted_strength` post-roadmap-#5)

- `Safe` ≥ 3.5
- `Match` 3.0–3.5
- `Target` 2.5–3.0
- `Reach` 2.0–2.5
- `Far Reach` < 2.0

Pre-#5 the label was applied to `application_strength` — see the v1
calibration in [`references/program_profile.md`](../references/program_profile.md)
for the calibration shifts vs v1.

### MatchResult output fields

The matcher returns these per candidate. Newer fields below the line are
post-review additions:

| Field | Meaning |
|-------|---------|
| `match_score` | CAPEG weighted composite, 0–4.0 |
| `application_strength` | `match + pi_adj`, clipped 0–4.0 (NOT a probability) |
| `confidence_band` | ±0.2 / 0.4 / 0.6 / 0.8 by evidence coverage |
| `strength_label` | `Far Reach` / `Reach` / `Target` / `Match` / `Safe` — applied to `difficulty_adjusted_strength` (post-#5) |
| --- | --- |
| `risk_adjusted_strength` | = `application_strength − band/2` |
| `lower_bound` | = `application_strength − band`; conservative reading at uncertainty edge |
| `program_difficulty_penalty` | 0–0.8 from `school_tier` + ProgramProfile signals (post-#5) |
| `difficulty_adjusted_strength` | = `max(0, risk_adjusted_strength − penalty)`; **primary sort key (post-#5)** |
| `difficulty_reasons` | per-component contributions (e.g., "small cohort (4/yr) +0.10") |
| `unverified_signals` | total of missing + unsourced |
| `missing_signals` | signals where the agent didn't search (information gap) |
| `unsourced_signals` | signals claimed without claim-level proof (hallucination risk) |
| `total_signals` | base 8 for 1-advisor; +1 per set `research_fit_score`; +N per set program signal |
| `missing_signal_names` / `unsourced_signal_names` | namespaced (`path:<id>`, `program:<field>`, …) |
| `explanation` | one-string narrative with `Evidence coverage:` line + per-claim source citations |

## Why this design

- **Connection-first**: real PhD admissions hinge on advisor recommendations
  and academic-network trust. h-index doesn't capture this.
- **5+ author rule**: HEP / big-collab papers list hundreds of authors
  alphabetically; treating position 312 as "barely contributed" is wrong,
  but treating it as 1st-author equivalent is also wrong. The
  `min(3.5, …)` floor balances this.
- **Big-collab differentiation**: 5 ATLAS papers as alphabetical co-authors
  is a much weaker signal than 5 small-team papers — `big_collab_papers_5y`
  caps at 0.4 strength while `small_team_coauthor_5y` saturates at 1.0.
- **Tier-adaptive weights**: top-10 schools care more about your network
  and pubs; top-60+ weight GPA more.
- **Output-dominant Experience**: just being in a famous lab without
  producing matters less than producing something tangible.
- **Steep top-10 admit penalty (−1.0)**: top-10 PhD programs reject ~90–95%
  of applicants. The −1.0 forces even a perfect 4.0 candidate to land at
  `Match` (3.0), not `Safe` — honest about top-school selectivity.
- **Risk-adjusted ranking**: evidence has to drive ranking, not just
  decorate it. Wide bands move candidates down the list.
- **Paper status weights**: `published` / `accepted` get full credit;
  `submitted` / `preprint` 0.7×; `in_prep` 0.3×. Honesty about pipeline
  maturity affects scoring.
