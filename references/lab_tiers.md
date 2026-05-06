# Lab prestige tier reference

`lab_tier` is the prestige bucket of the **PI** the student worked with for a
research experience. It feeds the Experience score (E) — `lab_tier` weight is
0.20, with `duration_months` (0.30) and `output_type` (0.50) as the other
two factors.

## The 6 tiers

| `lab_tier` | Score | Criteria |
|------------|-------|----------|
| `world_class` | 4.0 | HHMI investigator · Max Planck director · NAS / NAE member · Top 10 US program PI · National lab leadership (LBNL, ANL, FNAL, BNL, ORNL, JPL, NCAR, NIST, NIH intramural) · Equivalent international (e.g., CERN staff scientist, ETH professor, Cambridge / Oxford prof, Riken senior PI, IAS faculty) |
| `top_us` | 3.7 | Top 11–40 US PhD program PI (per **field-specific** US News ranking) |
| `strong_us_or_top_cn` | 3.5 | Top 41–70 US PI · OR prominent / well-cited PI at Tsinghua, PKU, Fudan, SJTU, USTC, ZJU, NJU, HIT, HUST (C9-or-equivalent named PI) |
| `good_us_or_985` | 3.0 | Top 71–100 US PI · OR average PI at a 985 university (not a flagship name) |
| `211_or_overseas` | 2.5 | 211 (non-985) Chinese university PI · OR overseas regular university PI (e.g., national university in mid-tier ranking) |
| `other` | 2.0 | Anything else — small college, industry research with no academic affiliation, undergraduate-only institutions |

## Calibration heuristics

The tier reflects the **prestige of the PI within their field**, not the
overall name recognition of their institution. Some examples:

- A famous immunologist at U Florida (top 50 US for biology overall, top 10 for
  some immunology subfields) → `top_us` if the immunology program ranks
  top 11–40, possibly `world_class` if PI is HHMI.
- A mid-career PI at MIT working in a small subfield → `world_class` (Top 10 US,
  reputation carries) regardless of personal h-index.
- A famous Chinese material scientist at Tsinghua → `strong_us_or_top_cn`
  (the entry covers top Chinese flagship PIs).
- A young assistant prof at U Wisconsin in a top-15 subfield → `top_us`.

## When the PI's tier isn't obvious

Ask the user: *"Was your PI a department chair, named professor, NSF
CAREER awardee, NAS member, etc.?"* — these signals quickly disambiguate
between tiers.

If unclear, default to `good_us_or_985` (3.0) — middle of the distribution,
conservative.

## Why `lab_tier` weight is only 0.20

Per the scoring philosophy: just being in a famous lab doesn't matter much —
**output matters more** (`output_type` weight is 0.50). A `world_class` lab
where the student only had `participation_only` output (E ≈ 0.20·4.0 + 0.30·X
+ 0.50·2.5 = 0.80 + 0.30·X + 1.25) scores much lower than a `good_us_or_985`
lab with a `paper` output (E = 0.60 + 0.30·X + 1.85).

The model rewards what the student actually did, not which lab they were
adjacent to.
