# Program difficulty (roadmap #5)

Per-program signals that refine raw `school_tier` into a richer
difficulty estimate. Replaces the v1 `tier_adj` term that lived inside
`application_strength`.

The matcher's **primary sort key** is now
`difficulty_adjusted_strength = max(0, risk_adjusted_strength −
program_difficulty_penalty)`, and the 5-tier label is applied to that
value (not to the raw `application_strength`).

## ProgramProfile schema

Embedded on `CandidateAdvisor.program_profile`. All fields optional;
each non-default field that contributes to the penalty needs a matching
entry in `program_profile.evidence` with
`supports_fields=["program:<field>"]` for strict mode.

```jsonc
"program_profile": {
  "department": "Physics",

  "admission_model": "rotation",       // direct_admit | rotation | centralized | mixed | unknown
  "rotation_supported": true,
  "direct_admit_required": false,
  "gre_required": false,
  "application_deadline": "2026-12-15",

  "cohort_size_estimate": 18,
  "faculty_count_in_area": 6,
  "international_friendliness": 0.7,    // [0, 1]

  "funding_structure": "guaranteed",    // guaranteed | pi_grant | fellowship_first | mixed | unknown

  "program_selectivity_score": 0.85,    // [0, 1] — overall acceptance-rate proxy

  "evidence": {
    "cohort_size_estimate": {
      "items": [{
        "url": "https://physics.example.edu/admissions/...",
        "source_type": "lab_page",
        "claim": "department admits ~18 PhDs/yr (2023 admissions report)",
        "supports_fields": ["program:cohort_size_estimate"]
      }]
    }
  }
}
```

## program_difficulty_penalty formula

```
penalty = clip(
    school_tier_admit_rate_factor +    # see table
    cohort_factor +
    admission_factor +
    funding_factor +
    area_factor +
    intl_factor
, 0.0, 0.8)
```

Each component:

| Component | Trigger | Δ |
|-----------|---------|---|
| `school_tier_admit_rate_factor` | `school_tier == "top_10"`        | **+0.70** |
|                                  | `top_11_30`                      | +0.50 |
|                                  | `top_31_60`                      | +0.30 |
|                                  | `top_60_plus`                    | 0.00 |
| `cohort_factor`                   | `cohort_size_estimate < 8`       | +0.10 |
|                                   | `cohort_size_estimate ≥ 30`      | −0.05 |
| `admission_factor`                | `direct_admit` OR `direct_admit_required=True` | +0.10 |
|                                   | `rotation` OR `centralized`      | −0.05 |
| `funding_factor`                  | `pi_grant`                       | +0.10 |
|                                   | `guaranteed`                     | −0.05 |
| `area_factor`                     | `faculty_count_in_area ≤ 1`      | +0.10 |
|                                   | `faculty_count_in_area ≥ 5`      | −0.05 |
| `intl_factor`                     | `international_friendliness < 0.3` | +0.05 |

Result clipped to `[0.0, 0.8]`.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.** The component weights are educated guesses, not load-
> bearing magnitudes.

## Calibration shifts vs v1

- Top_10 perfect 4.0 candidate, normal recruiting, 0 unverified:
  - v1: `application_strength = 4.0 − 1.0 = 3.0` → **Match**
  - v2: `app_strength = 4.0`, `risk_adj = 3.9`, `diff_adj = 3.9 − 0.70 = 3.20` → **Match**

- Top_60+ 3.5-nominal candidate, normal recruiting, 0 unverified:
  - v1: `application_strength = 3.5 + 0.4 = 3.9` → **Safe**
  - v2: `app_strength = 3.5`, `risk_adj = 3.4`, `diff_adj = 3.4 − 0.0 = 3.40` → **Match**

The v1 +0.4 boost for top_60+ is dropped intentionally — it overstated
how much "easier" low-tier programs are. Recalibrate against real
portfolios if the shift turns out wrong.

## Evidence and strict mode

Each scoring-relevant program field that's set (non-`None`,
non-`"unknown"`) enters `evidence_coverage` as the namespaced signal
`program:<field_name>`. The fields are:

- `cohort_size_estimate`
- `admission_model`
- `funding_structure`
- `faculty_count_in_area`
- `international_friendliness`

In strict mode, each set value needs an item in
`program_profile.evidence[<field>]` with
`supports_fields=["program:<field>"]`. The strict-mode error points
the agent at the right location:

```
candidate=cand_001 unsourced claim: program:funding_structure —
  program_profile.evidence['funding_structure'].items must include an
  EvidenceSource with supports_fields containing
  'program:funding_structure' (cite the department's admissions /
  cohort / funding page, an alumni report, or a faculty-listing page
  that backs the specific program signal)
```

Unset fields (`None` / `"unknown"`) don't enter coverage — same
opt-in pattern as research_fit. A null program_profile means "no
program-level data was collected"; only the school_tier component
contributes.

## Sort-key ladder (post-roadmap-#5)

```
descending priority:
  1. difficulty_adjusted_strength = risk_adjusted_strength − program_difficulty_penalty   ← primary
  2. risk_adjusted_strength
  3. research_fit_score   (None → −∞; tie-breaker only)
  4. direction_relevance
  5. application_strength (raw)
  6. lower_bound
```

Why diff_adj is primary: program difficulty is structural (not just
nominal CAPEG performance) and the user is choosing where to spend
years of their life. A "perfect candidate at a tiny direct-admit
program with PI-grant funding" should not look the same as a "perfect
candidate at a broad rotation program with guaranteed funding" — the
realistic admission and survival differ.

Research fit remains a pure tie-breaker (rank 3) — fits between
risk-adjusted strength and direction relevance, never overriding
difficulty-adjusted.

## What's deferred to v2 commit 2 (Opportunity / A refactor)

`program_difficulty_penalty` does NOT include `pi_signal` — that signal
already enters `application_strength` via `pi_adj`. The next commit
extracts recruiting-related fields out of the A pillar into a separate
**Opportunity** signal, at which point `pi_adj` and adjacent recruiting
data will get reorganized cleanly. For now: pi_adj stays where it was,
program penalty owns the school + cohort + funding + area dimensions.
