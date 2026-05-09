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

- `difficulty_adjusted_strength` — **primary sort key (post-#5)**
- `risk_adjusted_strength` and `lower_bound` as uncertainty views; `confidence_band` width
- `application_strength` (`= clip(match_score + opportunity_adj, 0, 4.0)`, NOT a probability)
- 5-tier `strength_label` applied to `difficulty_adjusted_strength`: Reach · Target · Match · Safe · Far Reach
- **Per-pillar CAPEG scores**: C / A / P / E / G — connection-first ordering preserved
- `o_score` and `opportunity_adj` (admit-cycle availability)
- `program_difficulty_penalty` and `difficulty_reasons` (per-component breakdown)
- `research_fit_score` and `research_fit_summary` when set (tie-breaker, NOT a pillar)
- Evidence coverage: `verified` / `missing` / `unsourced` with **namespaced** signal names
- Field-specific caveats from FieldProfile
- "Why ranked here" — concise per-claim justification with cited URLs
- **`StrategyRecommendation`** — `apply_bucket` (priority / target / reach / only_if_space / drop), `recommended_action`, `outreach_angle`, `evidence_to_fix`, `next_steps`. Purely derivative — does not modify any score.

**Goal**: the user sees at a glance what's strong, what's weak, what's
uncertain, and what to do next. Presentation is layered: a per-candidate
card for QClaw / Claude Code users (rendered by the agent following the
SKILL.md presentation contract), plus the full MatchResult JSON for power
users / strict-mode audit.

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

## 13. Frozen scope (post-Sprint-7)

The skill is feature-frozen as of Sprint-7. Sprint-6 did the
QClaw-launch hardening for the advisor-matching pipeline; Sprint-7
added the **CV optimization sub-skill** as a complementary
"PhD application triage" component. No further feature additions
after this without explicit roadmap revision.

### In scope (the two parallel workflows)

The skill is a **PhD application triage assistant** with two parallel
workflows that share install + repo:

1. **Advisor matching** — the original pipeline (`StudentProfile +
   CandidateAdvisor[] → MatchResult[]` per CAPEG / Opportunity /
   Difficulty / Research-fit / Strategy contracts). Frozen feature set
   per the Sprint-6 contract.
2. **CV optimization** (Sprint-7 addition) — LaTeX template + agent-led
   editing + multi-pass compile, with optional reordering / pruning for
   a target PI list. Adds **no** new scoring, **no** content invention,
   **no** SoP drafting. Lives in `phd_matcher/cv/`; full contract in
   `references/cv_optimization.md`.

CV optimization is added because it's the natural complement to advisor
matching in the "application triage" product positioning — once the
user knows which 5–10 PIs to apply to, optimizing the CV for those
targets is the obvious next step. It's structurally bounded (template
fill + reorder + compile, never invention), so it doesn't open new
classes of fabrication risk.

### Will not add (frozen)

- **Paid / commercial API integrations** — OpenAlex paid tier,
  Crossref Metadata Plus, Semantic Scholar paid, etc. The skill must
  remain runnable at $0 / month for individual users. Free-tier API
  keys are recommended, but no feature may *require* a paid key.
- **Admission probability output** — the score is a 4.0-scale
  relative-fit index, not P(admit). Surfacing anything that looks like
  a probability (percentages, "75% chance", calibrated odds) is
  forbidden — see §11.
- **Auto-bypass / scraping of blocked sites** — Cloudflare challenges,
  CAPTCHA-walled pages, login walls, paywalls. Blocked sources widen
  the confidence band; the skill does not work around access controls.
- **Large-scale HTML scraping pipelines** — the Python adapter layer is
  restricted to official JSON APIs (OpenAlex / PubMed / DBLP /
  Semantic Scholar). Web research is the agent's job; web *scraping
  infrastructure* is out of scope.
- **SoP / personal-statement / cover-letter / recommendation-letter
  drafting or revision** — explicitly out of scope for the CV
  sub-skill. CV optimization touches structure and ordering, not
  prose generation.
