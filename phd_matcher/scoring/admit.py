"""Match score and application strength index — per Scoring Design v0.3.

Renamed `admit_likelihood` → `application_strength`. The score is on a 4.0
scale and represents relative fit / competitiveness, NOT a probability —
there is no historical admission data to calibrate against. See README and
docs/scoring.md for the rationale.
"""

from phd_matcher.models import StrengthLabel

# ---- Tier-adaptive weights (post-roadmap-#3 — 5-pillar CAPEG) ------------

# C · A · P · E · G. Connection still the largest pillar (connection-first).
# A (Advisor influence) is bounded so it doesn't compete with C.
# Weights sum to 1.0 within each tier.
TIER_WEIGHTS: dict[str, dict[str, float]] = {
    "top_10":      {"C": 0.38, "A": 0.17, "P": 0.27, "E": 0.10, "G": 0.08},
    "top_11_30":   {"C": 0.35, "A": 0.15, "P": 0.25, "E": 0.12, "G": 0.13},
    "top_31_60":   {"C": 0.30, "A": 0.15, "P": 0.22, "E": 0.15, "G": 0.18},
    "top_60_plus": {"C": 0.25, "A": 0.12, "P": 0.18, "E": 0.18, "G": 0.27},
}


def match_score(
    c: float, a: float, p: float, e: float, g: float, school_tier: str
) -> float:
    """Weighted combination of 5 dimensions → 4.0."""
    if school_tier not in TIER_WEIGHTS:
        raise ValueError(
            f"Unknown school tier: {school_tier!r}. Valid: {list(TIER_WEIGHTS)}"
        )
    w = TIER_WEIGHTS[school_tier]
    return w["C"] * c + w["A"] * a + w["P"] * p + w["E"] * e + w["G"] * g


# ---- Application-strength adjustments ------------------------------------

# Roadmap-#5: `tier_adj` removed. Its school-tier admit-rate role moved
# into `phd_matcher.scoring.program.program_difficulty_penalty`'s
# `school_tier_admit_rate_factor` component. `application_strength` is
# now a pure (match + pi_adj) value; school difficulty is layered on top
# via `difficulty_adjusted_strength = risk_adjusted_strength − penalty`
# (computed in the ranker).

# PI recruiting signal adjustment. Stays here for v2 commit 1; v2 commit
# 2 (Opportunity / A refactor) will rework this boundary.
PI_ADJ: dict[str, float] = {
    "strong":     +0.2,
    "normal":      0.0,
    "shrinking":  -0.4,
    "missing":    -0.1,
}

NOT_RECRUITING_SIGNAL = "not_recruiting"


# ---- Confidence band based on evidence coverage --------------------------

def confidence_band_from_unverified(unverified_count: int) -> float:
    """Wider band when more signals lack source citations.

    "Unverified" includes: missing PI signal, advisor-influence signals at
    default values without sources, empty / unsourced paths to advisors.
    The matcher's caller (ranker) computes the count.
    """
    if unverified_count <= 0: return 0.2
    if unverified_count <= 2: return 0.4
    if unverified_count <= 4: return 0.6
    return 0.8


def application_strength(
    match: float,
    school_tier: str,
    pi_signal: str = "missing",
    unverified_count: int = 0,
) -> tuple[float, float]:
    """Returns (application_strength on 4.0, confidence_band on 4.0).

    Post-roadmap-#5: school_tier no longer modifies the strength here —
    its admit-rate role moved into `program_difficulty_penalty`. The
    parameter is kept on the signature for back-compat (callers may
    still pass it; it's unused) and for the `not_recruiting` fast-path.

    pi_signal == 'not_recruiting' → strength is forced to 0.
    """
    band = confidence_band_from_unverified(unverified_count)

    if pi_signal == NOT_RECRUITING_SIGNAL:
        return (0.0, band)

    pi = PI_ADJ.get(pi_signal, PI_ADJ["missing"])
    raw = match + pi
    strength = max(0.0, min(4.0, raw))
    return (strength, band)


# ---- Strength label (§7.3) -----------------------------------------------

def strength_label(strength: float) -> StrengthLabel:
    """Bucket the 4.0-scale application_strength into a 5-tier label.
    Return type is the same Literal alias as MatchResult.strength_label,
    so mypy is happy."""
    if strength >= 3.5: return "Safe"
    if strength >= 3.0: return "Match"
    if strength >= 2.5: return "Target"
    if strength >= 2.0: return "Reach"
    return "Far Reach"
