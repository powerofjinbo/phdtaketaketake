"""Admission-probability estimator (school + optional professor → P(offer)).

Separate from the matcher's relative-fit index: the matcher ranks many
candidates on a 4.0 scale; this module answers one question per target —
the probability of an offer — anchored on base rates and calibrated so an
unknown applicant gets exactly the base rate. See `estimator.py`.
"""

from phd_matcher.admission.estimator import estimate_admission, estimate_portfolio
from phd_matcher.admission.models import (
    AdmissionApplicant,
    AdmissionEstimate,
    AdmissionTarget,
    PortfolioEstimate,
)

__all__ = [
    "AdmissionApplicant",
    "AdmissionEstimate",
    "AdmissionTarget",
    "PortfolioEstimate",
    "estimate_admission",
    "estimate_portfolio",
]