- **Fully-automated application drafting or contact emails** — the
  skill produces ranked lists, strategy buckets, outreach angles, and
  formatted CVs. It does not generate or send messages on the user's
  behalf.
- **CV content invention** — never adds an experience, skill, paper,
  or award the user didn't supply. Tailoring is reordering and
  pruning only.
- **ATS / industry-resume optimization** — the CV template is academic
  PhD-application style; converting between genres is out of scope.
- **"Best-guess" defaults when evidence is missing** — the matcher
  widens the band, it does not invent. Any feature that looks like
  "fill in 0.5 when we don't know" violates the evidence-first
  contract and is rejected.

### Preserved invariants (will not be removed or weakened)

- Connection-first weighting (`w_C > w_A` in every tier)
- Evidence-first data integrity (Verified / Verified-empty / Missing /
  Blocked, with strict-mode requiring claim-level supports_fields proof)
- Audit repair queue surfacing missing + unsourced + blocked signals
- Strategy bucket recommendation (`priority` / `target` / `reach` /
  `only_if_space` / `drop`) as a derivative of the score, never
  modifying it
- Per-discipline FieldProfile caveats surfaced in every result
- Manual evidence override path (user pastes lab page text / CV /
  screenshot quote → counts as `source_type="cv"` or `"other"`)
- **CV sub-skill: template-fill + reorder + compile only. No
  invention, no content judgement, no SoP / cover letter generation.**

