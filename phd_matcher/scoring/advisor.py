"""Advisor Influence (A) — DESIGN.md §7, post-roadmap-#6a refactor.

The A pillar is now reputation / field standing / placement record only.
Funding and recruiting moved to OpportunitySignal (post-#6a) — see
`phd_matcher.scoring.opportunity`. Splitting these avoids the previous
bug where time-sensitive recruiting health bled into intrinsic PI
strength and confused both signals.

The A definition is intentionally narrow:

  A = reputation / field standing / placement record
  NOT funding
  NOT currently recruiting
  NOT application accessibility

A new PI without placement track-record will score lower on A. That's
acceptable — a new PI's strengths (active grants, growing lab,
recruiting openings) belong in O, not A.

Components (sum to 1.0):
  0.40 · influence_percentile  (h-index proxy)
  0.30 · elite_status          (NAS / HHMI / NAE / field-specific fellow)
  0.30 · grad_placement_quality

Each component is 0–1; the composite is 0–1 then mapped to the 4.0 scale
via the existing `raw_to_4_0` bucket function.
"""

from __future__ import annotations

W_INFLUENCE = 0.40
W_ELITE = 0.30
W_PLACEMENT = 0.30


def _safe_float(x: float | None) -> float:
    return 0.0 if x is None else float(x)


def advisor_strength_raw(candidate: dict) -> float:
    """Compute raw 0–1 advisor strength composite.

    `None` field values contribute 0 (conservative — incentivizes the
    agent to actually verify). active_funding_quality and pi_signal are
    intentionally NOT read here post-#6a; they live in O.
    """
    influence = _safe_float(candidate.get("normalized_collab_top20pct"))

    nas = candidate.get("collab_with_nas")
    elite = 1.0 if nas is True else 0.0

    placement = _safe_float(candidate.get("grad_placement_quality"))

    return (
        W_INFLUENCE * influence
        + W_ELITE * elite
        + W_PLACEMENT * placement
    )


def advisor_strength(candidate: dict) -> float:
    """Compute A score on the 4.0 scale.

    Internally: raw composite (0–1) → bucketed via `raw_to_4_0`.
    """
    from phd_matcher.scoring.connection import raw_to_4_0

    return raw_to_4_0(advisor_strength_raw(candidate))
