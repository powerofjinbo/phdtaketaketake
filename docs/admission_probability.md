# Admission probability estimator

> 中文概要：输入目标学校（可选：目标导师）和个人背景，输出该项目给你 offer 的概率（0–100%），
> 附 80% 区间、各因素贡献（百分点）和能提高概率的具体动作。算法以真实录取率为锚点，
> 把你放进该层级申请池里比较，用"未知申请人恰好得到基准录取率"的方式自动校准；
> 缺失或未经证实的信息不会被猜测，而是让区间变宽。

`phd_matcher.admission` answers one question per target: **what is the
probability that this program (with this professor) makes me an offer?**
It is deliberately separate from the matcher. The matcher ranks many
candidates on a 4.0 relative-fit index; this module produces a calibrated
probability for a short list the user already cares about.

## Inputs

`AdmissionApplicant` — required: `gpa_raw` + `gpa_scale`, `transcript`
(course lines), `publications` (an explicit `[]` means "none"),
`research_interests`, `application_direction`. Optional: GRE General,
Subject GRE, current advisors, research experiences, letter writers,
international status, external fellowship, undergraduate tier, and
`sop` — a structured reading of the uploaded statement of purpose.

`AdmissionTarget` — a school (`school_tier`) and optionally `pi`, a
professor researched exactly like a matcher `CandidateAdvisor` (connection
paths, research fit, recruiting / opportunity signals, program profile).
Optional `stats` holds a program admit rate with its citation; `stage`
(`pre_application` / `interview` / `waitlist`) and `contact_status`
(prior contact with the PI) refine the estimate.

## Algorithm

### 1. Anchor on a base rate

`p0` = P(offer) for a random applicant to this program. In order of
preference: a cited program statistic (`offers / applicants`), an uncited
one (used, but with a wider prior), or the field × tier prior in
`data/admission/priors.yaml`, nudged by known cohort size and funding
model. Interview and waitlist stages swap in P(offer | interview) and
P(offer | waitlist).

### 2. Place the applicant in the pool

Seven factors become z-scores against the *typical applicant to that tier*
(pools self-select, so the same file is further above the pool at a
top-60 program than at a top-10 one). The four applicant factors are the
matcher's applicant model v2 sub-scores (`scoring.applicant.assess_applicant`,
see `references/applicant_model.md`), so the matcher and the estimator
describe you the same way:

| Factor | Source | Notes |
|---|---|---|
| research | v2 `research_output_score` | publications are a required answer |
| experience | v2 `research_experience_score` | best experience plus depth, role and field relevance |
| academic | v2 `academic_score` | GPA in context: core-course GPA from the transcript, class rank, trend, graduate courses and the undergraduate institution offset; threshold-shaped (positive z counts half) |
| letters | v2 `letters_score` | writer standing × relationship; fewer than three letters widen the factor instead of lowering it |
| sop | uploaded SOP | LLM reading → always *uncertain* |
| connection | `connection.path_strength` | to *this* PI, via your advisors |
| fit | `research_fit` | keyword overlap fallback is *uncertain* |

How the estimator's inputs map onto the v2 profile: the transcript's core
courses become `major_gpa_raw` (on the applicant's own GPA scale; a
percentage on the 100 scale), graduate courses at B+ or above become
`graduate_course_count`, and a late-minus-early grade difference beyond
±0.15 becomes a rising / falling `gpa_trend`. `class_rank_percentile`
becomes a `ClassRank`. `undergrad_tier` maps elite → elite, strong →
strong, regular → good, unknown → not set. Letter writers become
recommenders: field_leader → world_class, established → top_us,
junior_or_unknown → good_us_or_985; a research supervisor is
`research_supervisor`, anyone else `course_instructor`. The undergraduate
institution is no longer a separate factor, since the academic score
already includes it.

The applicant index is `S = Σ a_k z_k`. Weights depend on who decides:

| | connection | fit | research | academic | letters | experience | sop |
|---|---|---|---|---|---|---|---|
| PI decides (direct admit) | **0.22** | 0.17 | 0.17 | 0.16 | 0.13 | 0.10 | 0.05 |
| Committee (rotation / centralized) | 0.15 | 0.07 | 0.20 | **0.23** | 0.17 | 0.13 | 0.05 |

