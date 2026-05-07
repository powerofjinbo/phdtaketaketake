# Publication v2 (Sprint-2-c2)

Layered additions on top of the v1 (tier × position decrement)
publication scoring. v2 is **opt-in**: papers without the new fields
score exactly as in v1.

## What v2 adds

- **`recency_weight`**: scales by `year` — ≤2y → 1.0, 3–5y → 0.95,
  >5y → 0.85. `None` → 1.0 (no penalty for unspecified year).
- **`contribution_role`** + bonus: when set with verified
  `contribution_evidence`, adds +0.05 to +0.15 to the paper score.
- **Big-collab guardrail**: when `total_authors > field threshold` AND
  no verified contribution_role, paper caps at `BIG_COLLAB_GUARDED_FLOOR
  = 3.5`.
- **Consortium guardrail**: `author_role="consortium"` without verified
  contribution_role caps at `0.45 × baseline` (heavily discounted).
- Field-aware **`paper_status_weight_overrides`** populated for cs
  (`preprint=0.85`) and biology (`preprint=0.75`); math's existing
  `preprint=0.9` preserved.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.**

## Schema additions

```jsonc
{
  "journal_tier": 1,
  "author_position": 4,
  "status": "published",

  // v2 additions (all optional)
  "year": 2026,
  "total_authors": 312,
  "author_role": "middle",                  // also covers "consortium" guardrail
  "contribution_role": "lead_analysis",     // lead_analysis / method_developer / data_collection / writing / unclear
  "contribution_evidence": [{
    "url": "https://atlas-glance.cern.ch/.../analysis-contacts",
    "source_type": "lab_page",
    "claim": "listed as primary analysis contact for this paper",
    "supports_fields": ["contribution_role"]
  }],

  // Stored only — reserved for future field-norm scoring
  "citations_optional": 142,
  "field_normalized_impact": 0.85
}
```

## Scoring formula (v2)

```
base   = (baseline − decrement[pos])   if pos ≤ 4
       = min(BIG_COLLAB_FLOOR, baseline − decrement[4])   if pos ≥ 5

base  *= status_weight(status, field_profile)             # v1
base  *= recency_weight(year, current_year)               # v2

if NOT verified_contribution:
    if total_authors > field_profile.big_collab_threshold:
        base = min(base, BIG_COLLAB_GUARDED_FLOOR)        # v2
    if author_role == "consortium":
        base = min(base, 0.45 × baseline)                 # v2

base += contribution_bonus(role)                          # v2 (+0.05 to +0.15)
return min(base, baseline)                                # final cap
```

## Contribution bonus table

| `contribution_role` | Bonus (when verified) |
|---------------------|-----------------------|
| `lead_analysis`     | +0.15 |
| `method_developer`  | +0.10 |
| `data_collection`   | +0.05 |
| `writing`           | +0.05 |
| `unclear`           | 0.00 |

`verified` means `contribution_evidence` has at least one item. An
unverified role is informational only — no bonus and no guardrail
bypass. `validate_paper_contributions(papers)` warns on unverified roles
so the agent can either gather evidence or remove the role claim.

## Recency multiplier

| Gap (years) | Multiplier |
|-------------|------------|
| ≤ 2 | 1.00 |
| 3–5 | 0.95 |
| > 5 | 0.85 |
| `year=None` | 1.00 |
| Future year (data error) | 1.00 |

## Big-collab guardrail

When `total_authors > field_profile.big_collab_threshold` AND no
verified `contribution_role`, the paper is capped at
`BIG_COLLAB_GUARDED_FLOOR = 3.5`. This prevents a candidate from
booking 1st-author equivalent credit for being one of 312 alphabetical
authors of a tier-1 ATLAS paper without showing analysis-contact
evidence.

A verified contribution role bypasses the cap — the candidate gets the
position-derived score (which still respects the 5+ rule, capping at
`BIG_COLLAB_FLOOR = 3.5`) plus the contribution bonus.

## Consortium guardrail

When `author_role == "consortium"` AND no verified contribution role,
the paper caps at `0.45 × baseline` (1.8 for tier 1). This is a hard
discount — consortium-only authorship is a weaker signal than
big-collab middle-author position.

A verified contribution role rescues consortium-role papers back to
the position-derived score plus bonus.

## Field-aware status overrides (Sprint-2-c2)

Defaults for `paper_status_weight_overrides` per field:

| field | preprint | published / accepted / in_press | submitted | in_prep |
|-------|----------|---------------------------------|-----------|---------|
| `math`     | **0.90** | 1.00 | 0.70 | 0.30 |
| `cs`       | **0.85** | 1.00 | 0.70 | 0.30 |
| `biology`  | **0.75** | 1.00 | 0.70 | 0.30 |
| (other)    | 0.70 (default) | 1.00 | 0.70 | 0.30 |

CS preprints often correspond to NeurIPS / ICML camera-ready papers
in the months between acceptance and conference. Biology bioRxiv
preprints are typically under journal review. Math arXiv is often
the canonical record (existing override from Sprint-1).

## How to use

1. **Always set `year`** when you have it — recency decay applies.
2. **Set `total_authors`** for big-collab fields — without it, the
   guardrail cannot trigger.
3. **Use `contribution_role` + `contribution_evidence`** when the
   candidate has a verified role on a big-collab paper. Without the
   evidence, the role is informational only.
4. **Don't game the bonus**: the matcher's `paper_score` caps at
   baseline, so adding `lead_analysis +0.15` to an already-tier-1
   1st-author paper has no effect. The bonus only matters when
   the paper would otherwise be guardrailed or below baseline.
