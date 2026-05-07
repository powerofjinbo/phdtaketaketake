"""Opportunity (O) — admit-cycle availability (roadmap #6a).

Splits the time-sensitive "is this PI taking students this cycle, with
active funding, with reasonable lab capacity, and is the application
path open?" question off from the A pillar (which post-#6a is reputation-
only). The matcher uses O to derive `opportunity_adj`, which **replaces
the v1 `pi_adj` term** inside `application_strength`.

Formula:

    O_raw = clip(
        0.30 · recruiting_health(pi_signal)
      + 0.30 · active_funding_quality
      + 0.20 · lab_capacity(open, current, recent_grads)
      + 0.10 · funding_timing(grant_end_years)
      + 0.10 · availability(sabbatical_or_admin_load)
    , 0, 1)

`opportunity_adj` ladder (replaces `pi_adj`):

    not_recruiting → force application_strength = 0
    O ≥ 0.70  → +0.2
    O ≥ 0.50  →  0.0
    O ≥ 0.30  → −0.2
    O <  0.30 → −0.4

For pure legacy candidates with no `opportunity_signal`, the matcher
falls back to the v1 PI_ADJ table directly (no O computation), so old
JSON and old tests retain exact behavior.

When `opportunity_signal` IS present, the matcher applies a **field-by-
field merge** with the legacy top-level fields: `opportunity_signal.X`
wins iff explicitly set, otherwise falls back to `candidate.X`. This
prevents losing legacy data when the agent migrates only some fields.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.** The component weights and ladder cutoffs are educated
> guesses, not load-bearing magnitudes.
"""

from __future__ import annotations

from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    OpportunitySignal,
    PISignal,
)

# ---- Component weights ---------------------------------------------------

W_RECRUITING = 0.30
W_FUNDING = 0.30
W_CAPACITY = 0.20
W_TIMING = 0.10
W_AVAILABILITY = 0.10

# ---- pi_signal → recruiting_health (0-1) ---------------------------------

_PI_SIGNAL_TO_RECRUITING_HEALTH: dict[str, float] = {
    "strong":         1.0,
    "normal":         0.7,
    "missing":        0.5,
    "shrinking":      0.3,
    "not_recruiting": 0.0,
}

NOT_RECRUITING_SIGNAL = "not_recruiting"

# ---- Default neutrals ----------------------------------------------------
#
# Missing data is mostly "didn't check" rather than "verified zero", so
# components default to 0.5 when None. Active funding is special: legacy
# semantic was "0 = verified-empty" so we keep its missing → 0.5 too,
# letting the band carry the uncertainty.

NEUTRAL = 0.5


# ---- Legacy PI_ADJ table (pure-legacy fallback) --------------------------
#
# Pre-#6a `pi_adj` table. Used only when `opportunity_signal is None` —
# the agent didn't opt into the richer model so we preserve old behavior
# exactly.

LEGACY_PI_ADJ: dict[str, float] = {
    "strong":     +0.2,
    "normal":      0.0,
    "shrinking":  -0.4,
    "missing":    -0.1,
}


# ---- New opportunity_adj ladder ------------------------------------------

OPPORTUNITY_ADJ_THRESHOLDS: tuple[tuple[float, float], ...] = (
    (0.70, +0.2),
    (0.50,  0.0),
    (0.30, -0.2),
    (0.00, -0.4),
)


# ---- Sub-component helpers -----------------------------------------------

def recruiting_health(pi_signal: str | PISignal) -> float:
    return _PI_SIGNAL_TO_RECRUITING_HEALTH.get(pi_signal, NEUTRAL)


def lab_capacity(
    open_positions: int | None,
    current_student_count: int | None,
    recent_phd_graduations: int | None,
) -> float:
    """Three-input average. Each sub-signal: None → neutral 0.5."""
    pos_score: float = NEUTRAL
    if open_positions is not None:
        pos_score = 1.0 if open_positions >= 1 else 0.3

    count_score: float = NEUTRAL
    if current_student_count is not None:
        if current_student_count == 0:
            count_score = 0.3       # ambiguous: new lab or inactive
        elif current_student_count <= 2:
            count_score = 0.6       # modest
        elif current_student_count <= 10:
            count_score = 1.0       # healthy
        elif current_student_count <= 20:
            count_score = 0.85      # large but okay
        else:
            count_score = 0.6       # mentorship-risk discount

    grad_score: float = NEUTRAL
    if recent_phd_graduations is not None:
        if recent_phd_graduations >= 2:
            grad_score = 1.0
        elif recent_phd_graduations == 1:
            grad_score = 0.7
        else:
            grad_score = 0.4        # 0 graduations is mildly negative

    return (pos_score + count_score + grad_score) / 3.0


def funding_timing(grant_end_years: int | None) -> float:
    if grant_end_years is None:
        return NEUTRAL
    if grant_end_years >= 4:
        return 1.0
    if grant_end_years >= 2:
        return 0.8
    if grant_end_years == 1:
        return 0.4
    return 0.2  # 0 — funding ends this cycle


def availability(sabbatical_or_admin_load: bool | None) -> float:
    if sabbatical_or_admin_load is None:
        return NEUTRAL
    return 0.2 if sabbatical_or_admin_load else 1.0


# ---- Effective-field accessors (field-by-field merge) -------------------

def effective_pi_signal(candidate: CandidateAdvisor) -> PISignal:
    """`opportunity_signal.pi_signal` wins iff != "missing"; otherwise
    falls back to `candidate.pi_signal`."""
    if candidate.opportunity_signal is None:
        return candidate.pi_signal
    if candidate.opportunity_signal.pi_signal != "missing":
        return candidate.opportunity_signal.pi_signal
    return candidate.pi_signal


