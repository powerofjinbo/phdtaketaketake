# Opportunity (roadmap #6a)

Time-sensitive admit-cycle availability — split off from the A pillar
(post-#6a, A is reputation-only). The matcher derives `opportunity_adj`
from the OpportunitySignal and **uses it to replace the v1 `pi_adj`
term** inside `application_strength`.

```
v1: application_strength = clip(match_score + pi_adj, 0, 4.0)
v2: application_strength = clip(match_score + opportunity_adj, 0, 4.0)
```

`match_score` itself is unchanged — still CAPEG. Opportunity affects
"申请可行性" (admit-cycle viability), not "学术匹配" (academic fit).

## A vs O — the split, written hard

| | A (Advisor Influence) | O (Opportunity) |
|--|--|--|
| Question | "Is this PI strong / well-known / good for placement?" | "Is this PI taking students this cycle, with funding, with capacity, with an open application path?" |
| Time horizon | Multi-year reputation | Current admit cycle |
| Components | influence_percentile (h-index proxy) · elite_status · grad_placement_quality | recruiting_health · active_funding_quality · lab_capacity · funding_timing · availability |
| In match_score | yes (A pillar of CAPEG) | no — feeds application_strength via opportunity_adj |
| Reads pi_signal | **NO** (post-#6a) | yes |
| Reads active_funding_quality | **NO** (post-#6a) | yes |

The split is **load-bearing**: a famous emeritus PI on sabbatical with no active grants ranks high on A, low on O. A new assistant prof with active R01 and 2 open positions ranks low on A, high on O. The result card surfaces both.

## OpportunitySignal schema

Embedded on `CandidateAdvisor.opportunity_signal`. All fields optional;
default state means "didn't check". Each scoring-relevant set field
needs evidence with `supports_fields=["opportunity:<field>"]` for strict
mode. Legacy `evidence["pi_signal"]` and
`evidence["active_funding_quality"]` (top-level on `CandidateAdvisor`,
with `supports_fields=["pi_signal" | "active_funding_quality"]`) are
also accepted for migration.

```jsonc
"opportunity_signal": {
  "pi_signal": "strong",                  // mirrors legacy CandidateAdvisor.pi_signal

  "lab_open_positions": 2,
  "current_student_count": 6,
  "recent_phd_graduations": 2,

  "active_funding_quality": 0.85,         // mirrors legacy CandidateAdvisor.active_funding_quality
  "grant_end_years": 4,                   // years of guaranteed funding remaining

  "sabbatical_or_admin_load": false,
  "application_contact_policy": "email_first",   // email_first | apply_through_program | do_not_contact | unknown

  "evidence": {
    "lab_open_positions": {
      "items": [{
        "url": "https://lab.example/open-positions",
        "source_type": "lab_page",
        "claim": "Lab page lists 2 open PhD positions for Fall 2026",
        "supports_fields": ["opportunity:lab_open_positions"]
      }]
    }
  }
}
```

## Field-by-field merge with legacy top-level

When `opportunity_signal` is present, the matcher applies a **field-by-
field merge** (not object-level override) so a partially-migrated JSON
doesn't lose information:

```
effective_pi_signal =
  opportunity_signal.pi_signal   if it != "missing"
  else CandidateAdvisor.pi_signal

effective_active_funding_quality =
  opportunity_signal.active_funding_quality   if it is not None
  else CandidateAdvisor.active_funding_quality
```

When `opportunity_signal` is **None**, the matcher takes a pure-legacy
path: `opportunity_adj = LEGACY_PI_ADJ[pi_signal]` (the v1 table
verbatim). This preserves exact old behavior for unmigrated JSON and
existing tests.

## opportunity_score formula

```
O_raw = clip(
    0.30 · recruiting_health(effective_pi_signal)
  + 0.30 · effective_active_funding_quality_or_neutral
  + 0.20 · lab_capacity(open_positions, current_student_count, recent_phd_graduations)
  + 0.10 · funding_timing(grant_end_years)
  + 0.10 · availability(sabbatical_or_admin_load)
, 0, 1)
```

| Sub-signal | Mapping |
|------------|---------|
| `recruiting_health(pi_signal)` | strong=1.0 · normal=0.7 · missing=0.5 · shrinking=0.3 · not_recruiting=0.0 |
| `active_funding_quality` | use value if set; None → 0.5 (neutral — "didn't check") |
| `lab_capacity` | average of three sub-signals: `open_positions ≥1 → 1.0 / =0 → 0.3 / None → 0.5` · `current_student_count` (0→0.3, 1–2→0.6, 3–10→1.0, 11–20→0.85, >20→0.6, None→0.5) · `recent_phd_graduations` (≥2→1.0, =1→0.7, =0→0.4, None→0.5) |
| `funding_timing(grant_end_years)` | None=0.5 · ≥4=1.0 · 2–3=0.8 · 1=0.4 · 0=0.2 |
| `availability(sabbatical_or_admin_load)` | False=1.0 · None=0.5 · True=0.2 |

Components for which the agent didn't check default to **neutral 0.5**
(not 0). Missing data shouldn't be treated as verified-zero — the band
already carries that uncertainty.

## opportunity_adj ladder

```
not_recruiting → force application_strength = 0
O ≥ 0.70 → +0.2
O ≥ 0.50 →  0.0
O ≥ 0.30 → −0.2
O <  0.30 → −0.4
```

Mirrors the v1 PI_ADJ magnitudes (+0.2 / 0 / −0.2 / −0.4) so candidates
with rich opportunity data fall into roughly the same bucket as v1
pi=strong / normal / shrinking-partial / shrinking-full. Pure-legacy
candidates use the v1 table verbatim (`LEGACY_PI_ADJ`); migrated
candidates with rich data can earn or lose the boost based on the full
O composite.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.** Component weights and ladder cutoffs are educated
> guesses, not load-bearing magnitudes.

## A's new formula (post-#6a)

```
A_raw = 0.40 · influence_percentile  (h-index proxy)
      + 0.30 · elite_status          (NAS / HHMI / NAE / field fellow)
      + 0.30 · grad_placement_quality
```

A no longer reads `active_funding_quality` (moved to O). A no longer
reads `pi_signal` (moved to O). A is now strictly reputation / field
standing / placement record. Tests `test_advisor_strength_excludes_funding`
and `test_advisor_strength_excludes_recruiting` pin this invariant.

A new PI without a placement record will score lower on A. That's
acceptable — a new PI's strengths (active grants, growing lab,
recruiting openings) belong in O, not A. The user can still see both
on the result card; the strategy layer (roadmap #7) can interpret
"high-O low-A" as "promising but unproven" vs "low-O high-A" as
"established but currently inaccessible".

## Evidence — legacy required vs new opt-in

| Field | Coverage entry | Where evidence may live |
|-------|----------------|-------------------------|
| `pi_signal` (legacy required)              | `pi_signal` | `candidate.evidence["pi_signal"]` (legacy) **OR** `opportunity_signal.evidence["pi_signal"]` (new namespace) |
| `active_funding_quality` (legacy required) | `active_funding_quality` | `candidate.evidence["active_funding_quality"]` (legacy) **OR** `opportunity_signal.evidence["active_funding_quality"]` (new namespace) |
| `lab_open_positions` (opt-in) | `opportunity:lab_open_positions` | only `opportunity_signal.evidence["lab_open_positions"]` |
| `current_student_count` | `opportunity:current_student_count` | only `opportunity_signal.evidence["current_student_count"]` |
| `recent_phd_graduations` | `opportunity:recent_phd_graduations` | only `opportunity_signal.evidence["recent_phd_graduations"]` |
| `grant_end_years` | `opportunity:grant_end_years` | only `opportunity_signal.evidence["grant_end_years"]` |
| `sabbatical_or_admin_load` | `opportunity:sabbatical_or_admin_load` | only `opportunity_signal.evidence["sabbatical_or_admin_load"]` |
| `application_contact_policy` | `opportunity:application_contact_policy` | only `opportunity_signal.evidence["application_contact_policy"]` |

Opt-in fields use the **`opportunity:<field>` namespace** in
`supports_fields`. Strict-mode rejection error directs the agent at
`opportunity_signal.evidence['<field>']`.

Legacy-required fields keep their original coverage names so existing
tests / older JSON keep working unchanged. The hint message now
mentions both locations and both supports_fields forms (legacy
`["pi_signal"]` or new `["opportunity:pi_signal"]`).

## Sort key (post-roadmap-#6a — unchanged from #5)

The new opportunity scoring does NOT touch the sort-key ladder. It
flows into `application_strength` → `risk_adjusted_strength` →
`difficulty_adjusted_strength` like before.

```
descending priority (post-#5, unchanged by #6a):
  1. difficulty_adjusted_strength
  2. risk_adjusted_strength
  3. research_fit_score              (None → -∞)
  4. direction_relevance
  5. application_strength
  6. lower_bound
```

## Why O isn't part of CAPEG (yet)

Adding O as a 6th pillar would require recalibrating all
`TIER_WEIGHTS` and would entangle time-sensitive availability with
multi-year fit. The current design — O as an `application_strength`
adjustment — keeps `match_score` clean (CAPEG = academic / network
fit only) while still letting opportunity data move the ranking
through `application_strength → risk_adjusted → difficulty_adjusted`.

If real-portfolio calibration shows O needs more weight, the upgrade
path is: keep current behavior, add an explicit O pillar with
`TIER_WEIGHTS["O"]` = 0.05–0.10 (small, bounded so it never outranks
C / A / P / E / G structural fit). For now, the application-strength-
adjustment form is the simpler v1.
