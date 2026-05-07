"""Program difficulty scoring (roadmap #5).

Replaces the old `tier_adj` term in `application_strength` with a richer,
multi-component `program_difficulty_penalty` on the 0–0.8 range. The
penalty combines:

  1. school_tier_admit_rate_factor — absorbs what `tier_adj` used to do.
     Magnitudes calibrated so that a perfect 4.0 candidate at top_10 with
     normal recruiting still lands at "Match" (≈3.2–3.5 on the 4.0 scale)
     instead of "Safe", consistent with v1 behaviour.
  2. cohort_size_estimate — small cohort ≈ harder admit.
  3. admission_model — direct-PI-admit pressure vs rotation.
  4. funding_structure — guaranteed support vs PI-grant-dependent.
  5. faculty_count_in_area — subfield bottleneck.
  6. international_friendliness — visible track record of int'l admits.

The signed contributions sum and clip to [0.0, 0.8]. Components below
sum to a maximum of ~0.95 (clipped to 0.8) and a minimum of ~−0.20
(clipped to 0.0), so a top_60+ rotation program with guaranteed funding
and 5+ matching faculty lands at penalty=0.0 (no extra burden), while a
top_10 small-cohort direct-admit PI-grant single-faculty-in-subfield
program lands at penalty=0.80.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.** The component weights below are educated guesses and
> should be re-fit once a real portfolio of admit/reject outcomes
> exists. Do not treat the magnitudes as load-bearing.

The `pi_signal` is intentionally NOT folded into this penalty — it
already enters `application_strength` via `pi_adj` (commit 1 of v2).
Commit 2 of v2 (Opportunity / A refactor) will rework that boundary.
"""

from __future__ import annotations

from phd_matcher.models import (
    EvidenceEntry,
    ProgramProfile,
    SchoolTier,
)

# ---- Component constants -------------------------------------------------

# School-tier admit-rate factor. Replaces the old `tier_adj` table
# (-1.0/-0.5/0/+0.4 on the 4.0 scale). Top_60+ no longer gets a positive
# boost; the v1 +0.4 boost is dropped intentionally — the user can
# recalibrate after running real low-tier portfolios.
SCHOOL_TIER_FACTOR: dict[str, float] = {
    "top_10":      0.70,
    "top_11_30":   0.50,
    "top_31_60":   0.30,
    "top_60_plus": 0.00,
}

COHORT_SMALL_THRESHOLD = 8        # < this → +0.10
COHORT_LARGE_THRESHOLD = 30       # ≥ this → −0.05
COHORT_SMALL_PENALTY = 0.10
COHORT_LARGE_RELIEF = -0.05

ADMISSION_DIRECT_PENALTY = 0.10   # direct_admit OR direct_admit_required
ADMISSION_ROTATION_RELIEF = -0.05 # rotation OR centralized

FUNDING_PI_GRANT_PENALTY = 0.10
FUNDING_GUARANTEED_RELIEF = -0.05

AREA_SOLO_THRESHOLD = 1           # ≤ this → +0.10
AREA_BROAD_THRESHOLD = 5          # ≥ this → −0.05
AREA_SOLO_PENALTY = 0.10
AREA_BROAD_RELIEF = -0.05

INTL_LOW_THRESHOLD = 0.30         # < this → +0.05
INTL_LOW_PENALTY = 0.05

PENALTY_MIN = 0.0
PENALTY_MAX = 0.8


# ---- Public scoring function --------------------------------------------

