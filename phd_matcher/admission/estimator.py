"""Admission-probability estimator.

Answers: "given my background, what is the probability that program X
(with professor Y) makes me an offer?" — as a number in [0, 100%], with an
80% interval, a factor breakdown and the levers that would move it.

Algorithm (see docs/admission_probability.md for the full derivation)
--------------------------------------------------------------------

1. **Anchor on a base rate.** Start from P(offer) for a random applicant
   to this program: a verified program statistic when the agent found one,
   otherwise the field × tier prior in data/admission/priors.yaml (nudged
   by known cohort-size / funding facts). Interview and waitlist stages
   swap in post-interview / waitlist rates.

2. **Place the applicant in the pool.** Nine factors become z-scores
   against the typical applicant to that tier (features.py): research
   output, research experience, GPA, core coursework, undergraduate
   institution, letters, SOP, network connection to the PI, research fit.
   Their weighted sum is the applicant index S. Weights depend on who
   decides: a direct-admit PI weighs connection and fit most; a committee
   weighs research output and letters most. When the admission model is
   unknown the estimator mixes both, using a field prior.

3. **Calibrate by construction.** P(offer) = ε_lo + (1−ε_lo−ε_hi)·σ(b + β·S
   + shifts). The intercept b is solved so that averaging over the whole
   applicant pool reproduces the base rate exactly (probit approximation
   of the logistic-normal mean). A completely unknown applicant therefore
   gets the base rate, and every factor moves the estimate only as far as
   it moves the applicant away from the pool. ε_hi = 5% caps any pre-
   application estimate at 95%: no PhD admission is certain.

4. **Shifts** for things that are not applicant quality: international
   status (odds ratio, softened by the program's international track
   record), a secured external fellowship, and — for the named PI — the
   recruiting / funding signal, prior contact with the PI and the PI's
   popularity (famous labs see more competition per slot). A PI who is
   not recruiting effectively closes the direct-admit route.

5. **Two outcomes for committee programs.** In rotation / centralized
   programs the offer comes from the department; joining the named PI's
   group is a second step driven by fit, connection and lab capacity.
   The estimator reports P(offer) and P(offer AND joining this PI).

6. **Uncertainty is propagated, not hidden.** Monte Carlo over: the base
   rate, the admission model, the slope β, unmodelled factors, unverified
   claims (shrunk, wide), and missing factors — which are imputed from the
   known ones through a one-factor model (strong applicants tend to be
   strong across the board), never assumed best- or worst-case. The point
   estimate is the posterior mean; the interval is the 10th–90th
   percentile. Draws are seeded per factor, so results are reproducible
   and portfolio estimates share the applicant's latent strength across
   targets (P(at least one offer) is *not* computed as if independent).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from pathlib import Path
from statistics import NormalDist

from phd_matcher.admission.features import (
    BonusFeature,
    Feature,
    build_features,
    to_student_profile,
)
from phd_matcher.admission.models import (
    AdmissionApplicant,
    AdmissionEstimate,
    AdmissionTarget,
    ConfidenceGrade,
    FactorContribution,
    Lever,
    PortfolioEstimate,
    Verdict,
)
from phd_matcher.admission.priors import DEFAULT_DATA_DIR, FieldPriors, load_priors
from phd_matcher.matching.ranker import evidence_coverage
from phd_matcher.models import Paper
from phd_matcher.scoring import advisor, opportunity

_N = NormalDist()

# ---- Index weights (sum to 1 within each admission model) ----------------
# Direct admit: the PI decides — connection is the largest single weight
# (connection-first), then fit and research output.
# Committee: a faculty committee reads the file — research output and
# letters lead; connection to one PI still matters (it shapes the letters
# the committee trusts) but less.
WEIGHTS: dict[str, dict[str, float]] = {
    "direct": {
        "connection": 0.21, "fit": 0.16, "research": 0.16, "letters": 0.12,
        "experience": 0.10, "coursework": 0.08, "gpa": 0.07, "pedigree": 0.05, "sop": 0.05,
    },
    "committee": {
        "research": 0.19, "letters": 0.16, "connection": 0.14, "experience": 0.12,
        "coursework": 0.11, "gpa": 0.10, "pedigree": 0.07, "fit": 0.06, "sop": 0.05,
    },
}

BETA = 2.5            # logit per unit of applicant index
BETA_SD = 0.25
# Unmodelled factors, split by whether they follow the applicant around.
# SHARED: what the estimator cannot see in the file itself (letter content,
# SOP prose, interview skill) — identical for every program, which is what
# makes outcomes across programs correlated. TARGET: committee taste,
# that year's lab needs, luck — independent per program.
SIGMA_SHARED = 0.35
SIGMA_TARGET = 0.25
SIGMA_MODEL = math.sqrt(SIGMA_SHARED ** 2 + SIGMA_TARGET ** 2)
LAPSE_LOW = 0.003
LAPSE_HIGH = 0.05

BASE_SD = {
    "verified_program_stat": 0.15,
    "unverified_program_stat": 0.30,
    "field_tier_prior": 0.40,
}

# stage → (beta scale, pool index shift, pool sd scale). Interviewees and
# waitlisted applicants are already a selected, stronger, more homogeneous
# pool — the CV matters less once you are in the room.
STAGES: dict[str, tuple[float, float, float]] = {
    "pre_application": (1.0, 0.0, 1.0),
    "interview": (0.5, 0.6, 0.7),
    "waitlist": (0.3, 0.8, 0.6),
}

INTL_ODDS_RATIO = 0.6
FELLOWSHIP_SHIFT = {"direct": 0.5, "committee": 0.25}
FELLOWSHIP_PI_FUNDED_BONUS = 0.2

CONTACT_SHIFT = {
    "none": 0.0,
    "emailed_no_reply": -0.1,
    "positive_reply": 0.5,
    "meeting_held": 0.9,
    "pi_invited_application": 1.4,
}
PI_SHIFT_IN_COMMITTEE = 0.35
NOT_RECRUITING_DIRECT = -6.0
NOT_RECRUITING_LAB = -4.0
LAB_FIT_SLOPE = 1.2

DEFAULT_SAMPLES = 3000
DEFAULT_SEED = 20261010


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _index_var(weights: dict[str, float], feats: list[Feature]) -> float:
    """Pool variance of S under the one-factor model:
    Var(S) = (Σ a·λ)² + Σ a²·(1 − λ²)."""
    common = sum(weights[f.key] * f.loading for f in feats)
    unique = sum(weights[f.key] ** 2 * (1 - f.loading ** 2) for f in feats)
    return common ** 2 + unique


# ---------------------------------------------------------------------------
# Random draws — seeded per key, so adding a factor never reshuffles others
# and portfolio targets share the applicant's draws.
# ---------------------------------------------------------------------------

class Draws:
    def __init__(self, n: int = DEFAULT_SAMPLES, seed: int = DEFAULT_SEED):
        self.n = n
        self.seed = seed
        self._normal: dict[str, list[float]] = {}
        self._uniform: dict[str, list[float]] = {}

    def normal(self, key: str) -> list[float]:
        if key not in self._normal:
            rng = random.Random(f"{self.seed}:n:{key}")
            self._normal[key] = [rng.gauss(0.0, 1.0) for _ in range(self.n)]
        return self._normal[key]

    def uniform(self, key: str) -> list[float]:
        if key not in self._uniform:
            rng = random.Random(f"{self.seed}:u:{key}")
            self._uniform[key] = [rng.random() for _ in range(self.n)]
        return self._uniform[key]


# ---------------------------------------------------------------------------
# Preparation: everything deterministic about one (applicant, target)
# ---------------------------------------------------------------------------

@dataclass
class Prepared:
    applicant: AdmissionApplicant
    target: AdmissionTarget
    fp: FieldPriors
    features: list[Feature]
    bonus: list[BonusFeature]
    p_direct: float
    base_rate: float
    base_source: str
    base_sd: float
    program_shift: float
    intl_known: bool | None
    intl_magnitude: float
    funding: dict[str, float]
    pi_mean: float
    pi_sd: float
    popularity: float
    not_recruiting: bool
    beta: float
    pool_shift: float
    pool_sd_scale: float
    intercept: dict[str, float]
    adjustments: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _base_rate(target: AdmissionTarget, fp: FieldPriors, priors, adjustments: list[str],
               warnings: list[str]) -> tuple[float, str]:
    tier = target.tier
    if target.stage == "interview":
        rate = priors.post_interview_rates[tier]
        adjustments.append(f"interview stage: base rate P(offer | interview) ≈ {rate:.0%}")
        return rate, "field_tier_prior"
    if target.stage == "waitlist":
        rate = priors.waitlist_rates[tier]
        adjustments.append(f"waitlist stage: base rate P(offer | waitlist) ≈ {rate:.0%}")
        return rate, "field_tier_prior"

    stats = target.stats
    if stats is not None and stats.admit_rate is not None:
        rate = stats.admit_rate
        verified = stats.evidence is not None and stats.evidence.has_evidence_for(
            "admission:admit_rate")
        if not verified:
            warnings.append("program admit rate has no cited source — treated as uncertain")
        year = f" ({stats.cycle_year})" if stats.cycle_year else ""
        adjustments.append(f"program admit rate {rate:.1%}{year}")
        return rate, ("verified_program_stat" if verified else "unverified_program_stat")

    rate = fp.base_rates[tier]
    shift = 0.0
    pp = target.effective_program_profile
    if pp is not None:
        if pp.cohort_size_estimate is not None:
            if pp.cohort_size_estimate < 8:
                shift -= 0.2
                adjustments.append(f"small cohort ({pp.cohort_size_estimate}/yr): harder")
            elif pp.cohort_size_estimate >= 30:
                shift += 0.1
                adjustments.append(f"large cohort ({pp.cohort_size_estimate}/yr): easier")
        if pp.funding_structure == "fellowship_first":
            shift -= 0.3
            adjustments.append("program expects outside fellowship funding: harder")
        elif pp.funding_structure == "pi_grant":
            shift -= 0.1
            adjustments.append("PI-grant funded slots: slightly harder")
    rate = _sigmoid(_logit(rate) + shift)
    warnings.append(
        f"no program-specific admit rate — using the {fp.field_id} × {tier} prior "
        f"({fp.base_rates[tier]:.0%}); a cited department statistic narrows the interval"
    )
    return rate, "field_tier_prior"


def prepare(
    applicant: AdmissionApplicant,
    target: AdmissionTarget,
    *,
    data_dir: str | Path | None = None,
) -> Prepared:
    data_path = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    priors = load_priors(data_path)
    fp = priors.for_field(target.field or applicant.field, data_path)
    feats, bonus = build_features(applicant, target, fp, data_path)

    adjustments: list[str] = []
    warnings: list[str] = []
    missing = [f"{f.label}: {f.note}" for f in feats if f.state == "missing"]

    base_rate, base_source = _base_rate(target, fp, priors, adjustments, warnings)
    base_sd = BASE_SD[base_source]
    beta_scale, pool_shift, pool_sd_scale = STAGES[target.stage]

    # ---- Who decides -----------------------------------------------------
    pp = target.effective_program_profile
    if pp is not None and (pp.admission_model == "direct_admit" or pp.direct_admit_required):
        p_direct = 0.95
    elif pp is not None and pp.admission_model in ("rotation", "centralized"):
        p_direct = 0.05
    elif pp is not None and pp.admission_model == "mixed":
        p_direct = 0.5
    else:
        p_direct = fp.admission_model_prior
        missing.append(f"Admission model: unknown — assuming {p_direct:.0%} PI-decides "
                       f"(field prior for {fp.field_id})")

    # ---- International status -------------------------------------------
    odds_ratio = INTL_ODDS_RATIO
    if pp is not None and pp.international_friendliness is not None:
        odds_ratio = 0.35 + 0.65 * pp.international_friendliness
    intl_mag = -0.5 * math.log(odds_ratio)
    if applicant.is_international is None:
        missing.append("International status: not given")
    elif applicant.is_international and intl_mag > 0.01:
        adjustments.append(f"international applicant: odds × {math.exp(-intl_mag):.2f} "
                           "vs. the pooled base rate")

    # ---- External funding ------------------------------------------------
    funding = {"direct": 0.0, "committee": 0.0}
    if applicant.external_fellowship == "secured":
        extra = FELLOWSHIP_PI_FUNDED_BONUS if (
            pp is not None and pp.funding_structure in ("pi_grant", "fellowship_first")) else 0.0
        funding = {k: v + extra for k, v in FELLOWSHIP_SHIFT.items()}
        name = applicant.fellowship_name or "external fellowship"
        adjustments.append(f"{name} secured: brings its own funding")

    # ---- PI-side signals -------------------------------------------------
    pi_mean, pi_sd, popularity, not_recruiting = 0.0, 0.0, 0.0, False
    pi = target.pi
    if pi is not None:
        not_recruiting = opportunity.is_not_recruiting(pi)
        if not_recruiting:
            warnings.append(f"{pi.name} is marked not recruiting this cycle")
        o_score, _, _ = opportunity.compute_opportunity_state(pi)
        cov = evidence_coverage(to_student_profile(applicant), pi)
        unsourced_pi = "pi_signal" in cov.unsourced_names
        if o_score is not None:
            o_shift = max(-0.8, min(0.5, 1.6 * (o_score - 0.55)))
            o_sd = 0.3 if unsourced_pi else 0.15
            adjustments.append(f"PI opportunity score {o_score:.2f}: {o_shift:+.2f} logit")
        else:
            sig = opportunity.effective_pi_signal(pi)
            o_shift = {"strong": 0.4, "normal": 0.0, "shrinking": -0.6}.get(sig, 0.0)
            o_sd = 0.4 if sig == "missing" or unsourced_pi else 0.15
            if sig == "missing":
                missing.append("PI recruiting status: not verified")
            elif sig != "not_recruiting":
                adjustments.append(f"PI recruiting signal '{sig}': {o_shift:+.2f} logit")
        if unsourced_pi:
            o_shift *= 0.5
        k_shift = CONTACT_SHIFT[target.contact_status] * beta_scale
        if target.contact_status != "none":
            adjustments.append(f"contact with PI '{target.contact_status}': {k_shift:+.2f} logit")
        pi_mean, pi_sd = o_shift + k_shift, o_sd
        a = advisor.advisor_strength(pi.model_dump())
        if a >= 3.7:
            popularity = -0.25
        elif a >= 3.3:
            popularity = -0.1
        if popularity:
            adjustments.append(f"high-profile PI (more applicants per slot): {popularity:+.2f}")

    beta = BETA * priors.beta_multiplier * beta_scale
    intercept: dict[str, float] = {}
    p_adj = (base_rate - LAPSE_LOW) / (1 - LAPSE_LOW - LAPSE_HIGH)
    for model, w in WEIGHTS.items():
        sd_s = math.sqrt(_index_var(w, feats)) * pool_sd_scale
        total_var = (beta * sd_s) ** 2 + base_sd ** 2 + SIGMA_MODEL ** 2 + intl_mag ** 2
        kappa = math.sqrt(1 + math.pi * total_var / 8)
        intercept[model] = kappa * _logit(p_adj) + priors.intercept_shift

    return Prepared(
        applicant=applicant, target=target, fp=fp, features=feats, bonus=bonus,
        p_direct=p_direct, base_rate=base_rate, base_source=base_source, base_sd=base_sd,
        program_shift=0.0, intl_known=applicant.is_international, intl_magnitude=intl_mag,
        funding=funding, pi_mean=pi_mean, pi_sd=pi_sd, popularity=popularity,
        not_recruiting=not_recruiting, beta=beta, pool_shift=pool_shift,
        pool_sd_scale=pool_sd_scale, intercept=intercept, adjustments=adjustments,
        missing_inputs=missing, warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def _g_posterior(feats: list[Feature]) -> tuple[float, float]:
    precision, num = 1.0, 0.0
    for f in feats:
        if f.loading <= 0 or f.state == "missing":
            continue
        v = (1 - f.loading ** 2) + f.sd ** 2
        precision += f.loading ** 2 / v
        num += f.loading * f.mean / v
    return num / precision, 1.0 / math.sqrt(precision)


def _feature_samples(prep: Prepared, f: Feature, draws: Draws, g: list[float]) -> list[float]:
    key = f"applicant:{f.key}" if f.loading > 0 else f"{prep.target.id}:{f.key}"
    eps = draws.normal(key)
    if f.state == "missing":
        lam, rest = f.loading, math.sqrt(1 - f.loading ** 2)
        return [lam * gs + rest * e for gs, e in zip(g, eps, strict=True)]
    return [f.mean + f.sd * e for e in eps]


def simulate(prep: Prepared, draws: Draws) -> tuple[list[float], list[float] | None]:
    """Return per-sample (P(offer), P(offer ∧ this PI's group) or None)."""
    n = draws.n
    tid = prep.target.id
    gmean, gsd = _g_posterior(prep.features)
    g = [gmean + gsd * e for e in draws.normal("applicant:g")]

    s_direct = [0.0] * n
    s_comm = [0.0] * n
    z_fit: list[float] | None = None
    z_conn: list[float] | None = None
    for f in prep.features:
        zs = _feature_samples(prep, f, draws, g)
        wd, wc = WEIGHTS["direct"][f.key], WEIGHTS["committee"][f.key]
        for i, z in enumerate(zs):
            s_direct[i] += wd * z
            s_comm[i] += wc * z
        if f.key == "fit":
            z_fit = zs
        elif f.key == "connection":
            z_conn = zs
    bonus = sum(b.weight * b.z for b in prep.bonus)

    eps_beta = draws.normal("applicant:beta")
    eps_base = draws.normal(f"{tid}:base")
    eps_shared = draws.normal("applicant:unseen")
    eps_noise = draws.normal(f"{tid}:noise")
    eps_pi = draws.normal(f"{tid}:pi")
    u_model = draws.uniform(f"{tid}:admission_model")
    u_intl = draws.uniform("applicant:international")

    has_pi = prep.target.pi is not None
    beta_sd = BETA_SD * prep.beta / BETA
    scale = 1 - LAPSE_LOW - LAPSE_HIGH
    offers: list[float] = []
    with_pi: list[float] | None = [] if has_pi else None
    for i in range(n):
        direct = u_model[i] < prep.p_direct
        model = "direct" if direct else "committee"
        s = s_direct[i] if direct else s_comm[i]
        beta = prep.beta + beta_sd * eps_beta[i]
        if prep.intl_known is None:
            intl = -prep.intl_magnitude if u_intl[i] < 0.5 else prep.intl_magnitude
        else:
            intl = -prep.intl_magnitude if prep.intl_known else prep.intl_magnitude
        logit = (prep.intercept[model] + prep.base_sd * eps_base[i]
                 + beta * (s - prep.pool_shift + bonus)
                 + intl + prep.funding[model]
                 + SIGMA_SHARED * eps_shared[i] + SIGMA_TARGET * eps_noise[i])
        pi_shift = prep.pi_mean + prep.pi_sd * eps_pi[i]
        if has_pi:
            if direct:
                logit += pi_shift + prep.popularity
                if prep.not_recruiting:
                    logit += NOT_RECRUITING_DIRECT
            else:
                logit += PI_SHIFT_IN_COMMITTEE * pi_shift
        p_offer = LAPSE_LOW + scale * _sigmoid(logit)
        offers.append(p_offer)
        if with_pi is not None:
            if direct:
                with_pi.append(p_offer)
            else:
                assert z_fit is not None and z_conn is not None
                q = LAB_FIT_SLOPE * (0.55 * z_fit[i] + 0.45 * z_conn[i]) + pi_shift
                if prep.not_recruiting:
                    q += NOT_RECRUITING_LAB
                with_pi.append(p_offer * _sigmoid(q))
    return offers, with_pi


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _interval(xs: list[float]) -> tuple[float, float]:
    s = sorted(xs)
    n = len(s)
    return (round(s[int(0.10 * (n - 1))], 4), round(s[int(0.90 * (n - 1))], 4))


def _verdict(p: float) -> Verdict:
    if p >= 0.60:
        return "strong"
    if p >= 0.35:
        return "competitive"
    if p >= 0.15:
        return "possible"
    if p >= 0.05:
        return "reach"
    return "long_shot"


def _confidence(point: float, interval: tuple[float, float], base_source: str,
                n_missing: int) -> ConfidenceGrade:
    ratio = (interval[1] - interval[0]) / (point + 0.05)
    if base_source == "verified_program_stat" and ratio < 0.9 and n_missing <= 1:
        return "A"
    if ratio < 1.3 and n_missing <= 3:
        return "B"
    if ratio < 1.9:
        return "C"
    return "D"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _hypothetical_levers(applicant: AdmissionApplicant, target: AdmissionTarget
                         ) -> list[tuple[str, str, str, AdmissionApplicant, AdmissionTarget]]:
    out = []
    if target.pi is not None and target.contact_status in ("none", "emailed_no_reply"):
        out.append(("contact_pi", "Get a positive reply from the PI before applying",
                    "联系导师并获得积极回复", applicant,
                    target.model_copy(update={"contact_status": "positive_reply"})))
    if applicant.external_fellowship != "secured":
        out.append(("fellowship", "Secure an external fellowship (e.g. NSF GRFP / CSC)",
                    "拿到外部奖学金（如 NSF GRFP / CSC）",
                    applicant.model_copy(update={"external_fellowship": "secured"}), target))
    has_first = any(p.author_position == 1 or p.author_role in ("first", "co_first")
                    for p in applicant.publications)
    if not has_first:
        paper = Paper(title="(hypothetical) first-author manuscript", journal="",
                      journal_tier=2, author_position=1, status="submitted")
        out.append(("first_author_paper", "Submit a first-author paper before the deadline",
                    "截止前投出一篇一作论文",
                    applicant.model_copy(update={"publications": [*applicant.publications, paper]}),
                    target))
    return out


def estimate_admission(
    applicant: AdmissionApplicant,
    target: AdmissionTarget,
    *,
    data_dir: str | Path | None = None,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    draws: Draws | None = None,
    with_levers: bool = True,
) -> AdmissionEstimate:
    draws = draws or Draws(samples, seed)
    prep = prepare(applicant, target, data_dir=data_dir)
    offers, with_pi = simulate(prep, draws)
    point = _mean(offers)

    # Factor contributions: re-run with the factor set to the pool average.
    factors: list[FactorContribution] = []
    gmean, _ = _g_posterior(prep.features)
    w_mix = {k: prep.p_direct * WEIGHTS["direct"][k] + (1 - prep.p_direct) * WEIGHTS["committee"][k]
             for k in WEIGHTS["direct"]}
    index = 0.0
    for idx, f in enumerate(prep.features):
        avg = Feature(f.key, f.label, f.label_zh, "known", 0.0, 0.0, f.loading)
        alt = replace(prep, features=[*prep.features[:idx], avg, *prep.features[idx + 1:]])
        delta = point - _mean(simulate(alt, draws)[0])
        z = f.mean if f.state != "missing" else f.loading * gmean
        index += w_mix[f.key] * z
        factors.append(FactorContribution(
            key=f.key, label=f.label, label_zh=f.label_zh, state=f.state, z=round(z, 2),
            weight=round(w_mix[f.key], 3), delta_pp=round(100 * delta, 1), note=f.note,
        ))
    for b in prep.bonus:
        alt = replace(prep, bonus=[x for x in prep.bonus if x.key != b.key])
        delta = point - _mean(simulate(alt, draws)[0])
        factors.append(FactorContribution(
            key=b.key, label=b.label, label_zh=b.label_zh, state="known", z=round(b.z, 2),
            weight=b.weight, delta_pp=round(100 * delta, 1), note=b.note,
        ))
    factors.sort(key=lambda c: -abs(c.delta_pp))

    levers: list[Lever] = []
    if with_levers:
        for key, label, label_zh, app2, tgt2 in _hypothetical_levers(applicant, target):
            p2 = _mean(simulate(prepare(app2, tgt2, data_dir=data_dir), draws)[0])
            if p2 - point > 0.005:
                levers.append(Lever(
                    key=key, label=label, label_zh=label_zh,
                    probability=round(p2, 4), delta_pp=round(100 * (p2 - point), 1),
                ))
        levers.sort(key=lambda lv: -lv.delta_pp)

    var_mix = (prep.p_direct * _index_var(WEIGHTS["direct"], prep.features)
               + (1 - prep.p_direct) * _index_var(WEIGHTS["committee"], prep.features))
    interval = _interval(offers)
    n_missing = sum(1 for f in prep.features if f.state == "missing")
    return AdmissionEstimate(
        target_id=target.id,
        institution=target.institution,
        program=target.program,
        pi_name=target.pi.name if target.pi is not None else None,
        stage=target.stage,
        probability=round(point, 4),
        interval_80=interval,
        probability_with_pi=round(_mean(with_pi), 4) if with_pi is not None else None,
        interval_80_with_pi=_interval(with_pi) if with_pi is not None else None,
        verdict=_verdict(point),
        confidence=_confidence(point, interval, prep.base_source, n_missing),
        base_rate=round(prep.base_rate, 4),
        base_rate_source=prep.base_source,  # type: ignore[arg-type]
        p_pi_decides=round(prep.p_direct, 2),
        applicant_index=round(index, 2),
        pool_percentile=round(_N.cdf(index / math.sqrt(var_mix)), 3),
        factors=factors,
        adjustments=prep.adjustments,
        levers=levers,
        missing_inputs=prep.missing_inputs,
        warnings=prep.warnings,
    )


def estimate_portfolio(
    applicant: AdmissionApplicant,
    targets: list[AdmissionTarget],
    *,
    data_dir: str | Path | None = None,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    with_levers: bool = True,
) -> PortfolioEstimate:
    """Estimate every target, plus P(at least one offer).

    The targets share the applicant's draws (latent strength, missing
    factors, slope), so outcomes are positively correlated — exactly as in
    reality, where a strong file tends to win several offers and a weak
    one tends to lose everywhere. The naive independent figure is reported
    alongside to show how much that correlation matters.
    """
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("target ids must be unique")
    draws = Draws(samples, seed)
    estimates = [
        estimate_admission(applicant, t, data_dir=data_dir, draws=draws, with_levers=with_levers)
        for t in targets
    ]
    per_target = [simulate(prepare(applicant, t, data_dir=data_dir), draws)[0] for t in targets]
    none_offer = [1.0] * draws.n
    for offers in per_target:
        for i, p in enumerate(offers):
            none_offer[i] *= 1 - p
    p_any = 1 - _mean(none_offer)
    p_indep = 1 - math.prod(1 - e.probability for e in estimates)
    return PortfolioEstimate(
        estimates=estimates,
        p_at_least_one=round(p_any, 4),
        p_at_least_one_if_independent=round(p_indep, 4),
        expected_offers=round(sum(e.probability for e in estimates), 2),
        note=("P(at least one offer) accounts for correlation between programs: the same "
              "unknowns about your file affect every application."),
    )


def logit_components(prep: Prepared) -> tuple[float, float, float]:
    """Deterministic summary of one prepared target, used by calibration.

    Returns ``(a, c, residual_var)`` such that, to a probit approximation,
    P(offer) ≈ ε_lo + (1−ε_lo−ε_hi)·σ((a + c) / √(1 + π·residual_var/8)),
    where ``c`` is the applicant-index part (scaled by β) and ``a`` is
    everything else (intercept, shifts). Admission models are mixed by
    their probability.
    """
    gmean, gsd = _g_posterior(prep.features)
    has_pi = prep.target.pi is not None
    a = c = var_s = 0.0
    for model, pm in (("direct", prep.p_direct), ("committee", 1 - prep.p_direct)):
        w = WEIGHTS[model]
        s = 0.0
        vs = 0.0
        for f in prep.features:
            if f.state == "missing":
                s += w[f.key] * f.loading * gmean
                vs += w[f.key] ** 2 * (f.loading ** 2 * gsd ** 2 + 1 - f.loading ** 2)
            else:
                s += w[f.key] * f.mean
                vs += w[f.key] ** 2 * f.sd ** 2
        bonus = sum(b.weight * b.z for b in prep.bonus)
        intl = 0.0 if prep.intl_known is None else (
            -prep.intl_magnitude if prep.intl_known else prep.intl_magnitude)
        pi_term = 0.0
        if has_pi:
            if model == "direct":
                pi_term = prep.pi_mean + prep.popularity + (
                    NOT_RECRUITING_DIRECT if prep.not_recruiting else 0.0)
            else:
                pi_term = PI_SHIFT_IN_COMMITTEE * prep.pi_mean
        a += pm * (prep.intercept[model] + intl + prep.funding[model] + pi_term)
        c += pm * prep.beta * (s - prep.pool_shift + bonus)
        var_s += pm * vs
    intl_var = prep.intl_magnitude ** 2 if prep.intl_known is None else 0.0
    resid = (prep.base_sd ** 2 + SIGMA_MODEL ** 2 + prep.beta ** 2 * var_s
             + intl_var + prep.pi_sd ** 2)
    return a, c, resid
