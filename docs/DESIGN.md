# phdtaketaketake — Design Charter

## Mission (one line)

**Generate auditable, discipline-calibrated, connection-first US PhD
advisor / program rankings for STEM applicants — to support school and
advisor selection, without pretending to be an admission-probability
predictor.**

---

## 1. Core principles

| Principle | What it means |
|-----------|---------------|
| **Connection-first** | The top signal is whether the applicant's current advisor / recommenders have a verifiable academic link to a target PI — not school prestige, not h-index, not paper count. |
| **Evidence-first** | Every claim traces to a real source the agent actually fetched. Strict mode rejects unsourced claims. |
| **Field-aware** | Publication culture, author-position semantics, advisor-influence signals, and ranking sources differ by STEM discipline. The skill cannot share one ruleset across them. |
| **Risk-adjusted** | Sparse evidence pushes a candidate down the ranking. Pretty numbers without proof don't beat moderate numbers with proof. |
| **Decision-support, not prophecy** | Output is a relative-fit / application-strength index, not a probability of admission. Surface what's strong, what's weak, what's uncertain — never claim "30% chance". |

---

## 2. User goals — questions the skill must answer

1. *Which US PhD programs fit my profile?*
2. *Which PIs match my research direction?*
3. *Which PIs have a real connection to my current advisor / recommenders?*
4. *Which schools are reach / target / match for me?*
5. *Which rankings reflect strong evidence vs. data gaps?*
6. *What should I prioritize next — gather more evidence, contact a specific PI, expand my list, change my angle?*
7. *How does the picture change if I shift subfield / target tier?*

---

## 3. Input design — `StudentProfile`

The schema must cover, with minimal questions:

- **Background** — institution, GPA + scale, degree level, field / subfield
- **Research direction** — short paragraph (≥30 words is a useful floor), not just keywords
- **Current advisors / recommenders** — the core Connection input
- **Papers** — venue, tier, author role, status, with field-specific conventions (`co_first`, `senior`, `consortium`)
- **Experiences** — lab tier, duration, output, PI strength
- **Application constraints** — target region / tier, willingness to cross subfield
- **Optional self-report** — SOP angle, recommendation-letter strength, weak spots

Goal: ask the minimum needed for a sound score, never proceed without the *required* inputs (field, GPA, research direction).

---

## 4. FieldProfile — the per-discipline calibration layer

Every bundled profile in `data/field_profiles/<id>.yaml` declares:

- `venue_system` (journal_first / conference_first / preprint_first / trial_first / mixed)
- `big_collab_threshold` (author count)
- `co_first_supported`
- `senior_author_position`
- `primary_databases` (per-field web sources, in priority order)
- `ranking_source_url_template` (per-field PhD-ranking URL — CSRankings for CS, US News field-specific for others)
- `genealogy_resources`
- `advisor_influence_signals`
- `paper_status_weight_overrides`
- `scoring_weight_overrides` (reserved)
- `research_fit_axes`
- `caveats`

The profile must reach the deterministic scoring engine — not just appear in caveats. Currently active: paper-status overrides (math `preprint=0.9`); coauthorship classification; ranking-source guidance.

---

## 5. Publication Scoring goals

Per-field calibrated, never "more papers = higher". Specifically:

| Field | Calibration |
|-------|-------------|
| Physics / HEP | Big-collab papers are not penalized as middle author, but also not credited as 1st author. The 5+ rule (`min(3.5, 4-author-score)`) holds. |
| CS | Conference-first. NeurIPS / ICML / CVPR / OSDI / SOSP / STOC / FOCS etc. = top journals — agent must not default them to tier 4. |
| Biology | `co_first` is common — `author_role: "co_first"` → 1st-author equivalent. Last = PI. PubMed / bioRxiv / NIH context matters. |
| Math | arXiv preprint often is the canonical record. Publication pipeline is slow. Author order frequently alphabetical. Math activates `paper_status_weight_overrides: {preprint: 0.9}`. |
| Chemistry / MSE | Last author = PI. 6+ author total-synthesis or materials papers may still be small effective teams — confirm with the student. |
| Clinical / biomedical | RCT / consortium / clinical trial author roles need specific handling (planned). |

