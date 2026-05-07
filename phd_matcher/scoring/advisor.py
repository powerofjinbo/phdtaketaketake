"""Advisor Influence (A) — DESIGN.md §7.

The A dimension answers "is this PI strong, active, and a good place to
invest 5–6 years?" — separate from C, which answers "do I have a real
connection to them?". Splitting these two avoids the previous bug where
PI prestige inflated Connection score even when the path was weak.

Components (sum to 1.0):
  0.30 · influence_percentile  (h-index proxy)
  0.20 · elite_status          (NAS / HHMI / NAE / field-specific fellow)
  0.20 · active_funding_quality
  0.20 · grad_placement_quality
  0.10 · recruiting_health     (derived from pi_signal)

Each component is 0–1; the composite is 0–1 then mapped to the 4.0 scale
via the existing `raw_to_4_0` bucket function.
"""

from __future__ import annotations

W_INFLUENCE = 0.30
W_ELITE = 0.20
W_FUNDING = 0.20
W_PLACEMENT = 0.20
W_RECRUITING = 0.10

# Map pi_signal → recruiting_health on 0–1.
# Distinct from admit.PI_ADJ which is a separate ±0.x adjustment to
# application_strength. Same input, different question:
#   - PI_ADJ: "is this PI taking students THIS cycle?" → admit timing
#   - recruiting_health: "is this lab healthy / growing / shrinking?"
#     → advisor quality signal that contributes to A
_PI_SIGNAL_TO_RECRUITING_HEALTH: dict[str, float] = {
    "strong":         1.0,
    "normal":         0.7,
    "shrinking":      0.3,
    "missing":        0.5,
    "not_recruiting": 0.0,
}


def _safe_float(x: float | None) -> float:
    return 0.0 if x is None else float(x)


def advisor_strength_raw(candidate: dict) -> float:
    """Compute raw 0–1 advisor strength composite.

    `None` field-strength values contribute 0 (conservative — incentivizes
    the agent to actually verify).
    """
    influence = _safe_float(candidate.get("normalized_collab_top20pct"))

    nas = candidate.get("collab_with_nas")
    elite = 1.0 if nas is True else 0.0

    funding = _safe_float(candidate.get("active_funding_quality"))
    placement = _safe_float(candidate.get("grad_placement_quality"))

    pi_signal = candidate.get("pi_signal", "missing")
    recruiting = _PI_SIGNAL_TO_RECRUITING_HEALTH.get(pi_signal, 0.5)

    return (
        W_INFLUENCE * influence
        + W_ELITE * elite
        + W_FUNDING * funding
        + W_PLACEMENT * placement
        + W_RECRUITING * recruiting
    )


def advisor_strength(candidate: dict) -> float:
    """Compute A score on the 4.0 scale.

    Internally: raw composite (0–1) → bucketed via `raw_to_4_0`.
    """
    from phd_matcher.scoring.connection import raw_to_4_0

    return raw_to_4_0(advisor_strength_raw(candidate))
