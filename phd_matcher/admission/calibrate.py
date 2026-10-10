"""Refit the estimator against real admit / reject outcomes.

The defaults in data/admission/priors.yaml are priors. Once a set of real
outcomes exists (your own cycle, classmates', a cleaned GradCafe /
一亩三分地 export…), this module fits two global parameters by maximum a
posteriori estimation:

  intercept_shift   moves every estimate up or down in log-odds
                    (are the base rates too optimistic / pessimistic?)
  beta_multiplier   scales how much the applicant index matters
                    (does a stronger file help more or less than assumed?)

Priors keep small datasets from swinging the model: intercept_shift ~
N(0, 0.5²), beta_multiplier ~ N(1, 0.3²). The fit is a grid search over
the probit-approximated likelihood (two parameters, so a grid is exact
enough and dependency-free — it also runs in Pyodide).

Outcome record: {"applicant": AdmissionApplicant, "target": AdmissionTarget,
                 "admitted": bool}
"""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from phd_matcher.admission.estimator import (
    LAPSE_HIGH,
    LAPSE_LOW,
    _sigmoid,
    logit_components,
    prepare,
)
from phd_matcher.admission.models import AdmissionApplicant, AdmissionTarget
from phd_matcher.admission.priors import load_priors

SHIFT_PRIOR_SD = 0.5
MULT_PRIOR_SD = 0.3
MIN_RECOMMENDED_OUTCOMES = 30


class Outcome(BaseModel):
    applicant: AdmissionApplicant
    target: AdmissionTarget
    admitted: bool

    model_config = ConfigDict(extra="forbid")


def _prob(a: float, c: float, resid: float, shift: float, mult: float) -> float:
    kappa = math.sqrt(1 + math.pi * resid / 8)
    p = LAPSE_LOW + (1 - LAPSE_LOW - LAPSE_HIGH) * _sigmoid((a + shift + mult * c) / kappa)
    return min(max(p, 1e-6), 1 - 1e-6)


def calibrate(outcomes: list[Outcome], *, data_dir: str | Path | None = None) -> dict:
    if not outcomes:
        raise ValueError("no outcomes to calibrate against")
    comps = [
        (*logit_components(prepare(o.applicant, o.target, data_dir=data_dir)), o.admitted)
        for o in outcomes
    ]

    def score(shift: float, mult: float) -> tuple[float, float, float]:
        ll = brier = 0.0
        for a, c, resid, y in comps:
            p = _prob(a, c, resid, shift, mult)
            ll += math.log(p if y else 1 - p)
            brier += (p - (1.0 if y else 0.0)) ** 2
        n = len(comps)
        return ll, -ll / n, brier / n

    best = (-math.inf, 0.0, 1.0)
    for i in range(-30, 31):
        shift = i * 0.05
        for j in range(6, 41):
            mult = j * 0.05
            ll, _, _ = score(shift, mult)
            post = (ll - 0.5 * (shift / SHIFT_PRIOR_SD) ** 2
                    - 0.5 * ((mult - 1.0) / MULT_PRIOR_SD) ** 2)
            if post > best[0]:
                best = (post, shift, mult)
    _, shift, mult = best
    _, ll0, br0 = score(0.0, 1.0)
    _, ll1, br1 = score(shift, mult)

    current = load_priors(data_dir)
    new_shift = round(current.intercept_shift + shift, 3)
    new_mult = round(current.beta_multiplier * mult, 3)
    warnings = []
    if len(outcomes) < MIN_RECOMMENDED_OUTCOMES:
        warnings.append(
            f"only {len(outcomes)} outcomes — the fit leans heavily on the priors; "
            f"{MIN_RECOMMENDED_OUTCOMES}+ are recommended"
        )
    return {
        "n_outcomes": len(outcomes),
        "n_admitted": sum(1 for o in outcomes if o.admitted),
        "fitted_relative": {"intercept_shift": shift, "beta_multiplier": mult},
        "calibration_block": {"intercept_shift": new_shift, "beta_multiplier": new_mult},
        "log_loss": {"before": round(ll0, 4), "after": round(ll1, 4)},
        "brier": {"before": round(br0, 4), "after": round(br1, 4)},
        "yaml": (f"calibration:\n  intercept_shift: {new_shift}\n"
                 f"  beta_multiplier: {new_mult}\n"),
        "warnings": warnings,
    }
