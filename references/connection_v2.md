# Connection v2 — expanded network model (Sprint-2-c1)

The C pillar is the core differentiator of this skill. v1 modelled a
handful of edge types (small-team coauthorship, big-collab, working
group, analysis contact, genealogy, generic overlap, committee). v2
expands the graph with **co-mentored students**, **shared grants**,
**committee/exam overlap**, **same center/institute**, **prior-
institution overlap**, and **conference-session overlap**, adds a
**secondary bonus** so multiple verified edges can compose, and
applies a **recency multiplier** so old connections decay.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.** The recency cutoffs and edge values are educated
> guesses, not load-bearing magnitudes.

## PathEdge schema (v2 additions, additive)

```jsonc
"paths_to_advisors": {
  "adv_001": {
    // ---- v1 fields (kept) ----
    "small_team_coauthor_5y": 5,
    "big_collab_papers_5y":   12,
    "same_working_group":     true,
    "analysis_contact_overlap": false,
    "genealogy_relation":     "uncle_nephew",
    "collaboration_overlap_years": 3.0,
    "committee_co_member":    false,
    "same_period":            false,

    // ---- v2 new fields ----
    "shared_grant_count_5y":           2,        // NSF/NIH/DOE shared grants in last 5y
    "co_mentored_student_count":       1,        // jointly mentored students
    "committee_or_exam_overlap":       true,     // PhD committee / qualifying exam overlap
    "same_center_or_institute":        false,    // shared NSF ERC / NIH center / DOE lab / institute
    "prior_institution_overlap_years": 6,        // years overlapped at the same institution before current roles
    "conference_session_overlap_5y":   3,        // shared conference sessions in last 5y
    "most_recent_connection_year":     2024,     // year of last direct interaction → recency multiplier

    "items": [ /* per-claim EvidenceSource records */ ],
    "note": "..."
  }
}
```

Every set field needs evidence with `supports_fields=[<field>]` (or
one verified-empty item with `supports_fields=["path:<id>"]` for a
"searched, found nothing" path). `most_recent_connection_year` is
intentionally NOT in `fields_set()` — it's metadata derived from
already-cited evidence (e.g., the year on the last co-authored paper)
and doesn't need its own evidence row.

## Edge strength ladder

```
small_team_coauthor_5y         min(1.0, n/5)        max 1.00   (5 papers saturate)
co_mentored_student_count      min(0.90, n·0.30)    max 0.90   (3 students saturate)
shared_grant_count_5y          min(0.80, n·0.40)    max 0.80   (2 grants saturate)
same_working_group             0.75                  (verified subgroup / convener overlap)
analysis_contact_overlap       0.70                  (verified analysis-contact role on a paper)
genealogy: same_advisor        0.65                  (academic siblings)
genealogy: uncle_nephew        0.50                  (advisor's PhD sibling)
committee_or_exam_overlap      0.45                  (PhD committee / qualifying exam)
genealogy: two_hop             0.40
same_center_or_institute       0.40                  (shared NSF ERC / NIH center / DOE lab / institute)
prior_institution_overlap      min(0.35, years/10)   max 0.35
conference_session_overlap_5y  min(0.20, n·0.10)     max 0.20   (proximity, not relationship)
big_collab_papers_5y           min(0.10, n/100)      max 0.10   (alphabetical author bulk only)

# v1 (unchanged):
collaboration_overlap_years    ≥5y → 1.00; 1–5y → 0.60; <1y → 0.30
committee_co_member            same_period=true → 0.80; false → 0.30
```

## Aggregation: strongest + secondary bonus, capped at 1.0

```
edge_raw = strongest_edge + 0.10 · second_strongest_edge   (cap 1.0)
```

Why "strongest + small bonus" rather than max-only or sum:

- **Max-only** under-credits candidates with multiple medium edges
  (e.g., committee overlap + same center + prior institution).
- **Sum** over-credits weak signals stacking. A "100 ATLAS papers +
  same-conference-2x + same-center" candidate would saturate even
  though no individual edge implies a real working relationship.

The 10% secondary bonus splits the difference: a single strong edge
(small-team coauthor=5 → 1.0) saturates alone; a candidate with
analysis_contact (0.70) + same_working_group (0.75) gets 0.75 +
0.10·0.70 = 0.82 (richer than either alone but doesn't blow past
the 1.0 cap).

## Recency multiplier

