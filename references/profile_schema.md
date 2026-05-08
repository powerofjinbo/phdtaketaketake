# Profile + CandidateAdvisor JSON schema

Canonical shapes of the matcher's inputs. See `phd_matcher/models.py` for the
Pydantic source of truth; this file is the human-readable reference.

## StudentProfile

```jsonc
{
  "name": "Optional display name",
  "field": "physics",                    // REQUIRED — any STEM field as string
  "undergrad_institution": "...",        // REQUIRED
  "master_institution": null,            // optional
  "gpa_raw": 3.82,                       // REQUIRED — number or string
  "gpa_scale": "4.0",                    // REQUIRED — see below
  "research_direction": "...",           // REQUIRED — short paragraph

  "current_advisors": [ ... ],           // recommended (drives Connection)
  "papers":           [ ... ],           // recommended (drives Pub)
  "experiences":      [ ... ]            // recommended (drives Experience)
}
```

`field` accepts any string. **No bundled candidate cache** for any field —
the agent generates candidates per query (see SKILL.md). The bundled
`data/journals/<field>.yaml` exists only for **physics + mse** as the project's
authoritative tier opinion; for other fields the agent uses its training
knowledge anchored on `references/journal_tiers.md`.

### `gpa_scale` enum

| Value | System |
|-------|--------|
| `"4.0"` | US 4.0 |
| `"4.3"` | Some Canadian / Asian |
| `"4.5"` | Some Chinese tech schools |
| `"100"` | Chinese percentage (`gpa_raw` is 0–100) |
| `"uk"` | UK honours (`gpa_raw` is `"first"` / `"high_2_1"` / `"low_2_1"` / `"2_2"` / `"third"`) |

### `current_advisors[]`

```jsonc
{
  "id": "adv_001",
  "name": "Prof. Lisa Wang",
  "institution": "Tsinghua University"
}
```

### `papers[]`

```jsonc
{
  "title": "Search for new physics in dijet events with the ATLAS detector",
  "journal": "Physical Review D",
  "journal_tier": 3,                     // REQUIRED — 0 | "S" | 1 | 2 | 3 | 4 | 5
  "author_position": 312,                // REQUIRED — 1-indexed; ATLAS/CMS papers can be 100+
  "status": "published",                 // see status enum
  "year": 2024,                          // optional
  "doi": null                            // optional
}
```

#### `status` enum (post-review)

| Value | Weight | Meaning |
|-------|--------|---------|
| `"published"` | 1.0 | Already in print / online with DOI |
| `"accepted"` | 1.0 | Editor's accept letter received |
| `"in_press"` | 1.0 | Production stage |
| `"submitted"` | 0.7 | Under review at the named journal |
| `"preprint"` | 0.7 | On arXiv / bioRxiv etc., not yet under review or pre-submission |
| `"in_prep"` | 0.3 | Drafting; not yet a real submission |

The weight multiplies the tier × position score. Default is `"published"` —
match the assumption that the user lists papers they expect on their CV by
application time. Use the lower weights honestly when the user says "I'm
submitting in October" or "we're still drafting".

Tier mapping is universal across STEM — see
[`references/journal_tiers.md`](journal_tiers.md), with field-specific caveats
(CS is conference-driven, biology has co-first conventions, math journals have
different pace, etc.).

### `experiences[]`

```jsonc
{
  "lab_pi_name": "Prof. Lisa Wang",
  "lab_tier": "strong_us_or_top_cn",     // see lab_tiers.md
  "duration_months": 18,
  "output_type": "honors_thesis"
}
```

