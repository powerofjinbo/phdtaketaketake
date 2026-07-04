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
    """Wider band when more signals lack source citations (ABSOLUTE count).

    "Unverified" includes: missing PI signal, advisor-influence signals at
    default values without sources, empty / unsourced paths to advisors.

    Legacy/simple form kept for direct callers and the v1
    `application_strength` path. The ranker now prefers
    :func:`confidence_band_from_coverage`, which uses the coverage *fraction*
    so partial sourcing is rewarded even for candidates with many signals.
    """
    if unverified_count <= 0: return 0.2
    if unverified_count <= 2: return 0.4
    if unverified_count <= 4: return 0.6
    return 0.8


# Band endpoints on the 4.0 scale. Fully-sourced → NARROW; fully-unsourced →
# WIDE. The coverage-fraction band interpolates linearly between them so that
# *every* additional sourced signal narrows the band — unlike the absolute
# bucket form, which saturates at ≥5 unverified and gives a candidate who
# sourced 3 of 8 signals the same band as one who sourced 0 of 8.
BAND_NARROW = 0.2
BAND_WIDE = 0.8


def confidence_band_from_coverage(unverified: int, total: int) -> float:
    """Band as a linear function of the *unverified fraction* of signals.

    band = BAND_NARROW + (BAND_WIDE − BAND_NARROW) · (unverified / total)

    - fully sourced (unverified=0)        → 0.2
    - fully unsourced (unverified=total)  → 0.8
    - partial coverage interpolates, so sourcing one more signal always
      narrows the band (monotone in coverage). This restores an
      evidence-first gradient across the realistic 5–15-signal operating
      range, where the absolute-count band was a flat 0.8.

    `total <= 0` (no signals to verify) falls back to the narrow endpoint —
    there is nothing outstanding to widen the band. `unverified` is clamped
    into `[0, total]` defensively.
    """
    if total <= 0:
        return BAND_NARROW
    frac = min(max(unverified, 0), total) / total
    return round(BAND_NARROW + (BAND_WIDE - BAND_NARROW) * frac, 2)


def application_strength(
    match: float,
    school_tier: str,
    pi_signal: str = "missing",
    unverified_count: int = 0,
) -> tuple[float, float]:
    """Legacy signature — derives `pi_adj` from `pi_signal` via `PI_ADJ`.

    Post-roadmap-#6a, the matcher pipeline calls
    :func:`application_strength_from_adj` instead, which takes
    `opportunity_adj` directly (computed by
    `phd_matcher.scoring.opportunity.compute_opportunity_state`). This
    function is kept so direct callers and `tests/test_admit.py` retain
    the v1 PI_ADJ behavior exactly.

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


def application_strength_from_adj(
    match: float,
    opportunity_adj: float,
    *,
    force_zero: bool,
    unverified_count: int = 0,
    total_count: int | None = None,
) -> tuple[float, float]:
    """Returns (application_strength on 4.0, confidence_band on 4.0).

    Post-roadmap-#6a entry point. Takes `opportunity_adj` directly
    (computed upstream by
    `phd_matcher.scoring.opportunity.compute_opportunity_state`).
    `force_zero=True` means the effective `pi_signal == "not_recruiting"`
    and the strength must be clipped to 0.

    When `total_count` is provided, the band uses the coverage *fraction*
    (:func:`confidence_band_from_coverage`) so partial sourcing is rewarded.
    When it is omitted (None), the legacy absolute-count band is used — this
    preserves exact behavior for any direct caller that doesn't pass a total.
    """
    if total_count is None:
        band = confidence_band_from_unverified(unverified_count)
    else:
        band = confidence_band_from_coverage(unverified_count, total_count)

    if force_zero:
        return (0.0, band)

    raw = match + opportunity_adj
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