def effective_active_funding_quality(candidate: CandidateAdvisor) -> float | None:
    """`opportunity_signal.active_funding_quality` wins iff explicitly
    set (not None); otherwise falls back to
    `candidate.active_funding_quality`."""
    o = candidate.opportunity_signal
    if o is None:
        return candidate.active_funding_quality
    if o.active_funding_quality is not None:
        return o.active_funding_quality
    return candidate.active_funding_quality


# ---- Public scoring entry points ----------------------------------------

def opportunity_score(candidate: CandidateAdvisor) -> float | None:
    """Compute O score (0-1) for the candidate.

    Returns `None` when `opportunity_signal` is absent (pure legacy path
    — the caller should derive `opportunity_adj` via `legacy_pi_adj`
    instead). Otherwise returns the clipped 0-1 composite.
    """
    if candidate.opportunity_signal is None:
        return None

    o = candidate.opportunity_signal
    eff_pi = effective_pi_signal(candidate)
    eff_funding = effective_active_funding_quality(candidate)

    funding = eff_funding if eff_funding is not None else NEUTRAL

    raw = (
        W_RECRUITING   * recruiting_health(eff_pi)
        + W_FUNDING    * funding
        + W_CAPACITY   * lab_capacity(
            o.lab_open_positions,
            o.current_student_count,
            o.recent_phd_graduations,
        )
        + W_TIMING       * funding_timing(o.grant_end_years)
        + W_AVAILABILITY * availability(o.sabbatical_or_admin_load)
    )
    return max(0.0, min(1.0, raw))


def opportunity_adj_from_score(o_score: float) -> float:
    """Map O (0-1) to ±adj. Caller must check `not_recruiting` separately
    via `is_not_recruiting()` since that forces `application_strength=0`."""
    for threshold, adj in OPPORTUNITY_ADJ_THRESHOLDS:
        if o_score >= threshold:
            return adj
    return -0.4


def legacy_pi_adj(pi_signal: str | PISignal) -> float:
    """Pure-legacy fallback (no opportunity_signal). Uses the v1 PI_ADJ
    table verbatim. `not_recruiting` is handled by the caller."""
    return LEGACY_PI_ADJ.get(pi_signal, LEGACY_PI_ADJ["missing"])


def is_not_recruiting(candidate: CandidateAdvisor) -> bool:
    """Effective pi_signal == 'not_recruiting' (uses the field-by-field
    merge so the new opportunity_signal can declare not_recruiting too).
    Triggers the application_strength=0 fast-path."""
    return effective_pi_signal(candidate) == NOT_RECRUITING_SIGNAL


def compute_opportunity_state(
    candidate: CandidateAdvisor,
) -> tuple[float | None, float, bool]:
    """One-shot: returns ``(o_score_or_None, opportunity_adj, force_zero)``.

    - `o_score is None` → pure-legacy path; `opportunity_adj` came from
      `legacy_pi_adj`.
    - `o_score` set → new path; `opportunity_adj` came from
      `opportunity_adj_from_score`.
    - `force_zero=True` → `not_recruiting` was detected (effective
      pi_signal); the caller should force `application_strength=0`.
    """
    force_zero = is_not_recruiting(candidate)

    o = opportunity_score(candidate)
    if o is None:
        # Pure legacy
        return (None, legacy_pi_adj(candidate.pi_signal), force_zero)

    return (o, opportunity_adj_from_score(o), force_zero)


# ---- Evidence-coverage helpers ------------------------------------------

# Fields tracked in evidence_coverage. The first two are "legacy
# required" — they should be evidenced even in pure-legacy mode and
# their coverage names match the v1 names (`pi_signal`,
# `active_funding_quality`) so existing tests / older JSON keep
# working. The rest are opt-in: only counted when the agent set the
# corresponding `opportunity_signal.<field>`.
LEGACY_REQUIRED_OPPORTUNITY_FIELDS: tuple[str, ...] = (
    "pi_signal",
    "active_funding_quality",
)

OPT_IN_OPPORTUNITY_FIELDS: tuple[str, ...] = (
    "lab_open_positions",
    "current_student_count",
    "recent_phd_graduations",
    "grant_end_years",
    "sabbatical_or_admin_load",
    "application_contact_policy",
)


def opt_in_signal_is_set(opportunity: OpportunitySignal, field_name: str) -> bool:
    """Whether an OpportunitySignal opt-in field counts as 'agent making
    a claim'. None / "unknown" mean 'didn't check' and don't enter
    coverage; everything else does."""
    val = getattr(opportunity, field_name)
    if val is None:
        return False
    if field_name == "application_contact_policy" and val == "unknown":
        return False
    return True


def opportunity_evidence_for(
    candidate: CandidateAdvisor, field_name: str
) -> tuple[EvidenceEntry | None, EvidenceEntry | None]:
    """Look up evidence entries for an opportunity field in BOTH locations:
    the new `opportunity_signal.evidence[<field>]` (preferred) and the
    legacy `candidate.evidence[<field>]` (back-compat). Returns
    ``(new_entry, legacy_entry)``; either may be None."""
    new_entry: EvidenceEntry | None = None
    if candidate.opportunity_signal is not None:
        new_entry = candidate.opportunity_signal.evidence.get(field_name)

    legacy_entry: EvidenceEntry | None = candidate.evidence.get(field_name)
    return (new_entry, legacy_entry)