After aggregation, `edge_raw` is scaled by the recency multiplier
based on `most_recent_connection_year`:

```
gap = current_year − most_recent_connection_year
  0–2y    → 1.00
  3–5y    → 0.85
  6–10y   → 0.60
  10y+    → 0.35
None      → 0.75   (agent didn't capture the year)
```

Future years (data error / typo) clamp to 1.00.

`None → 0.75` is an intentional "neutral discount" — agents that
don't bother to track recency get a calibrated penalty, while
agents that explicitly say "this connection is from 2010" get the
full 0.60 (or 0.35) discount.

## Calibration shifts vs Sprint-1 (recalibrated for v2)

| Edge | v1 | v2 | rationale |
|------|----|----|-----------|
| `small_team_coauthor_5y` | min(1.0, n/5) | unchanged | strongest direct working signal, saturates appropriately |
| `big_collab_papers_5y` cap | 0.40 | **0.10** | alphabetical author bulk is a very weak signal alone; rescue via WG / AC |
| `same_working_group` | 0.70 | **0.75** | small bump — verified subgroup membership is closer to direct collab than v1 implied |
| `analysis_contact_overlap` | 0.95 | **0.70** | recalibrated to compose with secondary bonus instead of saturating alone |
| `same_advisor` genealogy | 1.00 | **0.65** | academic siblings without active collab are no longer the strongest signal |
| `uncle_nephew` genealogy | 0.70 | **0.50** | shifted down to fit the new ladder |
| `two_hop` genealogy | 0.40 | unchanged | |
| `collaboration_overlap_years` | ≥5y→1.0 / 1-5→0.6 / <1→0.3 | unchanged | |
| `committee_co_member` | 0.80 / 0.30 | unchanged | (distinct from new `committee_or_exam_overlap` which is 0.45) |

The genealogy downgrade is the biggest behavioral change. Under v1, a
candidate who's an academic sibling (same_advisor) saturated to C=4.0
even with no other connection. Under v2, same_advisor alone gets
0.65 → after recency 0.75 (unknown) → 0.49 → bucket 3.3. Adding any
verified active collaboration (e.g., 1 small-team paper or same-center)
pushes them back into the 3.7+ range.

## Guardrails (v2 invariants pinned by tests)

1. **Big-collab author-list overlap alone cannot create strong C.**
   `path_strength({big_collab_papers_5y: 100, most_recent_connection_year: 2026})`
   = 0.10. Bucket 2.3.

2. **Same working group / analysis contact rescues big-collab fields.**
   `{big_collab_papers_5y: 50, same_working_group: True}` → max=0.75
   wins, big_collab adds tiny secondary bonus. Bucket 3.7.

3. **Co-mentored student / shared grant rank near direct collaboration.**
   co_mentored cap 0.90, shared_grant cap 0.80 — just below the 1.00
   small_team_coauthor saturation.

4. **Many weak signals must NOT beat one strong verified direct edge.**
   Many-weak (big_collab + 2 conferences + same_center + prior_institution_5y)
   → max=0.40 + 0.10·0.35 = 0.435 → recency 0.75 → 0.326 → bucket 2.8.
   One-strong (small_team=5 with recent year) → 1.0 → bucket 4.0.

5. **Verified-empty path behavior remains intact.** A PathEdge with
   no edge fields set + items.supports_fields=["path:<id>"] still
   counts as verified-empty in strict mode.

6. **Strict evidence requires `supports_fields` for every newly-set
   v2 field.** `shared_grant_count_5y=2` without a matching item =
   strict-mode reject; `path:<adv_id>` shows up in `unsourced_names`.

7. **No-advisor baseline preserved.** `connection_score([], cand)`
   still returns 2.3 (lowest bucket) under v2 — unchanged.

## Sort key (post-Sprint-2-c1 — unchanged from #5)

The new connection scoring does NOT touch the sort-key ladder. C
flows into `match_score` (CAPEG) like before. The primary sort key
is still `difficulty_adjusted_strength` from roadmap-#5.

## Field-aware threshold for big-collab

`big_collab_papers_5y` vs `small_team_coauthor_5y` is bucketed using
`FieldProfile.big_collab_threshold` (physics 10, mse/cs 8,
biology/chemistry 6, math 4). Use the
`classify_coauthorship(author_count, field_profile)` helper —
unchanged from Sprint-1.