This frozen-scope declaration is the contract under which the skill
goes onto QClaw and other skill platforms. Future work focuses on
calibration against real portfolios, not feature expansion.

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
| OpenAlex deepening (Sprint-3-c2) | h_index → influence + research_fit evidence | ✅ done — collector now also fills `normalized_collab_top20pct` from `min(1.0, h_index/50)` (with formula in the claim); attaches `research_fit` evidence items from recent papers whose concepts/title overlap the student's research_direction tokens. The score `research_fit_score` itself is NEVER written by the collector (pinned by `test_collect_evidence_does_not_compute_research_fit_score`) (`ccb6567`) |
| Multi-source adapters (Sprint-3-c3) | PubMed + DBLP + Semantic Scholar + dispatcher | ✅ done — three new `SourceAdapter` subclasses sharing the `FixtureLookup` layout. `select_adapter(name, ...)` factory + `default_adapter_for_field(field)` (biology→pubmed, cs/math→semantic_scholar, physics/mse/chemistry→openalex). `--source` CLI flag overrides the per-field default. Live mode is opt-in per adapter (PubMed live: E-utilities; DBLP live: deferred to c5; Semantic Scholar live: Graph API) (`8f47fa6`) |
| Source cache + rate limit (Sprint-3-c4) | `CachedAdapter` + `RateLimitedAdapter` decorators | ✅ done — disk-cached JSON via MD5 keys per (op, args); optional `ttl_seconds`; preserves inner adapter's `name` and forwards `errors`. Rate-limited adapter throttles live calls (default 0.1s polite-pool friendly). Composable: cache wrapping rate-limit means cache hits skip the wait entirely. CLI gains `--cache-dir`, `--cache-ttl-days`, `--rate-limit-seconds`; output `mode` reports `live+cache` etc. (`7ab8944`) |
| 8 | CI / packaging / distribution | ✅ done (Sprint-3-c5, partial) — `pyproject.toml` exposes 4 console scripts (`phdtaketaketake-match` / `-audit` / `-collect-evidence` / `-discovery-plan`); script bodies moved to `phd_matcher/cli/` package, `scripts/<name>.py` thin shims for checkout-only invocation. CI workflow YAML staged at `.github_workflows/ci.yml` (full lint + mypy + pytest + console-script smoke matrix py3.11/3.12) — needs `gh auth refresh -s workflow` then `git mv .github_workflows/ .github/workflows/` to activate. PyPI publishing deferred (`3cd23f7`) |
| Docs / UX polish (Sprint-4-c1) | README sync to v2 + calibration banner | ✅ done — README.md / README.zh.md updated to describe the post-Sprint-3 5-layered pipeline (CAPEG + O + D + R + Strategy); calibration disclaimer banner added at the top of both READMEs ("expert-designed heuristic, not empirically calibrated"). Output-per-candidate sections list every v2 field. Two shim docstring inconsistencies fixed (`ea27b1e`) |
| Pipeline diagram (Sprint-4-c2) | Mermaid 5-layer flowchart | ✅ done — new `docs/scoring_pipeline.md` with end-to-end Mermaid flowchart (Inputs → CAPEG → application_strength → risk-adjusted → difficulty-adjusted → strategy bucket); enumerates the 6 test-pinned architectural invariants; embedded as the first reference at the top of `docs/scoring.md` (`e8ec9ea`) |
| JSON Schema export (Sprint-4-c3) | `schemas/*.schema.json` + drift detector | ✅ done — 12 Pydantic top-level models exported as JSON Schema (Draft 2020-12) under `schemas/`; new console script `phdtaketaketake-export-schemas`; `extra="forbid"` → `additionalProperties: false`, Literals → enums, Field bounds → minimum/maximum; drift-detector test fails if Pydantic models change without regenerating (`ccaeb18` + follow-up `65eaa15`) |
| End-to-end demo (Sprint-4-c4) | `examples/physics_hep_audit_demo/` | ✅ done — full 4-stage pipeline (discovery_plan → collect_evidence → audit → match) on a fictional Tsinghua-undergrad ATLAS-Higgs applicant with 3 candidates landing in target / reach / only_if_space buckets; bundled fixtures replace live API calls; reproducible via `bash examples/physics_hep_audit_demo/run_example.sh`; `examples/README.md` index for adding new demos. Originally landed as `physics_hep_strict/`; renamed in Sprint-5-c4 since the demo runs in default mode (no `--strict-evidence`) to exercise the audit's repair queue, so the old name was misleading (`0179078`; renamed `22656db`) |
| DESIGN.md close-out (Sprint-4-c5) | Roadmap closed | ✅ done (`b59c05f`) |
| SKILL.md v2 sync (Sprint-5-c1) | Architecture overview + Step 5 A composite | ✅ done — replaced the v1 4-pillar (C/P/E/G) summary block at the top of `SKILL.md` with the 5-layer pipeline view (CAPEG match_score → application_strength → risk_adjusted → difficulty_adjusted → strategy bucket) + 5 CAPEG pillars in v2 form (`A = 0.40·influence + 0.30·elite + 0.30·placement`) + 3 non-CAPEG dimensions (Opportunity, Program difficulty, Research fit). Step 5 ("Advisor influence signals") A composite updated to match (was self-contradicting Step 5.5). `active_funding_quality` field redirected to `OpportunitySignal` as canonical home (`f83c6b7`) |
| docs/scoring.md back-half sync (Sprint-5-c2) | Sort key + app_strength + big-collab + program penalty | ✅ done — fixed 4 stale blocks: "primary sort key is risk_adjusted_strength" → reframed as intermediate, with primary-sort role handed to `difficulty_adjusted_strength`; `application_strength = match + pi_adj` → `clip(match_score + opportunity_adj, 0, 4.0)` with v1 footnote; "big-collab caps at 0.4 strength" → actual v2 cap formula `min(0.10, n/100)` with cross-ref to `references/connection_v2.md`; "Steep top-10 admit penalty (−1.0)" → `program_difficulty_penalty` (0–0.8) layer with school_tier factor table and cross-ref to `references/program_profile.md` (`5655d5e`) |
| profile_schema + demo README sync (Sprint-5-c3) | ResearchFit v2 example + MatchResult prose + spurious portfolio_note | ✅ done — `references/profile_schema.md` CandidateAdvisor example now shows the v2 `ResearchFit` submodel (6 fixed axes + evidence on the submodel) instead of the legacy free-form `research_fit_axes` dict, with v1 form kept as a commented fallback; "Research-fit fields" table re-keyed with v2-preferred / v1-legacy labels; MatchResult prose rewritten to spell out the post-#5/#6a pipeline (app_strength → risk_adjusted → difficulty_adjusted as actual primary sort key). `examples/physics_hep_audit_demo/README.md` removed a spurious "No priority or target candidates" portfolio_note that contradicted actual `match.json` (Hartman is target); rewrote the explanatory paragraph to say why Hartman is target-but-not-priority (`ab57a91`) |
| Example dir rename (Sprint-5-c4) | `physics_hep_strict/` → `physics_hep_audit_demo/` | ✅ done — see Sprint-4-c4 row above for the rename rationale and final paths (`22656db`; DESIGN backfill `1df9bc9`) |
| Sprint-5 close-out (Sprint-5-c5) | Polish + roadmap close | ✅ done — pyproject.toml comment "the four CLIs" → "the CLIs" (forward-compat as more scripts get added); `README.md` "four CLIs" → "five CLIs" + added `phdtaketaketake-export-schemas` entry to the listed set; `docs/scoring_pipeline.md` dropped the specific test-count "(358/358 passing)" since the count drifts every sprint; this row + 4 Sprint-5 close-out rows added above (`24517fa`) |
| Doc drift final sweep (Sprint-6-c1) | Genealogy v2 values + §11 Output goals refresh | ✅ done — `SKILL.md` Step 4 academic-genealogy ladder updated to v2 strengths (same_advisor 0.65 / uncle_nephew 0.50 / two_hop 0.40, was v1's 1.0 / 0.7 / 0.4) plus a one-paragraph note explaining the v2 framing ("genealogy is a meaningful historical signal, but weaker than verified recent working contact"); `docs/DESIGN.md` §11 Output goals rewritten to enumerate the actual MatchResult fields the card surfaces (`difficulty_adjusted_strength` as primary sort key, CAPEG with A as a first-class pillar, full StrategyRecommendation shipped — replaced "Next action (planned)") (`0b114ef`) |
| Natural-language entry + min-viable contract (Sprint-6-c2) | QClaw-shaped agent contract | ✅ done — `SKILL.md` new "How users actually invoke this skill" section between the architecture overview and Step 0, with two example natural-language entry messages (zh + en), required-information list (field / undergrad+gpa / research_direction / current_advisors / target schools), optional-improves-quality list with floor-vs-crash semantics, minimum-viable-run definition; `phd_matcher/cli/match.py` emits a stderr warning when StudentProfile loads with empty `current_advisors` (connection-first matching is degraded — no anchor for paths_to_advisors); README.md / README.zh.md "Use" section mirrors the entry-point framing with the required-vs-optional input list (`217d6c4`) |
| Output card format + boundary statement (Sprint-6-c3) | Per-candidate card + product disclaimer | ✅ done — `SKILL.md` Step 8 fully rewritten: replaced the old debug-style result rendering with a product-grade card template (fixed field order: title / Label / Strategy / numbers / Why-bullets / Main-risks / Next-action), concrete example using `physics_hep_audit_demo` Hartman card, "what goes in card vs JSON appendix" table, mandatory product-boundary footer in zh + en ("This is a 4.0-scale relative application-strength index, not an admission probability. Missing or blocked sources widen the confidence band instead of being guessed."); README.md / README.zh.md disclaimer block promoted the boundary statement to the top of the disclaimer (`5ceddcb`) |
| Blocked-source user-facing language (Sprint-6-c4) | Four-state policy + Main-risks template | ✅ done — `references/data_integrity.md` new "Blocked / timeout / CAPTCHA is not verified-empty" subsection introducing the fourth state alongside Verified / Verified-empty / Missing, with symptom→treatment table (200 OK / 403 / 429 / timeout / CAPTCHA / page-loaded-but-data-missing) and explicit manual evidence path (user pastes page content → recorded as `source_type="cv"` or `"other"`); `SKILL.md` new Step 8.5 "How to talk about missing signals to the user" with namespaced-signal → plain-English mapping table (path:adv_id, school_tier, pi_signal, opportunity:* / program:* signals), canonical "Main risks" template using user's preferred wording ("I couldn't verify the following signals — they're counted as missing and widen the confidence band ... you can manually paste lab page text, an alumni list, or a screenshot"), three-things-to-never-say + three-things-to-always-say checklists. No code changes — pure agent contract (`4864139`) |
| Product positioning + frozen-scope + closeout (Sprint-6-c5) | QClaw-launch hardening close | ✅ done — README.md tagline → "PhD advisor matching and application triage assistant. Connection-first, evidence-first." + QClaw mention; README.zh.md tagline → "基于真实学术网络证据的 PhD 导师匹配与申请优先级工具" + QClaw 提及; `docs/DESIGN.md` new §13 "Frozen scope (post-Sprint-6)" enumerates "will not add" items (paid APIs, admission-probability output, auto-bypass scraping, large-scale HTML scraping, fully-automated drafting, best-guess defaults) and "preserved invariants" (connection-first / evidence-first / audit queue / strategy / field caveats / manual evidence override); this row + 4 Sprint-6 close-out rows above (`e8ac634`) |
| CV template + cv-template CLI (Sprint-7-c1) | Sub-skill scaffolding + template + SKILL.md contract | ✅ done — new `phd_matcher/cv/` module exposes `TEMPLATE_PATH`; bundled `templates/default.tex` derived from a real physics-PhD-applicant CV (Education / Research / Publications / Tech Skills / Teaching / Leadership / Honors all present by default; OPTIONAL_BLOCK markers for niche bits like Coursework table; `<angle-bracket>` placeholders compile as-is to a placeholder demo CV); `phdtaketaketake-cv-template` CLI; SKILL.md new section "CV optimization (parallel workflow)" with 6 steps + zh+en disclaimer; `references/cv_optimization.md` per-section edit conventions + tailoring playbook; DESIGN.md §13 expanded to enumerate Sprint-7 in-scope additions and Sprint-7-specific frozen items (no SoP drafting, no content invention, no ATS optimization) (`1c4e9d4`) |
| cv-compile CLI + structured failure recovery (Sprint-7-c2) | Multi-pass compile + diagnostics + Overleaf fallback | ✅ done — `phd_matcher/cv/compile.py` core pipeline (latexmk preferred, pdflatex fallback up to 3 passes, regex-based diagnostic excerpt distilling 200–1000-line TeX logs to actionable lines); `phdtaketaketake-cv-compile` CLI with 4 exit codes (0 ok / 1 failed / 2 tex_not_installed / 3 input error); install hint covers macOS / Debian / Fedora / Windows + minimal-TeX gotcha (`tlmgr install titlesec enumitem`) + universal Overleaf fallback; template trimmed to remove unused imports (latexsym / marvosym / verbatim) and `fullpage` → `geometry` for portability across minimal TeX installs; 15 environment-tolerant tests (skip cleanly when TeX absent; accept either compile-success or compile-failed-with-diagnostic when TeX present-but-incomplete) (`75092d5`) |
| CV tailoring playbook + Sprint-7 close-out (Sprint-7-c3) | End-to-end tailoring example + README mention + closeout | ✅ done — `references/cv_optimization.md` new "Worked example" section walks through a real tailoring decision using `examples/physics_hep_audit_demo` data: pretends user is the demo's Tsinghua / ATLAS Higgs student, shows step-by-step how Hartman (the only `target` candidate) drives Research Experience reorder + bullet reorder + Publications reorder + Technical Skills reorder, with concrete LaTeX before/after and an explicit "what did NOT change" footer reinforcing the no-invention contract; README.md / README.zh.md "Use" section gain a "Parallel workflow: CV optimization" subsection mentioning both CLIs and Overleaf fallback; this row + 2 Sprint-7 close-out rows above (`0976877`) |

---

## Core design statement

> **Move PhD application from "look at rankings and brand names" to
> "match by real evidence in an advisor network".**

Every architectural decision in this repo should answer to that line. If
a feature makes the matcher prettier but doesn't push *evidence* into
*decision*, it's the wrong feature.