When the program's admission model is unknown the estimator mixes the two
with a field prior (CS mostly direct admit, biology / math mostly
committee). Optional GRE scores add a small term only when reported.

### 3. Calibrate by construction

```
P(offer) = ε_lo + (1 − ε_lo − ε_hi) · σ(b + β·(S − s_stage) + shifts + noise)
```

β = 2.5 logits per index unit. The intercept `b` is solved so that the
average over the whole applicant pool equals `p0`:

```
b = κ · logit((p0 − ε_lo) / (1 − ε_lo − ε_hi)),
κ = √(1 + π/8 · (β²·Var(S) + σ²_base + σ²_model + σ²_intl))
```

(probit approximation of the logistic-normal mean; `Var(S)` comes from the
one-factor pool model below). Consequence: an applicant we know nothing
about gets exactly the base rate, and each factor moves the estimate only
as far as it moves the applicant away from the pool. ε_hi = 5% caps any
pre-application estimate at 95%.

### 4. Shifts (log-odds)

* International status: odds ratio 0.6 vs. domestic by default, or
  `0.35 + 0.65 · international_friendliness` when the program profile has
  it; split ± around the pooled base rate.
* Secured external fellowship: +0.5 (direct admit) / +0.25 (committee),
  +0.2 more for PI-grant-funded programs.
* PI side (full weight when the PI decides, 0.35× in committee programs):
  recruiting / opportunity score, prior contact (`positive_reply` +0.5,
  `meeting_held` +0.9, `pi_invited_application` +1.4, no reply −0.1), and
  PI popularity (high-profile labs: −0.1 / −0.25, more applicants per slot).
  A PI who is not recruiting closes the direct-admit route.

### 5. Two outcomes for committee programs

In rotation / centralized programs the department makes the offer and the
lab is chosen later. The estimator reports `probability` (offer) and
`probability_with_pi` = P(offer) × P(joining this PI | offer), where the
second factor is driven by fit, connection and the PI's capacity.

### 6. Uncertainty

Monte Carlo (3000 draws, seeded per factor so results are reproducible)
over: the base rate, the admission model, β, unseen parts of the file
(shared across programs) and committee idiosyncrasy (per program),
unverified claims (shrunk halfway to the pool, wide sd), and missing
factors. Missing applicant factors are imputed through a one-factor model
(pool correlation ρ = 0.4): strong known factors pull the imputed value
up, but only partially, and the remaining spread widens the interval.
`probability` is the posterior mean; `interval_80` is the 10th–90th
percentile.

### 7. Portfolio

`estimate_portfolio` shares the applicant-level draws across targets, so
P(at least one offer) reflects that the same unknowns affect every
application. The naive independent figure is reported next to it.

## Outputs

`probability`, `interval_80`, `probability_with_pi`, `verdict`
(long_shot < 5% ≤ reach < 15% ≤ possible < 35% ≤ competitive < 60% ≤
strong), `confidence` (A–D from interval width, base-rate source and
missing inputs), `pool_percentile`, `factors` (each with its z and the
percentage-point change versus an average applicant on that factor),
`levers` (what-ifs: positive reply from the PI, a secured fellowship, a
first-author submission), `missing_inputs` and `warnings`.

## Calibration against real outcomes

The parameters are priors. With real outcomes (your cycle, classmates',
a cleaned forum export) run:

```
phdtaketaketake-admission --calibrate outcomes.json
```

It fits a global intercept shift and a slope multiplier (MAP with priors
N(0, 0.5²) and N(1, 0.3²)), reports log loss and Brier score before and
after, and prints the `calibration:` block for `priors.yaml`. 30+ outcomes
are recommended.

## Honesty contract

* Every number is an estimate with an interval, never a promise.
* Facts about a professor or program still need cited evidence. Uncited
  claims are used at half strength with wide uncertainty; missing facts
  widen the interval instead of being guessed.
* The default base rates are approximate. A cited department statistic
  is the single biggest accuracy improvement for any target.

## Integration points

* CLI: `phdtaketaketake-admission --applicant-file … --targets-file …`
* Python: `phd_matcher.admission.estimate_admission / estimate_portfolio`
* Web worker: `phd_matcher.admission.api.estimate_admission_json(applicant_json, targets_json, "/eng/data")`
