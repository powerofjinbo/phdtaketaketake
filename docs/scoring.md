# Scoring formulas

> 5-pillar **CAPEG** + 3 non-CAPEG dimensions (Opportunity / Program
> difficulty / Research fit) + Strategy bucket, all on a 4.0 scale,
> tier-adaptively weighted by school competitiveness. **Real-data-only** —
> see [`references/data_integrity.md`](../references/data_integrity.md).
>
> Pipeline overview: [`docs/scoring_pipeline.md`](scoring_pipeline.md)
> (Mermaid diagram + layer-by-layer explanation).

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

### 4. Connection Score (C) — per (student, candidate) pair (v2)

Sprint-2-c1 expanded the network model. Aggregation is now **strongest
single edge + 0.10 × second-strongest** (capped at 1.0), then scaled
by a **recency multiplier** based on `most_recent_connection_year`.
See [`references/connection_v2.md`](../references/connection_v2.md) for
the full schema, ladder, guardrails, and v1→v2 calibration shifts.

**Roadmap-#3 split**: C used to mix path strength with the candidate's own
network signals (h-index proxy / NAS / placement). Those now live in the
A dimension; C is path-only. Without a `current_advisor`, C falls to the
lowest bucket (2.3).

**Edge ladder (v2):**

| Edge | Strength |
|------|----------|
| `small_team_coauthor_5y` (≤threshold authors) | `min(1.0, n/5)` |
| `co_mentored_student_count` | `min(0.90, n·0.30)` |
| `shared_grant_count_5y` | `min(0.80, n·0.40)` |
| `same_working_group` (verified subgroup / convener overlap) | **0.75** |
| `analysis_contact_overlap` (shared analysis-contact role) | **0.70** |
| `genealogy_relation: same_advisor` | **0.65** |
| `genealogy_relation: uncle_nephew` | **0.50** |
| `committee_or_exam_overlap` (PhD committee / qualifying exam) | 0.45 |
| `genealogy_relation: two_hop` | 0.40 |
| `same_center_or_institute` | 0.40 |
| `prior_institution_overlap_years` | `min(0.35, years/10)` |
| `conference_session_overlap_5y` | `min(0.20, n·0.10)` |
| `big_collab_papers_5y` (>threshold authors) | **`min(0.10, n/100)`** — alphabetical author list ≠ working relationship |
| `collaboration_overlap_years` | ≥5y → 1.0, 1–5y → 0.6, <1y → 0.3 (unchanged from v1) |
| `committee_co_member` (`same_period: true`) | 0.8 (unchanged) |
| `committee_co_member` (`same_period: false`) | 0.3 (unchanged) |

**Aggregation:**
```
edge_raw = strongest_edge + 0.10 · second_strongest_edge   (cap 1.0)
edge_raw *= recency_multiplier(most_recent_connection_year)
```

**Recency multiplier:**

