"""Match score and admission likelihood — per Scoring Design v0.3 §6, §7."""

# ---- Tier-adaptive weights (§6) ------------------------------------------

TIER_WEIGHTS: dict[str, dict[str, float]] = {
    "top_10":      {"C": 0.45, "P": 0.30, "E": 0.15, "G": 0.10},
    "top_11_30":   {"C": 0.40, "P": 0.30, "E": 0.15, "G": 0.15},
    "top_31_60":   {"C": 0.35, "P": 0.25, "E": 0.20, "G": 0.20},
    "top_60_plus": {"C": 0.30, "P": 0.20, "E": 0.20, "G": 0.30},
}


def match_score(c: float, p: float, e: float, g: float, school_tier: str) -> float:
    """Weighted combination → 4.0."""
    if school_tier not in TIER_WEIGHTS:
        raise ValueError(f"Unknown school tier: {school_tier!r}. Valid: {list(TIER_WEIGHTS)}")
    w = TIER_WEIGHTS[school_tier]
    return w["C"] * c + w["P"] * p + w["E"] * e + w["G"] * g


# ---- Admission likelihood (§7) -------------------------------------------

# School competitiveness adjustment (lower tier = easier admit at same match).
# Calibrated to reflect realistic admission rate ratios (top 10 PhD programs
# admit ~5–10% of applicants; top 60+ admit ~25–35% — a 4–8x gap).
TIER_ADMIT_ADJ: dict[str, float] = {
    "top_10":      -1.0,    # MIT / Stanford / Princeton / Berkeley etc — brutal
    "top_11_30":   -0.5,
    "top_31_60":    0.0,
    "top_60_plus": +0.4,
}

# PI recruiting signal adjustment
PI_ADJ: dict[str, float] = {
    "strong":     +0.2,    # >=2 new PhDs/year, last 3 years
    "normal":      0.0,    # 1–2/year
    "shrinking":  -0.4,    # <1/year
    "missing":    -0.1,    # data unavailable (slight conservative)
}

NOT_RECRUITING_SIGNAL = "not_recruiting"


def confidence_band(missing_signals: int) -> float:
    """Confidence width on 4.0 scale based on data completeness."""
    if missing_signals <= 0: return 0.3
    if missing_signals == 1: return 0.5
    return 0.7


def admit_likelihood(
    match: float,
    school_tier: str,
    pi_signal: str = "missing",
    missing_signals: int = 0,
) -> tuple[float, float]:
    """Returns (admit_likelihood on 4.0, confidence_band on 4.0).

    pi_signal == 'not_recruiting' → admit_likelihood is forced to 0.
    """
    band = confidence_band(missing_signals)

    if pi_signal == NOT_RECRUITING_SIGNAL:
        return (0.0, band)

    if school_tier not in TIER_ADMIT_ADJ:
        raise ValueError(f"Unknown school tier: {school_tier!r}")

    pi_a = PI_ADJ.get(pi_signal, PI_ADJ["missing"])
    raw = match + TIER_ADMIT_ADJ[school_tier] + pi_a
    likelihood = max(0.0, min(4.0, raw))
    return (likelihood, band)


# ---- 5-tier label (§7.3) -------------------------------------------------

def likelihood_label(likelihood: float) -> str:
    if likelihood >= 3.5: return "Safe"
    if likelihood >= 3.0: return "Match"
    if likelihood >= 2.5: return "Target"
    if likelihood >= 2.0: return "Reach"
    return "Far Reach"
