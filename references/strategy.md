# Strategy explainer (Sprint-2-c5 / Roadmap-#7)

Per-candidate `StrategyRecommendation` + portfolio-level
`StrategySummary`. Sits **on top** of scoring and is purely derivative —
does NOT modify any scoring field. Pinned by
`test_strategy_does_not_change_scores`.

> The strategy report is a **decision memo**, not a "score → label"
> mapping. Hard risks (not_recruiting, ≥3 unsourced claims, very low
> fit) override high nominal scores via bucket precedence.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.**

## Apply buckets (precedence: drop → only_if_space → reach → target → priority)

First-match wins. Hard risks check first; only candidates that survive
every drop / only_if_space / reach guard land in target / priority.

| Bucket | Triggers (any one is sufficient) |
|--------|----------------------------------|
| `drop` | `pi_signal == "not_recruiting"`; OR `unsourced_signals >= 3`; OR `research_fit_score is not None AND < 0.20`; OR `risk_adjusted_strength < 1.50` |
| `only_if_space` | `risk_adjusted_strength < 2.00`; OR `missing_signals >= 5`; OR `lower_bound < 1.60`; OR no verified path AND no strong fit |
| `reach` | `application_strength >= 2.40 AND risk_adjusted_strength < 2.40` (high nominal + wide band) |
| `target` | `risk_adjusted_strength >= 2.30 AND unsourced_signals <= 2 AND (strong C OR strong fit OR strong A)` |
| `priority` | All target requirements + `risk_adjusted_strength >= 2.70 AND unsourced_signals == 0 AND lower_bound >= 2.30 AND (strong C OR strong fit)` |

"Strong C" = `c_score >= 3.7`. "Strong fit" = `research_fit_score >= 0.65`.
"Strong A" = `a_score >= 3.3`.

## Recommended actions

| Action | When |
|--------|------|
| `skip` | bucket == drop |
| `contact_first` | strong C verified (regardless of bucket); OR (priority/target + strong fit) |
| `investigate_evidence` | unsourced claims exist AND no strong C |
| `deprioritize` | only_if_space AND no strong C |
| `apply` | otherwise (priority/target/reach with no unsourced; or reach without strong C) |

The "strong C overrides bucket" rule reflects the connection-first
thesis: a verified direct connection (5+ small-team coauthored papers,
shared grant, co-mentored student, etc.) is the load-bearing reason to
apply. Even with 5+ missing signals or a wide band, if the connection
itself is verified, the user should reach out personally rather than
defer.

## StrategyRecommendation schema

```jsonc
{
  "apply_bucket": "target",                // priority/target/reach/only_if_space/drop
  "recommended_action": "contact_first",   // apply/contact_first/investigate_evidence/deprioritize/skip
  "why_this_rank": [
    "risk_adjusted_strength=2.81 ≥ 2.30",
    "strong connection (C=4.00)"
  ],
  "main_risks": [
    "wide confidence band (±0.6) — true strength may be 2.21–3.41"
  ],
  "evidence_to_fix": [
    "school_tier",
    "active_funding_quality"
  ],
  "outreach_angle": "Lead with the shared small-team coauthorship with adv_001 (5 papers) as the connection.",
  "next_steps": [
    "Email the PI; mention the sourced connection above.",
    "Optionally tighten 4 missing signal(s) for a narrower band."
  ]
}
```

## StrategySummary (portfolio-level)

```jsonc
{
  "priority_candidates": ["cand_001", "cand_004"],
  "target_candidates": ["cand_002"],
  "reach_candidates": ["cand_003"],
  "only_if_space_candidates": ["cand_005"],
  "drop_candidates": ["cand_006"],
  "evidence_fix_queue": [
    { "candidate_id": "cand_001", "signal": "school_tier", "severity": "high" },
    { "candidate_id": "cand_002", "signal": "active_funding_quality", "severity": "medium" }
  ],
  "portfolio_notes": [
    "6 candidates: 2 priority · 1 target · 1 reach · 1 only_if_space · 1 drop"
  ]
}
```

The fix queue is sorted **high severity first** (unsourced before
missing) so the user knows what to repair before re-running the matcher.

## Outreach angle generation

The strategy explainer never invents claims. It uses ONLY:

- A verified path edge (small_team_coauthor / co_mentored_student /
  shared_grant / same_working_group / analysis_contact / same_advisor
  genealogy)
- A sourced `research_fit_summary` with `research_fit_score >= 0.50`

If neither is available, `outreach_angle` is `null` and `next_steps`
adds "Read 2 recent papers before contacting" so the user doesn't email
cold without context.

## What strategy does NOT do

- It does NOT modify `match_score`, `application_strength`,
  `risk_adjusted_strength`, `difficulty_adjusted_strength`, or
  `research_fit_score`. Pinned by `test_strategy_does_not_change_scores`.
- It does NOT predict admission probability. Buckets are about how the
  user should triage their own application time, not about admit odds.
- It does NOT replace `audit_candidates.py` — the audit CLI is for
  pre-match evidence repair; strategy is post-match decision support.
- It does NOT generate full SOP / cover-letter text. `outreach_angle`
  is a one-line lead the user should expand themselves.

## CLI integration

`scripts/match.py` now emits:

```jsonc
{
  "input_field": "physics",
  "field_profile_id": "physics",
  "input_warnings": [...],
  "strategy_summary": {
    "priority_candidates": [...],
    "target_candidates":   [...],
    ...
  },
  "results": [
    {
      "candidate": {...},
      "match_score": 3.49,
      "application_strength": 3.10,
      "difficulty_adjusted_strength": 2.81,
      "strategy": {
        "apply_bucket": "target",
        "recommended_action": "contact_first",
        ...
      }
    }
  ]
}
```

Per-candidate `strategy` is automatically attached by `compute_match`;
top-level `strategy_summary` is the portfolio rollup.
