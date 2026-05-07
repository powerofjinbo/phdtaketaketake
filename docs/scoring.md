# Scoring formulas — v0.3

> All four dimensions on a 4.0 scale (matching GPA), then weighted by school tier.

## Dimensions

### 1. Pub Score (P)

Score per paper:

- **Position 1–4**: `baseline(tier) − decrement(position)`
  - Decrements: `0, 0.10, 0.25, 0.45`
- **Position 5+**: `min(3.5, baseline(tier) − 0.45)`
  - Top-tier 5+ author → 3.5 (big-collab credit, e.g., ATLAS/CMS)
  - Lower-tier 5+ author → 4-author score (no inversion)

Tier baselines:

| Tier | Baseline | Examples |
|------|----------|----------|
| S | 4.0 | Nature, Science, Cell |
| 1 | 4.0 | PRL, JACS, Nat Materials |
| 2 | 3.7 | PRX, Adv Materials, Nano Letters |
| 3 | 3.3 | PRD, Chem Mater, J Mater Chem A |
| 4 | 2.8 | PR Applied, J Appl Phys |
| 5 | 2.3 | weak SCI / workshops |
| retracted | 0 | predatory / retracted |

**Multi-paper aggregation** (top-3 weighted):
- 0 papers → `3.0` (floor)
- 1 paper → that paper's score
- 2 papers → `0.7 · best + 0.3 · 2nd_best`
- 3+ papers → `0.5 · best + 0.3 · 2nd + 0.2 · 3rd` (only top-3 used)

### 2. GPA Score (G)

| Scale | Conversion |
|-------|-----------|
| 4.0 | direct (capped at 4.0) |
| 4.3 | `min(GPA × 4.0/4.3, 4.0)` |
| 4.5 | `min(GPA × 4.0/4.5, 4.0)` |
| Chinese 100 | bucket table (≥90→4.0, 85–89→3.7, 80–84→3.3, 75–79→3.0, 70–74→2.7, 65–69→2.3, <65→2.0) |
| UK honours | First→3.8, High 2:1→3.5, Low 2:1→3.2, 2:2→2.8, Third→2.3 |

When student provides both major and cumulative: use `max(major, cumulative)`.

### 3. Experience Score (E)

```
E = 0.20 · lab_prestige + 0.30 · duration + 0.50 · output
```

Take **strongest** single experience, no stacking.

**Lab prestige** (6 tiers):

| Tier | Score | Examples |
|------|-------|----------|
| `world_class` | 4.0 | HHMI / Max Planck / NAS member / Top 10 US PI |
| `top_us` | 3.7 | Top 11–40 US PI |
| `strong_us_or_top_cn` | 3.5 | Top 41–70 US PI / Tsinghua, PKU, C9 prominent |
| `good_us_or_985` | 3.0 | Top 71–100 US / 985 regular |
| `211_or_overseas` | 2.5 | 211 / overseas regular |
| `other` | 2.0 | rest |

**Duration**: ≥24mo→4.0, 12–24mo→3.5, 6–12mo→3.0, 3–6mo→2.5, <3mo→2.0

**Output**: paper→3.7 (already counted in P), oral→3.7, poster→3.3, thesis→3.0, participation only→2.5

### 4. Connection Score (C) — per (student, candidate) pair

This is the IP. Computed pairwise.

**Path strength** between *student's current advisor* and *candidate*: max over edge types (no stacking).

| Edge type | Strength formula |
|-----------|------------------|
| Co-author (5-yr) | `min(1.0, paper_count / 5)` |
| Academic genealogy | same advisor=1.0, uncle/nephew=0.7, two-hop=0.4 |
| Joint collaboration | ≥5y=1.0, 1–5y=0.6, <1y=0.3 |
| Committee / editorial | same period=0.8, different period=0.3 |