| gap (years) | multiplier |
|-------------|------------|
| 0–2 | 1.00 |
| 3–5 | 0.85 |
| 6–10 | 0.60 |
| 10+ | 0.35 |
| `None` | 0.75 (didn't capture year) |

**v1→v2 recalibration shifts** (bold values above changed): same_advisor 1.0→0.65, uncle_nephew 0.7→0.50, analysis_contact 0.95→0.70, same_working_group 0.7→0.75, big_collab cap 0.4→0.10. See [`references/connection_v2.md`](../references/connection_v2.md) for rationale.

**Big-collab threshold** is field-specific via
`FieldProfile.big_collab_threshold` (physics 10, mse/cs 8,
biology/chemistry 6, math 4). Use
`classify_coauthorship(author_count, field_profile)` to bucket.

**Composite (post-Sprint-2-c1)**:

```
C_raw = max(path_strength_v2(edges, current_year) for edges in paths)
```

`path_strength_v2` is the aggregation+recency formula above. Without a
current advisor: `C_raw = 0` → bucket 2.3 (lowest). The candidate's
intrinsic prestige (h-index proxy / NAS / placement) lives in A
(post-roadmap-#3); their admit-cycle availability lives in O
(post-roadmap-#6a).

**0–1 → 4.0 mapping:** ≥0.8 → 4.0, 0.6–0.8 → 3.7, 0.4–0.6 → 3.3, 0.2–0.4 → 2.8, <0.2 → 2.3

### 4b. Advisor Influence Score (A) — post-roadmap-#6a (reputation-only)

A answers "is this PI strong, well-known, and good for placement?" —
the multi-year reputation question. Recruiting health and active
funding moved out to **Opportunity (O)** in roadmap #6a, so A no longer
reads `pi_signal` or `active_funding_quality`.

```
A_raw = 0.40 · influence_percentile  (h-index proxy)
      + 0.30 · elite_status          (NAS / HHMI / NAE / field-specific fellow)
      + 0.30 · grad_placement_quality
```

`A` then maps 0–1 → 4.0 via the same `raw_to_4_0` buckets as C. A new
PI without placement record will score lower on A — by design. Their
strengths (active grants, growing lab, recruiting openings) belong in
O.

### 4c. Opportunity (O) — admit-cycle availability, post-roadmap-#6a

O is the orthogonal "is this PI taking students this cycle, with
funding, with capacity, with an open application path?" question.
**O is NOT in `match_score`** — it does not enter CAPEG. Instead, O
derives `opportunity_adj` which **replaces the v1 `pi_adj` term**
inside `application_strength`:

```
v1: application_strength = clip(match + pi_adj, 0, 4.0)
v2: application_strength = clip(match + opportunity_adj, 0, 4.0)
```

```
O_raw = clip(
    0.30 · recruiting_health(pi_signal)
  + 0.30 · active_funding_quality
  + 0.20 · lab_capacity(open_positions, current_count, recent_grads)
  + 0.10 · funding_timing(grant_end_years)
  + 0.10 · availability(sabbatical_or_admin_load)
, 0, 1)
```

`opportunity_adj` ladder (replaces pi_adj):

| condition | adj |
|-----------|-----|
| `not_recruiting` | force application_strength = 0 |
| O ≥ 0.70 | +0.2 |
| O ≥ 0.50 |  0.0 |
| O ≥ 0.30 | −0.2 |
| O < 0.30 | −0.4 |

Pure-legacy candidates (no `opportunity_signal`) use the v1 PI_ADJ
table verbatim — preserving exact old behavior. Candidates with
`opportunity_signal` get the field-by-field-merged O score → adj.

See [`references/opportunity.md`](../references/opportunity.md) for the
full schema, sub-component formulas, and migration semantics.

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
application_strength = clip(match + opportunity_adj, 0, 4.0)
```

Post-roadmap-#5: school-tier difficulty no longer enters
`application_strength` directly. Its admit-rate role moved into
`program_difficulty_penalty`'s `school_tier_admit_rate_factor`
component, and the matcher now exposes
`difficulty_adjusted_strength = risk_adjusted_strength − penalty` as
the primary sort key. See [`references/program_profile.md`](../references/program_profile.md).

Post-roadmap-#6a: `pi_adj` is replaced by `opportunity_adj`, derived
from the new Opportunity (O) score (see §4c above). `not_recruiting`
still forces `application_strength = 0`. Pure-legacy candidates
(no `opportunity_signal`) use the v1 PI_ADJ table verbatim:

| PI signal (legacy) | pi_adj (preserved) |
|--------------------|--------------------|
| strong (≥2 new PhDs/yr) | +0.2 |
| normal (1–2/yr) | 0 |
| shrinking (<1/yr) | −0.4 |
| missing data | −0.1 |
| not_recruiting | force to 0 |

Migrated candidates with `opportunity_signal` get the richer
`opportunity_adj` derived from the full O composite — see
[`references/opportunity.md`](../references/opportunity.md).

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

`risk_adjusted_strength` is an **intermediate** between
`application_strength` and the actual primary sort key
`difficulty_adjusted_strength` (defined in the next section). It bakes
the evidence-coverage band into the score:

```
risk_adjusted_strength = application_strength − confidence_band / 2
```

Half the band is subtracted as a downside discount. A well-sourced 3.0 ±0.2
candidate (risk-adjusted 2.9) outranks a loosely-claimed 3.2 ±0.8 candidate
(risk-adjusted 2.8). This means **the agent literally can't get a top rank
by writing nice numbers without sources** — the band would widen and the
risk-adjusted score would drop. The program-difficulty layer (post-#5)
then subtracts further; see the next section.

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
| `application_strength` | `clip(match_score + opportunity_adj, 0, 4.0)` (NOT a probability; `opportunity_adj` replaces v1 `pi_adj` post-#6a) |
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
  is capped at `min(0.10, n / 100)` (i.e. 100 alphabetical-author papers
  to even reach 0.10 of an edge), while `small_team_coauthor_5y`
  saturates at 1.0. The v2 cap was tightened from v1's 0.4 after the
  ATLAS / CMS-scale recalibration; rationale in
  [`references/connection_v2.md`](../references/connection_v2.md).
- **Tier-adaptive weights**: top-10 schools care more about your network
  and pubs; top-60+ weight GPA more.
- **Output-dominant Experience**: just being in a famous lab without
  producing matters less than producing something tangible.
- **Program difficulty as a separate layer (post-#5)**: top-10 PhD
  programs reject ~90–95% of applicants — but admit-rate isn't the only
  axis (cohort size, rotation vs direct-admit, funding model, faculty
  count, international friendliness all matter). v2 captures this as
  `program_difficulty_penalty` (0–0.8) on
  `difficulty_adjusted_strength`, replacing v1's flat tier-based
  `tier_adj` in `application_strength`. School_tier alone gives
  `top_10=0.70 / top_11_30=0.50 / top_31_60=0.30 / top_60+=0.00`; a
  filled `program_profile` refines this. Full schema in
  [`references/program_profile.md`](../references/program_profile.md).
- **Risk-adjusted ranking**: evidence has to drive ranking, not just
  decorate it. Wide bands move candidates down the list.
- **Paper status weights**: `published` / `accepted` get full credit;
  `submitted` / `preprint` 0.7×; `in_prep` 0.3×. Honesty about pipeline
  maturity affects scoring.