`output_type` enum:
- `"paper"` (already counted in pub_score; carries 3.7 here so experience isn't penalized)
- `"conference_oral"` (3.7) / `"conference_poster"` (3.3)
- `"honors_thesis"` (3.0) / `"participation_only"` (2.5)

The matcher takes the **strongest single experience** (no stacking).

---

## CandidateAdvisor (always agent-generated via web research)

```jsonc
{
  "id": "cand_001",
  "name": "Prof. Jane Doe",
  "institution": "Stanford University",
  "school_tier": "top_10",                  // top_10 | top_11_30 | top_31_60 | top_60_plus
  "field": "chemistry",
  "research_areas": ["catalysis", "C-H activation"],

  "paths_to_advisors": {                    // KEY — see edge schema below
    "adv_001": {
      "small_team_coauthor_5y": 3,
      "sources": [
        "https://scholar.google.com/citations?user=...",
        "https://api.openalex.org/works?filter=..."
      ],
      "note": "3 co-authored papers in 2022–2024 per Scholar"
    }
  },

  "normalized_collab_top20pct": 0.65,
  "collab_with_nas": false,
  "grad_placement_quality": 0.7,
  "active_funding_quality": 0.6,

  "pi_signal": "normal",
  "recent_phd_count": 4,

  // Roadmap-#6a — opportunity (admit-cycle availability). Drives
  // `opportunity_adj` (replaces v1 pi_adj) inside application_strength.
  // Field-by-field merges with legacy top-level pi_signal /
  // active_funding_quality. See references/opportunity.md.
  "opportunity_signal": {
    "pi_signal": "strong",
    "lab_open_positions": 2,
    "current_student_count": 5,
    "recent_phd_graduations": 2,
    "active_funding_quality": 0.85,
    "grant_end_years": 4,
    "sabbatical_or_admin_load": false,
    "application_contact_policy": "email_first",
    "evidence": {
      "lab_open_positions": {
        "items": [{
          "url": "https://lab.stanford.edu/positions",
          "source_type": "lab_page",
          "claim": "Lab page lists 2 open PhD positions for Fall 2026",
          "supports_fields": ["opportunity:lab_open_positions"]
        }]
      }
    }
  },

  // Roadmap-#5 — program difficulty (replaces tier_adj). All fields optional.
  // Each scoring-relevant set field needs evidence with
  // supports_fields=["program:<field>"]. See references/program_profile.md.
  "program_profile": {
    "department": "Chemistry",
    "admission_model": "rotation",
    "cohort_size_estimate": 18,
    "faculty_count_in_area": 6,
    "international_friendliness": 0.7,
    "funding_structure": "guaranteed",
    "evidence": {
      "cohort_size_estimate": {
        "items": [{
          "url": "https://chem.stanford.edu/admissions/...",
          "source_type": "lab_page",
          "claim": "department admits ~18 PhDs/yr (2023 admissions report)",
          "supports_fields": ["program:cohort_size_estimate"]
        }]
      }
    }
  },

  // Roadmap-#4 — research fit (tie-breaker, NOT a pillar). v2 form:
  // structured 6-axis ResearchFit submodel. When `research_fit` is set,
  // the matcher derives research_fit_score from the weighted formula
  // (0.30·topic + 0.20·method + 0.15·system + 0.15·temporal + 0.10·grant
  // + 0.10·background) and the legacy flat fields below are ignored.
  // Set evidence inside `research_fit.evidence`, not the candidate-level
  // evidence dict.
  "research_fit_summary": "5 of last 8 papers on catalysis with C-H activation focus",
  "research_fit": {
    "topic_fit": 0.90,
    "method_fit": 0.80,
    "system_or_dataset_fit": 0.70,
    "theory_experiment_fit": null,         // optional; mainly physics
    "temporal_fit": 0.85,                  // recent papers still on topic
    "grant_fit": 0.60,
    "student_background_fit": 0.70,
    "evidence": {
      "research_fit": {
        "items": [{
          "url": "https://scholar.google.com/citations?user=...",
          "source_type": "google_scholar",
          "claim": "5 of last 8 papers (2024) on C-H activation",
          "supports_fields": ["research_fit"]
        }]
      }
    }
  },
  // Legacy v1 form (still accepted; ignored when `research_fit` set):
  // "research_fit_score": 0.78,
  // "research_fit_axes": {"material_or_system": 0.9, "synthesis": 0.8, ...},

  "evidence": {                             // claim-level sources, see references/evidence_schema.md
    "normalized_collab_top20pct": {
      "items": [{
        "url": "https://scholar.google.com/citations?user=...",
        "source_type": "google_scholar",
        "claim": "h_index = 42 (checked 2026-05-06)",
        "supports_fields": ["normalized_collab_top20pct"]
      }]
    },
    "pi_signal": {
      "items": [{
        "url": "https://lab.stanford.edu/people",
        "source_type": "lab_page",
        "claim": "lab page lists 4 current PhDs joined 2023-2024",
        "supports_fields": ["pi_signal"]
      }]
    }
    // ...one entry per claimed signal
  },

  "searched_sources": [                     // auditability — what was checked, even if empty
    "https://www.genealogy.math.ndsu.nodak.edu/?id=...",
    "https://www.nasonline.org/member-directory/..."
  ]
}
```

### Connection edges (`paths_to_advisors[advisor_id]`) — Connection v2

The matcher reads from these keys (any subset). All edges should be
backed by `items[]` entries with matching `supports_fields` per the
data-integrity policy. Aggregation: **strongest single edge + 0.10 ×
second-strongest (cap 1.0), then × recency multiplier**. See
[`connection_v2.md`](connection_v2.md) for the full ladder, recency
table, guardrails, and v1→v2 calibration shifts.

| Edge field | Type | Strength | When to record |
|------------|------|----------|----------------|
| `small_team_coauthor_5y` | int | `min(1.0, n/5)` | Distinct co-authored papers in last 5y with **≤threshold authors** (real working relationship) |
| `co_mentored_student_count` | int | `min(0.90, n·0.30)` | Students jointly mentored by both (committee co-mentorship counts) |
| `shared_grant_count_5y` | int | `min(0.80, n·0.40)` | NSF/NIH/DOE shared grants in last 5y |
| `same_working_group` | bool | 0.75 | Verified subgroup / convener overlap within a larger collaboration |
| `analysis_contact_overlap` | bool | 0.70 | Both listed as analysis contacts on a specific paper / note |
| `genealogy_relation` | string | `same_advisor`=0.65 / `uncle_nephew`=0.50 / `two_hop`=0.40 | Verified via Math Genealogy or faculty bio |
| `committee_or_exam_overlap` | bool | 0.45 | PhD committee / qualifying exam overlap |
| `same_center_or_institute` | bool | 0.40 | Both members of NSF ERC / NIH center / DOE lab / institute |
| `prior_institution_overlap_years` | int | `min(0.35, years/10)` | Years overlapped at the same institution before current roles |
| `conference_session_overlap_5y` | int | `min(0.20, n·0.10)` | Conferences in last 5y where both presented at same session |
| `big_collab_papers_5y` | int | `min(0.10, n/100)` | Papers with **>threshold authors** (alphabetical author bulk; very weak alone) |
| `collaboration_overlap_years` | float | ≥5y=1.0 / 1–5y=0.6 / <1y=0.3 | Generic shared-collab overlap (v1, unchanged) |
| `committee_co_member` | bool + `same_period` bool | 0.8 / 0.3 | Documented editorial board / NSF panel / PC overlap (v1, unchanged) |
| `most_recent_connection_year` | int | (recency multiplier) | Year of last direct interaction; None → 0.75 multiplier |
| `items` | list[EvidenceSource] | — | Per-claim evidence with `supports_fields` |
| `note` | str | — | Freeform — what was searched, what was found |

Big-collab threshold is field-specific via
`FieldProfile.big_collab_threshold` (physics 10, mse/cs 8,
biology/chemistry 6, math 4).

### Advisor-influence fields (drive the A pillar — post-roadmap-#6a, reputation-only)

| Field | Range | Estimation |
|-------|-------|------------|
| `normalized_collab_top20pct` | 0–1 | Proxy: `min(1.0, h_index / 50)`. Look up h-index on Google Scholar / OpenAlex. |
| `collab_with_nas` | bool | Three-state. `true` only if you found a specific NAS / HHMI co-author in the official directory. `false` only if you searched and confirmed none (verified-empty). `null` if you didn't search. |
| `grad_placement_quality` | 0–1 | Read the lab's alumni page. Top faculty placements: 0.8+, mix academia+industry: 0.5–0.7, mostly post-docs: 0.4. |
| `active_funding_quality` | 0–1 | **Moved to OpportunitySignal post-#6a** but kept on top-level for legacy back-compat (field-by-field merge). NIH RePORTER / NSF Award Search / DOE Office of Science / ERC. |
| `pi_signal` | enum | **Moved to OpportunitySignal post-#6a** but kept on top-level for legacy back-compat. See OpportunitySignal table for values. |

Each non-null value needs a matching entry in `candidate.evidence` with
`supports_fields=[<field>]` items. See
[`references/candidate_discovery.md`](candidate_discovery.md) for the
per-field elite-signal guidance and
[`references/evidence_schema.md`](evidence_schema.md) for the strict
mode rules.

### Program-difficulty fields (drive the difficulty penalty — post-roadmap-#5)

| Field | Range | Notes |
|-------|-------|-------|
| `program_profile` | `ProgramProfile` \| `null` | Per-program difficulty signals (cohort, admission model, funding, area coverage, international friendliness). Replaces the v1 `tier_adj` term. |

When `program_profile` is set, each scoring-relevant field that's set
(non-`None`, non-`"unknown"`) requires evidence with
`supports_fields=["program:<field>"]`. See
[`references/program_profile.md`](program_profile.md) for the full
schema, formula, and per-component table.

### Research-fit fields (drive the tie-breaker — post-roadmap-#4)

| Field | Range | Notes |
|-------|-------|-------|
| `research_fit` | `ResearchFit` \| `null` | **v2 form (preferred).** Structured 6-axis submodel: `topic_fit`, `method_fit`, `system_or_dataset_fit`, `theory_experiment_fit` (optional, display-only), `temporal_fit`, `grant_fit`, `student_background_fit`. All axes 0–1. When set, derives `research_fit_score` deterministically; legacy fields below are ignored. Evidence lives in `research_fit.evidence` with `supports_fields=["research_fit"]`. |
| `research_fit_score` | 0–1 \| `null` | **Legacy v1 form.** Free-form score; ignored when `research_fit` is set. `null` means "not computed" (not counted in evidence coverage; does not widen the band). |
| `research_fit_summary` | string \| `null` | Short prose describing the alignment (used by both v1 and v2). |
| `research_fit_axes` | dict[str, float] | **Legacy v1 form.** Free-form per-axis breakdown; ignored when `research_fit` is set. Values must be in `[0, 1]`. |

In either form, the matcher uses the score as a **tie-breaker only** —
it does NOT enter the match formula. Strict mode requires evidence with
`supports_fields=["research_fit"]` when a score is set (legacy path) or
the structured submodel is used (v2 path; evidence lives on the
submodel itself). See [`references/research_fit.md`](research_fit.md)
for the per-field axis weights and per-discipline rubrics.

### `pi_signal` enum

| Value | Adjustment | When to use |
|-------|------------|-------------|
| `"strong"` | +0.2 | ≥2 new PhDs/yr last 3y per lab page |
| `"normal"` | 0 | 1–2/yr per lab page |
| `"shrinking"` | −0.4 | <1/yr OR many recent graduations without admits |
| `"missing"` | −0.1 | Page didn't load / didn't have a students list / status unclear (default — never guess) |
| `"not_recruiting"` | force application_strength = 0 | Explicitly stated |

### Minimal valid CandidateAdvisor

```jsonc
{
  "id": "cand_001",
  "name": "Prof. Jane Doe",
  "institution": "Stanford University",
  "school_tier": "top_10",
  "field": "chemistry",
  "research_areas": ["catalysis"]
}
```

Other fields default to safe values (empty paths, 0 / false / "missing"
signals). The matcher will rank this candidate low because so many signals
are unverified — the confidence band will be ≥ ±0.6.

---

## MatchResult (output)

```jsonc
{
  "candidate": { ... },
  "c_score": 3.70,
  "a_score": 3.30,                      // post-roadmap-#3 — Advisor influence pillar
  "p_score": 3.30,
  "e_score": 3.25,
  "g_score": 3.85,
  "match_score": 3.49,

  "application_strength": 3.49,         // post-#6a: clip(match_score + opportunity_adj, 0, 4.0). NOT a probability
  "confidence_band": 0.40,
  "strength_label": "Match",            // post-#5: applied to difficulty_adjusted_strength
  "risk_adjusted_strength": 3.29,       // = strength − band/2
  "lower_bound": 3.09,                  // = strength − band — conservative reading

  // Roadmap-#5 — program difficulty (new primary sort key)
  "program_difficulty_penalty": 0.50,   // 0–0.8; from school_tier + ProgramProfile signals
  "difficulty_adjusted_strength": 2.79, // = max(0, risk_adjusted − penalty); primary sort key
  "difficulty_reasons": [
    "school_tier=top_11_30 admit-rate factor +0.50"
  ],

  // Roadmap-#6a — opportunity (admit-cycle availability)
  "o_score": 0.78,                      // 0–1 from OpportunitySignal; null = pure-legacy path
  "opportunity_adj": 0.2,               // replaces v1 pi_adj inside application_strength

  "field_profile_id": "physics",        // which FieldProfile applied (or null)

  // Roadmap-#4 — research fit (mirror of CandidateAdvisor; tie-breaker only)
  "research_fit_score": 0.78,
  "research_fit_summary": "5 of last 8 papers on H→cc̄, primary detector matches",
  "research_fit_axes": { "subfield": 0.95, ... },

  "unverified_signals": 2,              // = missing + unsourced (back-compat)
  "missing_signals": 1,                 // data absent (info gap)
  "unsourced_signals": 1,               // value claimed without proof (hallucination risk)
  "total_signals": 9,                   // 8 for 1-advisor case; 9 if research_fit_score is set
  "missing_signal_names": ["grad_placement_quality"],
  "unsourced_signal_names": ["collab_with_nas"],

  "explanation": "Evidence coverage: 7/9 verified · 1 missing (grad_placement_quality) · 1 unsourced (collab_with_nas) · co-authored 3 small-team paper(s) with Prof. Wang in last 5y [https://scholar.google.com/... · google_scholar] · ..."
}
```

`application_strength` is **NOT a probability**. It's a 4.0-scale
relative-fit index: `clip(match_score + opportunity_adj, 0, 4.0)`,
where `opportunity_adj` (post-#6a) replaces v1's `pi_adj` and is
derived from the candidate's `OpportunitySignal` (recruiting health,
funding, lab capacity, grant timing, application contact policy).

The **primary sort key** is `difficulty_adjusted_strength`
(`= max(0, risk_adjusted_strength − program_difficulty_penalty)`).
Two layers happen between `application_strength` and the sort:

1. `risk_adjusted_strength = application_strength − band/2` — bakes
   evidence-coverage uncertainty in, so well-evidenced candidates
   outrank loosely-claimed peers even at lower nominal strength.
2. `difficulty_adjusted_strength` — subtracts the per-program
   difficulty penalty (school_tier admit-rate factor +
   `ProgramProfile` refinements; replaces v1's flat `tier_adj`).

See [`docs/scoring.md`](../docs/scoring.md) for the per-layer formulas
and [`references/scoring_reference.md`](scoring_reference.md) for the
in-context cheat-sheet.
