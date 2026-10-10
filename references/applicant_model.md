# Applicant model v2 — how strong is the applicant on their own?

The v1 engine described the applicant with three numbers: P (papers), E
(the single best research experience) and G (raw GPA). Applicant model v2
(`phd_matcher/scoring/applicant.py`) replaces that with a fuller,
candidate-independent `ApplicantAssessment` built **only from facts the
user provided**. Every new input is optional. A v1 profile scores exactly
as before, except that a genuine research-side spike (a pillar ≥ 3.8) now
earns a small bonus.

## Pillars (4.0 scale)

| Pillar | What it reads | Notes |
|---|---|---|
| **G: academic record** | GPA, `major_gpa_raw`, `class_rank`, `undergrad_tier`, `gpa_trend`, `graduate_course_count`, master's GPA + `master_tier` | GPA in context: major-course GPA counts 60%, class rank is blended 50/50 when known, the institution tier adds −0.20 to +0.15, trend ±0.08/−0.12, graduate courses up to +0.12. A master's degree counts 60% against 40% for the undergraduate record. |
| **P: research output** | `papers[]` | Unchanged (best paper + depth bonus; see `publication_v2.md`). |
| **E: research experience** | `experiences[]` (+ optional `role`, `field_relevance`) | Each experience is the v1 score ± role (lead +0.15 / assistant −0.15) ± relevance (same subfield +0.10 / different −0.25). The best experience plus a depth bonus from the next two; experiences ≤ 3.0 add nothing. |
| **L: letters** *(new)* | `recommenders[]` | Per letter: 0.35 writer standing + 0.30 relationship (research supervisor 4.0 … other 2.5) + 0.15 familiarity (months known) + 0.20 expected strength. The top three letters get slot weights 0.45 / 0.35 / 0.20, renormalised over the letters described. |

When no recommenders are described, L is **unknown**, not weak. Its
weight scales with `letters_coverage` (letters described ÷ 3), so
describing a real strong letter never lowers the score. Fewer than three
letters is surfaced as a risk flag.

## Bounded bonuses (never a pillar)

- **Honors.** The best honor counts 0.15 if international, 0.10 national,
  0.05 regional and 0.02 university. Each further honor at regional level
  or above adds 0.02, capped at 0.18.
- **Tests.** Subject GRE adds +0.06 at the 90th percentile or above and
  +0.03 at the 75th or above. Below the 40th it subtracts 0.05. GRE quant
  adds +0.02 at the 90th percentile and subtracts 0.03 below the 50th. A
  TOEFL below 90, IELTS below 6.5 or Duolingo below 110 subtracts 0.08 and
  raises a screening-risk flag.
- **Spike.** One research-side pillar (P, E or L) at 3.8 or above adds
  +0.05; two add +0.08. A perfect GPA alone is not a spike.

## Composite, tier and confidence

- Stand-alone `applicant_strength` uses neutral weights P 0.30, E 0.25,
  G 0.20 and L 0.25, plus the bonuses.
- The tier label is `exceptional` at 3.70 or above, `strong` at 3.35,
  `competitive` at 3.00, and `developing` below that.
- Confidence comes from six optional input groups: high when four or more
  are provided, medium at two or three, low below that.
  `missing_inputs` lists the absent groups in plain language, so the agent
  knows what to ask next.

## Inside the matcher (CAPEG)

C and A keep their tier weights. The P/E/G slot is filled by the
tier-weighted applicant composite:

```
s_tier = (w_P·P + w_E·E + w_G·G) / (w_P+w_E+w_G)
s_tier = (1 − 0.25·cov_L)·s_tier + 0.25·cov_L·L      (when letters described)
s_tier += honors + tests + spike
match  = w_C·C + w_A·A + (w_P+w_E+w_G)·s_tier − academic_screen_penalty
```

**Academic screening floor.** The penalty is `0.40 · max(0, floor − G)`.
The floor is 3.30 for top_10, 3.10 for top_11_30, 2.90 for top_31_60 and
2.70 for top_60_plus. Below its floor a file risks being cut before the
research is read. Connections help, but they don't fully compensate.

`MatchResult` gains `l_score`, `s_score`, `academic_screen_penalty` and
the full `applicant` assessment.

## Advice built on it (`phd_matcher/matching/advice.py`)

- **`tier_readiness`.** For each tier, compares the profile's score with
  the typical admit bar there, before any PI-specific signal. The bars are
  3.55 for top_10, 3.30 for top_11_30, 3.05 for top_31_60 and 2.75 for
  top_60_plus. The verdict is above_bar, at_bar (within ±0.15) or
  below_bar.
- **`improvement_plan`.** A what-if analysis. Each realistic action is
  simulated on a copy of the profile and ranked by its gain in
  `applicant_strength`:
  - a strong research-supervisor letter
  - a first-author preprint
  - submitting in-prep manuscripts
  - extending the best project to 12 months
  - two graduate courses
  - an English retake

  Every action states its assumption. Nothing is written back, and the
  agent must only suggest actions the student can truly take.
- **`build_application_list`.** A balanced shortlist: about 25% reach,
  50% target and 25% safer by `difficulty_adjusted_strength`. It skips
  drops, keeps at most two PIs per institution, and notes when there are
  no safer options or too few candidates.

`phdtaketaketake-match` output now includes `applicant`,
`tier_readiness`, `improvement_plan` and `application_plan`
(`--list-size`, default 12).

## Data-integrity rules

- **User-provided facts only.** All v2 inputs come from the user; never
  infer a class rank, honor or recommender.
- **Expected letter strength.** Use `expected_strength="unknown"` unless
  the user says otherwise.
- **Institution tiers.** `undergrad_tier` / `master_tier` may be set by
  the agent from a cited ranking, the same way as `school_tier`.
- **What-if actions are hypothetical.** Present them as "if you can do X,
  your profile would move by Δ", never as facts on the CV.