**Goal**: P score = field-calibrated research-output strength.

---

## 6. Connection Scoring goals

Connection covers:

- `small_team_coauthor_5y` (≤ field threshold)
- `big_collab_papers_5y` (> field threshold) — alphabetical author bulk; weak signal
- `same_working_group` (subgroup / convener overlap)
- `analysis_contact_overlap` (paper editor / analysis contact)
- academic genealogy (`same_advisor` / `uncle_nephew` / `two_hop`)
- committee / editorial board / conference PC co-membership
- shared grants / centers / institutes (planned)
- known advisor-to-advisor network beyond co-authorship (planned)
- verified-empty path (records "I searched, found nothing")

**Goal**: distinguish "name on a 3000-author author list" from "actually worked together, would calibrate a recommendation letter".

---

## 7. Advisor Influence — A dimension (extracted in #3, refactored in #6a)

A is now **reputation-only** (post-`58596fa`). Funding and
recruiting moved to the **Opportunity (O)** signal in roadmap #6a so A
no longer reads `pi_signal` or `active_funding_quality`. Components:

- h-index / citation percentile (proxy via `normalized_collab_top20pct`)
- academy membership (NAS / NAE / NAM via `collab_with_nas`)
- field-specific fellow status (HHMI / APS / ACM / IEEE / ACS / RSC / MRS / TMS — surfaced in `collab_with_nas` + caveats)
- lab placement quality (`grad_placement_quality`)