**Field strength** (candidate's own network, advisor-independent):
```
C_field = 0.4 · normalized_collab_top20pct
        + 0.3 · collab_with_NAS_or_HHMI
        + 0.3 · grad_placement_quality
```

**Composite**:
```
C_raw = 0.6 · max_path_strength + 0.4 · C_field
```

If student has no current advisor: `C_raw = C_field`.

**0–1 → 4.0 mapping**: ≥0.8→4.0, 0.6–0.8→3.7, 0.4–0.6→3.3, 0.2–0.4→2.8, <0.2→2.3

## Final scores

### Match score (tier-adaptive)

```
match = w_C · C + w_P · P + w_E · E + w_G · G
```

| School tier | w_C | w_P | w_E | w_G |
|-------------|-----|-----|-----|-----|
| Top 10 | 0.45 | 0.30 | 0.15 | 0.10 |
| Top 11–30 | 0.40 | 0.30 | 0.15 | 0.15 |
| Top 31–60 | 0.35 | 0.25 | 0.20 | 0.20 |
| Top 60+ | 0.30 | 0.20 | 0.20 | 0.30 |

### Application strength

> **Important**: `application_strength` is **NOT a probability**. It's a
> 4.0-scale relative-fit index. There's no historical admission data behind
> it — calibration is qualitative, based on realistic admission-rate ratios
> across school tiers. The label (Reach / Target / Match / Safe / Far Reach)
> communicates relative competitiveness, not literal odds.

```
application_strength = clip(match + tier_adj + pi_adj, 0, 4.0)
```

| School tier | tier_adj |
|-------------|----------|
| Top 10 | **−1.0** |
| Top 11–30 | **−0.5** |
| Top 31–60 | 0 |
| Top 60+ | **+0.4** |

These reflect realistic admission-rate ratios (top-10 PhD programs admit
~5–10%; top-60+ admit ~25–35% — a 4–8× gap). A perfect 4.0 candidate at MIT
lands at application_strength ~ 3.0 (`Match`), not `Safe` — which is honest:
even a flawless profile is uncertain at the most selective programs.

| PI signal | pi_adj |
|-----------|--------|
| strong (≥2 new PhDs/yr) | +0.2 |
| normal (1–2/yr) | 0 |
| shrinking (<1/yr) | −0.4 |
| missing data | −0.1 |
| not recruiting | force to 0 |

**Confidence band** (4.0 scale, driven by evidence coverage):

| Unverified count | Band |
|------------------|------|
| 0 (everything sourced) | ±0.2 |
| 1–2 | ±0.4 |
| 3–4 | ±0.6 |
| 5+ (mostly unsourced) | ±0.8 |

A signal counts as unverified unless its `EvidenceEntry.sources` (or
`PathEdge.sources` for connection edges) is non-empty. Default values without
sources count as unverified too — "didn't check" is treated the same as
"asserted without proof".

**5-tier label**:
- `Safe` ≥ 3.5
- `Match` 3.0–3.5
- `Target` 2.5–3.0
- `Reach` 2.0–2.5
- `Far Reach` < 2.0

## Why this design

- **Connection-first**: real PhD admissions hinge on advisor recommendations and academic-network trust. h-index doesn't capture this.
- **5+ author rule**: HEP / big-collab papers list hundreds of authors alphabetically; treating position 312 as "barely contributed" is wrong, but treating it as 1st-author equivalent is also wrong. The `min(3.5, …)` floor balances this.
- **Tier-adaptive weights**: top-10 schools care more about your network and pubs; top-60+ schools weight GPA more because applicants there typically have less polished pubs.
- **Output-dominant Experience**: just being in a famous lab without producing matters less than producing something tangible (thesis, talk, paper).
- **Steep top-10 admit penalty (−1.0)**: top-10 PhD programs reject ~90–95% of applicants. A −0.4 adjustment under-states this; the −1.0 we use forces even strong candidates to land at `Match` not `Safe` for MIT/Stanford/etc, which is honest.
- **All listed papers count**: a paper on the profile is assumed to be published / accepted / appearing on the student's CV by application time. We don't distinguish between `published` / `accepted` / `submitted` / `in preparation` — the user is responsible for only listing papers they're confident about. This keeps the schema simple; gaming it (listing speculative papers) just leaks confidence into the user's own application.

See implementation in [`phd_matcher/scoring/`](../phd_matcher/scoring/).
