"""Research fit (Sprint-2-c3 structured v2).

Deterministic 6-axis weighted score derived from `ResearchFit`. When a
`CandidateAdvisor` has `research_fit` set, the matcher uses this score
in place of the legacy `research_fit_score` field (which remains for
back-compat).

  research_fit_score = 0.30 · topic_fit
                     + 0.20 · method_fit
                     + 0.15 · system_or_dataset_fit
                     + 0.15 · temporal_fit
                     + 0.10 · grant_fit
                     + 0.10 · student_background_fit

`theory_experiment_fit` is stored on `ResearchFit` for transparency
(especially in physics) but does NOT enter the v1 formula — keeps the
score additive over a meaningful 6-axis basis. Future calibration may
include it as a ±0.05 modifier.

Sort-key role unchanged from roadmap #4: research_fit_score is a pure
tie-breaker (rank 3 in the post-#5 ladder), never overrides
risk_adjusted_strength or difficulty_adjusted_strength.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.**
"""

from __future__ import annotations

from phd_matcher.models import CandidateAdvisor, ResearchFit

# ---- Component weights ---------------------------------------------------

W_TOPIC = 0.30
W_METHOD = 0.20
W_SYSTEM = 0.15
W_TEMPORAL = 0.15
W_GRANT = 0.10
W_BACKGROUND = 0.10


def research_fit_v2_score(rf: ResearchFit) -> float:
    """Deterministic weighted score from a ResearchFit submodel."""
    return (
        W_TOPIC      * rf.topic_fit
        + W_METHOD     * rf.method_fit
        + W_SYSTEM     * rf.system_or_dataset_fit
        + W_TEMPORAL   * rf.temporal_fit
        + W_GRANT      * rf.grant_fit
        + W_BACKGROUND * rf.student_background_fit
    )


def effective_research_fit_score(candidate: CandidateAdvisor) -> float | None:
    """Resolve the effective `research_fit_score` for a candidate.

    Priority (post-Sprint-2-c3):
      1. If `candidate.research_fit` is set → derive from the v2 formula.
      2. Else if legacy `candidate.research_fit_score` is set → use it.
      3. Else → None ("not computed"; not counted in evidence coverage).
    """
    if candidate.research_fit is not None:
        return research_fit_v2_score(candidate.research_fit)
    return candidate.research_fit_score