Composite (post-#6a): `0.40·influence + 0.30·elite + 0.30·placement`.
Bounded tier weights still ensure A never outranks C — connection-first
invariant preserved.

Still planned:
- recent PhD output rate (separate from recruiting health)
- student career outcomes (longitudinal placement data — stronger than the current placement_quality proxy)
- field-centrality / network-density

**Goal**: ask "is this PI strong, well-known, and good for placement?" —
the multi-year reputation question. The orthogonal "is this PI taking
students this cycle, with funding, with capacity?" question is owned
by O (§7b).

---

## 7b. Opportunity — admit-cycle availability (roadmap #6a)

Time-sensitive availability signal. **Not in `match_score`** (CAPEG
stays clean); feeds `application_strength` via `opportunity_adj`
which **replaces the v1 `pi_adj` term**.

Components:
- `pi_signal` — recruiting health (strong / normal / shrinking / missing / not_recruiting)
- `lab_open_positions` / `current_student_count` / `recent_phd_graduations` — capacity
- `active_funding_quality` — funding strength (NIH RePORTER / NSF / DOE / ERC)
- `grant_end_years` — funding timing
- `sabbatical_or_admin_load` — PI availability
- `application_contact_policy` — accessibility

`O_raw = 0.30·recruiting + 0.30·funding + 0.20·capacity + 0.10·timing + 0.10·availability`.

Pure-legacy candidates (no `opportunity_signal`) use the v1 PI_ADJ
table verbatim — preserving exact old behavior. Migrated candidates
get `opportunity_adj` from the full O composite.

**Goal**: separate the time-sensitive "can I get in this cycle and survive
funding-wise" question from the multi-year "is this PI's network and
placement record worth investing 5–6 years in" (A) question.

---

## 8. Research Fit (live as tie-breaker — roadmap #4)

Not keyword overlap. Must decompose by field profile:

| Field | Fit axes |
|-------|----------|
| CS | Recent venue track · project keywords · methods |
| Biology | Technique · organism · disease area · model system |
| Math | Problem area · advisor lineage · preprint topic |
| Chem / MSE | Material system · method · instrument platform |
| Physics | Experiment / collaboration · subgroup · theory ↔ experiment distinction |
| Clinical | Disease area · trial network · hospital system |

**Active form**: pure tie-breaker in the sort key (post-`a24d9ab`); does NOT enter the match formula and does NOT contribute to evidence coverage when null (so a missing fit cannot widen the band). **Not** a Connection-rivaling pillar — that would dilute the connection-first thesis.

---

## 9. School Difficulty goals

`school_tier` is *program-specific*, not "the school's overall ranking":

| Field | Source |
|-------|--------|
| Physics / Chemistry / Biology / Math | US News field-specific PhD program ranking |
| CS | **CSRankings** — community-maintained, more reliable for CS subfields |
| MSE / EE / ChemE | Engineering ranking |
| Medical / clinical-adjacent | NIH funding · hospital system · department strength |
| Interdisciplinary | Allow multiple ranking sources, take the most charitable applicable one |

**Goal**: `school_tier` reflects how hard *this PhD program in this field* is, not how famous the university name is.

---

## 10. Evidence / Strict Mode goals

Strict mode (`--strict-evidence`) must guarantee:

- Every positive claim has an `EvidenceSource`
- Every source binds to specific `supports_fields`
- Legacy bare URLs do not pass strict
- Verified-empty ("I searched, found nothing") is recorded with structured evidence (`supports_fields=["path:<id>"]` for paths)
- Explanation cites only sources whose `supports_fields` matches the claim
- Unsourced claims are rejected outright
- Missing data is allowed but surfaced

**Goal**: the agent can be ignorant — but cannot pretend.

---

## 11. Output goals

The result card per candidate must surface:

- Match score / `application_strength` (NOT a probability)
- `risk_adjusted_strength` (sort key) · `lower_bound` · `confidence_band`
- 5-tier label: Reach · Target · Match · Safe · Far Reach
- Per-dimension scores: C / P / E / G (eventually + A for advisor influence and an optional research-fit term)
- Evidence coverage: `verified` / `missing` / `unsourced` with names
- Field-specific caveats from FieldProfile
- "Why ranked here" — concise per-claim justification with cited URLs
- **Next action** (planned): "gather more evidence on X" / "contact PI Y" / "expand list to top-30" / "consider subfield Z"

**Goal**: the user sees at a glance what's strong, what's weak, what's uncertain, what to do next.

---

## 12. Non-goals

Explicitly out of scope:

- Predicting real admission probability
- Replacing advisor / committee judgment
- Using training memory to fabricate facts
- Treating h-index as the core ranking signal
- Double-counting school prestige
- Letting unsourced narrative move the final ranking
- Pretending all STEM disciplines share one set of conventions

---

## Roadmap

| # | Item | Status |
|---|------|--------|
| 1 | FieldProfile operationalization | ✅ done (commits `7a6d002` → `1d391a0`) |
| 2 | Field-aware publication scoring | ✅ done (`1d391a0`) |
| 3 | Advisor influence as standalone A dimension | ✅ done (`f80c4d9`) |
| 4 | Research fit as tie-breaker / ≤0.15× adjustment | ✅ done — initial form is **pure tie-breaker** in sort key, no pillar weight (`a24d9ab`) |
| 5 | Program difficulty refinement (per-field ranking source) | ✅ done — `ProgramProfile` + `program_difficulty_penalty` (0–0.8) replaces `tier_adj`; `difficulty_adjusted_strength` is now the primary sort key; label applied to it (`90922d6`) |
| 6a | Opportunity scoring (admit-cycle availability) | ✅ done — `OpportunitySignal` + `opportunity_adj` replaces v1 `pi_adj`; A refactored to reputation-only (`0.40·influence + 0.30·elite + 0.30·placement`) (`58596fa`) |
| 6b | Evidence audit CLI | ✅ done — `scripts/audit_candidates.py` returns `strict_ready` / `blocking_issues` / `repair_queue` (severity high/medium) / `coverage_summary` / `input_warnings`; `repair_hint_for` exposed as public API (`4ad71cf`) |
| Connection v2 (Sprint-2-c1) | Expanded network model | ✅ done — PathEdge gains 6 new edge types (shared_grant / co_mentored_student / committee_or_exam / same_center / prior_institution / conference_session) + `most_recent_connection_year` drives a recency multiplier; aggregation switched to "strongest + 0.10·second-strongest, cap 1.0" then × recency; v1 same_advisor 1.0→0.65, analysis_contact 0.95→0.70, big_collab cap 0.40→0.10 (`9747f43`) |
| Publication v2 (Sprint-2-c2) | Recency + contribution_role + big-collab guardrails | ✅ done — Paper gains `contribution_role` / `contribution_evidence` / `citations_optional` / `field_normalized_impact`; `paper_score` adds `recency_weight` (≤2y → 1.0 / 3–5y → 0.95 / >5y → 0.85), big-collab guardrail (cap at 3.5 unless verified contribution), consortium guardrail (cap at 0.45×baseline unless verified); cs.yaml/biology.yaml gain `paper_status_weight_overrides` (`1054ff3`) |
| Research Fit v2 (Sprint-2-c3) | Structured 6-axis weighted score | ✅ done — `ResearchFit` submodel with 6 weighted axes (topic 0.30 / method 0.20 / system 0.15 / temporal 0.15 / grant 0.10 / background 0.10) replaces the free-form `research_fit_axes` dict; `theory_experiment_fit` stored for display, NOT in formula; resolution priority: v2 ResearchFit → legacy `research_fit_score` → None; tie-breaker role unchanged (`a07fd4a`) |
| 6 | Candidate discovery workflow field-aware | ✅ done (Sprint-2-c4) — `scripts/build_discovery_plan.py` + `phd_matcher.matching.discovery.build_discovery_plan`; per-field query recipes for physics / cs / biology / chemistry / mse / math; surfaces `primary_databases` / `ranking_source_url` / `field_caveats` from the profile + universal `exclusion_rules` (`370bc97`) |
| 7 | Output explainer as application-strategy report (next-action) | ✅ done (Sprint-2-c5) — `StrategyRecommendation` per candidate + `StrategySummary` portfolio-level rollup; bucket precedence drop→only_if_space→reach→target→priority (first match wins); strong-C-overrides-bucket rule for `contact_first`; outreach_angle uses only sourced material; pinned by `test_strategy_does_not_change_scores`; CLI emits `strategy_summary` + per-result `strategy` (`d353279`) |
| Evidence collection v1 (Sprint-3-c1) | Source adapters + collect_evidence.py | ✅ done — `phd_matcher/sources/` with `SourceAdapter` base + `OpenAlexAdapter` (fixture / live / offline modes); `EvidenceCollector` orchestrator; `scripts/collect_evidence.py` enriches `research_areas` (from concepts) and `paths_to_advisors[<adv>]` (small_team / big_collab counts + most_recent_connection_year + verified-empty) with structured `EvidenceSource` items. Hard rule: adapters never compute scores (pinned by `test_collect_evidence_does_not_modify_scores`) (`2325666`) |
| OpenAlex deepening (Sprint-3-c2) | h_index → influence + research_fit evidence | ✅ done — collector now also fills `normalized_collab_top20pct` from `min(1.0, h_index/50)` (with formula in the claim); attaches `research_fit` evidence items from recent papers whose concepts/title overlap the student's research_direction tokens. The score `research_fit_score` itself is NEVER written by the collector (pinned by `test_collect_evidence_does_not_compute_research_fit_score`) (`<COMMIT-PENDING>`) |
| 8 | CI / packaging / distribution | blocked — CI YAML staged at `.github_workflows/ci.yml`, needs `gh auth refresh -s workflow` to land at `.github/workflows/`; PyPI / plugin marketplace deferred |

---

## Core design statement

> **Move PhD application from "look at rankings and brand names" to
> "match by real evidence in an advisor network".**

Every architectural decision in this repo should answer to that line. If
a feature makes the matcher prettier but doesn't push *evidence* into
*decision*, it's the wrong feature.