def program_difficulty_penalty(
    school_tier: SchoolTier,
    program_profile: ProgramProfile | None,
) -> tuple[float, list[str]]:
    """Return ``(penalty, reasons)`` where penalty is in ``[0.0, 0.8]``.

    The penalty is subtracted from ``risk_adjusted_strength`` to produce
    ``difficulty_adjusted_strength`` (the primary sort key post-roadmap-#5).
    Each contributing component appends a human-readable string to
    ``reasons`` so the explanation can surface why a program ranks where
    it does.

    Computation is purely additive over component contributions, then
    clipped — no field-aware overrides for this v1.
    """
    reasons: list[str] = []

    # 1. School-tier admit-rate factor (replaces tier_adj)
    factor = SCHOOL_TIER_FACTOR[school_tier]
    if factor > 0:
        reasons.append(
            f"school_tier={school_tier} admit-rate factor +{factor:.2f}"
        )

    if program_profile is None:
        # No program-level data → only school_tier contributes.
        return _clip_penalty(factor), reasons

    p = program_profile

    # 2. Cohort size
    if p.cohort_size_estimate is not None:
        if p.cohort_size_estimate < COHORT_SMALL_THRESHOLD:
            factor += COHORT_SMALL_PENALTY
            reasons.append(
                f"small cohort ({p.cohort_size_estimate}/yr) +{COHORT_SMALL_PENALTY:.2f}"
            )
        elif p.cohort_size_estimate >= COHORT_LARGE_THRESHOLD:
            factor += COHORT_LARGE_RELIEF
            reasons.append(
                f"large cohort ({p.cohort_size_estimate}/yr) {COHORT_LARGE_RELIEF:+.2f}"
            )

    # 3. Admission model (direct admit pressure vs rotation/centralized)
    is_direct = (
        p.admission_model == "direct_admit"
        or p.direct_admit_required is True
    )
    if is_direct:
        factor += ADMISSION_DIRECT_PENALTY
        reasons.append(
            f"direct-admit pressure +{ADMISSION_DIRECT_PENALTY:.2f}"
        )
    elif p.admission_model in ("rotation", "centralized"):
        factor += ADMISSION_ROTATION_RELIEF
        reasons.append(
            f"{p.admission_model} program {ADMISSION_ROTATION_RELIEF:+.2f}"
        )

    # 4. Funding structure
    if p.funding_structure == "pi_grant":
        factor += FUNDING_PI_GRANT_PENALTY
        reasons.append(
            f"funding=pi_grant +{FUNDING_PI_GRANT_PENALTY:.2f}"
        )
    elif p.funding_structure == "guaranteed":
        factor += FUNDING_GUARANTEED_RELIEF
        reasons.append(
            f"guaranteed funding {FUNDING_GUARANTEED_RELIEF:+.2f}"
        )

    # 5. Faculty in area (subfield bottleneck)
    if p.faculty_count_in_area is not None:
        if p.faculty_count_in_area <= AREA_SOLO_THRESHOLD:
            factor += AREA_SOLO_PENALTY
            reasons.append(
                f"only {p.faculty_count_in_area} matching faculty +{AREA_SOLO_PENALTY:.2f}"
            )
        elif p.faculty_count_in_area >= AREA_BROAD_THRESHOLD:
            factor += AREA_BROAD_RELIEF
            reasons.append(
                f"{p.faculty_count_in_area}+ faculty in area {AREA_BROAD_RELIEF:+.2f}"
            )

    # 6. International friendliness
    if (
        p.international_friendliness is not None
        and p.international_friendliness < INTL_LOW_THRESHOLD
    ):
        factor += INTL_LOW_PENALTY
        reasons.append(
            f"low international friendliness ({p.international_friendliness:.2f}) "
            f"+{INTL_LOW_PENALTY:.2f}"
        )

    return _clip_penalty(factor), reasons


def _clip_penalty(value: float) -> float:
    return max(PENALTY_MIN, min(PENALTY_MAX, value))


# ---- Evidence-coverage helper -------------------------------------------

# Fields whose set value contributes to the penalty. evidence_coverage
# tracks these as "program:<field>" signals, only when the value is set
# (analogous to how research_fit is only counted when score is non-null).
SCORING_RELEVANT_FIELDS: tuple[str, ...] = (
    "cohort_size_estimate",
    "admission_model",
    "funding_structure",
    "faculty_count_in_area",
    "international_friendliness",
)


def program_signal_is_set(program: ProgramProfile, field_name: str) -> bool:
    """Whether a ProgramProfile field counts as 'agent making a claim'.

    `unknown` (for the two literal fields) and `None` (for the optional
    numeric / bool fields) both mean 'didn't check' — those don't enter
    coverage. Otherwise the signal is set and needs evidence.
    """
    val = getattr(program, field_name)
    if val is None:
        return False
    if field_name in ("admission_model", "funding_structure") and val == "unknown":
        return False
    return True


def program_evidence_for(
    program: ProgramProfile, field_name: str
) -> EvidenceEntry | None:
    """Look up the evidence entry for a program field. The evidence dict
    on `ProgramProfile` is indexed by the bare field name (e.g.,
    ``"cohort_size_estimate"``); the namespaced form (``"program:..."``)
    appears only in `supports_fields`."""
    return program.evidence.get(field_name)
