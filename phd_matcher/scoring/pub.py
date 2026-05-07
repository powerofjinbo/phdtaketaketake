"""Publication score (P) — Sprint-2-c2 Publication v2 expansion.

Layered additions on top of the v1 (tier × position decrement) scheme:
  - recency_weight: scales by year (≤2y → 1.0, 3–5y → 0.95, >5y → 0.85)
  - contribution_bonus: with verified `contribution_role`, adds +0.05 to
    +0.15 to the score
  - big-collab guardrail: when `total_authors > field threshold` AND no
    verified contribution_role, caps the paper at `BIG_COLLAB_GUARDED_FLOOR`
  - consortium guardrail: `author_role="consortium"` without verified
    contribution_role caps at `0.45 × baseline` (heavily discounted)

The position-decrement scheme is unchanged — v2 layers add on top without
disrupting existing values for papers that don't opt in.

> **Thresholds are v2 defaults; recalibrate after running real
> portfolios.**
"""

from __future__ import annotations

import datetime

from phd_matcher.models import FieldProfile

# Journal tier baseline scores (4.0 scale)
TIER_BASELINE: dict[int | str, float] = {
    "S": 4.0,
    1: 4.0,
    2: 3.7,
    3: 3.3,
    4: 2.8,
    5: 2.3,
    0: 0.0,
}

POSITION_DECREMENT: dict[int, float] = {
    1: 0.0,
    2: 0.10,
    3: 0.25,
    4: 0.45,
}

BIG_COLLAB_FLOOR = 3.5
NO_PAPER_FLOOR = 3.0

# v2: Big-collab guardrail (Sprint-2-c2). When total_authors exceeds the
# field's big_collab_threshold AND no verified contribution_role exists,
# the paper's score is capped at this value — preventing "I'm one of 300
# alphabetical authors of a tier-1 ATLAS paper" from being scored as
# 1st-author equivalent.
BIG_COLLAB_GUARDED_FLOOR = 3.5

# v2: Consortium-without-evidence multiplier. author_role="consortium"
# without a verified contribution_role caps at 0.45 × baseline.
CONSORTIUM_NO_EVIDENCE_FACTOR = 0.45

# v2: Contribution bonus per verified role. Additive on top of base score.
CONTRIBUTION_BONUS: dict[str, float] = {
    "lead_analysis":    0.15,
    "method_developer": 0.10,
    "data_collection":  0.05,
    "writing":          0.05,
    "unclear":          0.0,
}

# v2: Recency multiplier from publication year.
RECENCY_RECENT_GAP = 2     # ≤ this → 1.00
RECENCY_MID_GAP = 5        # ≤ this → 0.95
RECENCY_RECENT_FACTOR = 1.00
RECENCY_MID_FACTOR = 0.95
RECENCY_OLD_FACTOR = 0.85

# Paper-status weights. Applied multiplicatively to the tier × position score.
# Default 'published' = 1.0 preserves the "all CV papers count fully" rule
# for the typical case; submitted / preprint / in-prep get partial credit so
# the agent can be honest about pipeline maturity without inflating scores.
STATUS_WEIGHT: dict[str, float] = {
    "published":  1.0,
    "accepted":   1.0,
    "in_press":   1.0,
    "submitted":  0.7,
    "preprint":   0.7,
    "in_prep":    0.3,
}

# AuthorRole → effective position used for tier × decrement scoring (P1).
_ROLE_TO_EFFECTIVE_POSITION: dict[str, int] = {
    "first": 1,
    "co_first": 1,        # shared first → 1st (per SKILL.md special positions)
    "corresponding": 1,   # corresponding ≈ 1st when not also senior
    "senior": 1,          # PhD applicants almost never hold this; treat
                          # as 1st-equivalent for the rare returning-applicant case
    # 'middle' and 'consortium' fall through to literal author_position.
}


def journal_baseline(tier: int | str) -> float:
    if tier not in TIER_BASELINE:
        raise ValueError(
            f"Unknown journal tier: {tier!r}. "
            f"Valid: {sorted(TIER_BASELINE.keys(), key=str)}"
        )
    return TIER_BASELINE[tier]


def status_weight(
    status: str, field_profile: FieldProfile | None = None
) -> float:
    """Multiplicative weight for a paper status. Raises on unknown status —
    unknown must NOT silently default to 1.0.

    Field profile (P1) may override per-field — e.g., `math.yaml` sets
    `paper_status_weight_overrides: {preprint: 0.9}` so arXiv preprints
    carry more weight than the cross-field default 0.7.
    """
    if status not in STATUS_WEIGHT:
        raise ValueError(
            f"Unknown paper status: {status!r}. "
            f"Valid: {sorted(STATUS_WEIGHT.keys())}"
        )
    if field_profile and status in field_profile.paper_status_weight_overrides:
        return field_profile.paper_status_weight_overrides[status]
    return STATUS_WEIGHT[status]


def effective_position(
    author_position: int,
    author_role: str | None = None,
    field_profile: FieldProfile | None = None,
) -> int:
    """Compute the position used for tier × decrement scoring.

    Without an `author_role`, returns `author_position` as-is. With a role,
    applies the role override (e.g., `co_first` → 1 regardless of byline).

    **P0 guardrail**: if `author_role='co_first'` but the field profile
    declares `co_first_supported=False` (e.g., physics, chemistry, math),
    the override is silently dropped (returns literal position). Use
    `validate_paper_roles()` to surface such cases as warnings/errors at
    the validation layer.
    """
    if author_role is None:
        return author_position
    if (
        author_role == "co_first"
        and field_profile is not None
        and not field_profile.co_first_supported
    ):
        return author_position
    return _ROLE_TO_EFFECTIVE_POSITION.get(author_role, author_position)


def validate_paper_roles(
    papers: list[dict], field_profile: FieldProfile | None = None
) -> list[str]:
    """Return human-readable warnings about author_role usage that
    conflicts with the active FieldProfile.

    Currently checks:
      - `author_role='co_first'` in a field whose `co_first_supported=False`
        (physics / chemistry / mse / math) — warn that this convention
        isn't recognized in this discipline.

    Returns an empty list if no profile or no conflicts.
    """
    if field_profile is None:
        return []
    warnings: list[str] = []
    for i, p in enumerate(papers):
        role = p.get("author_role")
        if role == "co_first" and not field_profile.co_first_supported:
            warnings.append(
                f"paper[{i}]: author_role='co_first' is not a recognized "
                f"convention in {field_profile.id} "
                f"(FieldProfile.co_first_supported=false). The role override "
                f"is dropped — the paper scores at literal author_position. "
                f"Confirm with the user whether the convention applies."
            )
    return warnings


def recency_weight(year: int | None, *, current_year: int | None = None) -> float:
    """v2: scale paper score by recency. None → 1.00 (no penalty for
    unspecified year). Future years (data error) clamp to 1.00."""
    if year is None:
        return RECENCY_RECENT_FACTOR
    if current_year is None:
        current_year = datetime.datetime.now().year
    gap = current_year - year
    if gap <= RECENCY_RECENT_GAP:
        return RECENCY_RECENT_FACTOR
    if gap <= RECENCY_MID_GAP:
        return RECENCY_MID_FACTOR
    return RECENCY_OLD_FACTOR


def contribution_bonus(
    contribution_role: str | None,
    *,
    has_evidence: bool,
) -> float:
    """v2: additive bonus for a verified contribution_role. None → 0.0.
    Roles without supporting evidence return 0.0 (the agent-stated role
    is informational only)."""
    if contribution_role is None or not has_evidence:
        return 0.0
    return CONTRIBUTION_BONUS.get(contribution_role, 0.0)


def paper_score(
    journal_tier: int | str,
    author_position: int,
    status: str = "published",
    *,
    author_role: str | None = None,
    field_profile: FieldProfile | None = None,
    year: int | None = None,
    total_authors: int | None = None,
    contribution_role: str | None = None,
    has_contribution_evidence: bool = False,
    current_year: int | None = None,
) -> float:
    """Score a single paper (v2 layered formula).

    v1 (unchanged): tier × position decrement, status_weight, with the
    5+ author rule capping at `BIG_COLLAB_FLOOR`.

    v2 layers:
      - `recency_weight(year)` multiplier (1.00 / 0.95 / 0.85)
      - big-collab guardrail: when `total_authors > field threshold` AND
        no verified `contribution_role`, cap at `BIG_COLLAB_GUARDED_FLOOR`
      - consortium guardrail: `author_role="consortium"` without verified
        `contribution_role` caps at `0.45 × baseline`
      - `contribution_bonus(role)` additive (+0.05 to +0.15) when role
        is set AND `has_contribution_evidence=True`
    """
    if author_position < 1:
        raise ValueError(f"author_position must be >= 1, got {author_position}")

    baseline = journal_baseline(journal_tier)
    if baseline == 0.0:
        return 0.0

    pos = effective_position(author_position, author_role, field_profile)
    if pos <= 4:
        base = baseline - POSITION_DECREMENT[pos]
    else:
        base = min(BIG_COLLAB_FLOOR, baseline - POSITION_DECREMENT[4])

    base *= status_weight(status, field_profile)
    base *= recency_weight(year, current_year=current_year)

    # v2 guardrails — applied after the v1 score, before the contribution
    # bonus. Both guardrails are bypassed by a verified contribution_role
    # (other than "unclear").
    has_verified_contrib = (
        has_contribution_evidence
        and contribution_role is not None
        and contribution_role != "unclear"
    )

    if not has_verified_contrib:
        # Big-collab guardrail
        if (
            total_authors is not None
            and field_profile is not None
            and total_authors > field_profile.big_collab_threshold
        ):
            base = min(base, BIG_COLLAB_GUARDED_FLOOR)
        # Consortium guardrail (separate from big-collab — applies even
        # when total_authors ≤ threshold for some reason)
        if author_role == "consortium":
            base = min(base, CONSORTIUM_NO_EVIDENCE_FACTOR * baseline)

    base += contribution_bonus(
        contribution_role, has_evidence=has_contribution_evidence,
    )

    # Final cap at baseline — bonuses can lift but not exceed tier ceiling.
    return min(base, baseline)


def validate_paper_contributions(papers: list[dict]) -> list[str]:
    """v2: warn when `contribution_role` is set without
    `contribution_evidence`. The role still informs the user but
    contributes 0 to the score until verified."""
    warnings: list[str] = []
    for i, p in enumerate(papers):
        role = p.get("contribution_role")
        if role is None:
            continue
        evidence = p.get("contribution_evidence") or []
        if not evidence:
            warnings.append(
                f"paper[{i}]: contribution_role={role!r} is set but "
                f"contribution_evidence is empty. The bonus is dropped "
                f"(role informational only). Cite a paper acknowledgement, "
                f"corresponding-author note, or the candidate's own CV."
            )
    return warnings


def aggregate_papers(scores: list[float]) -> float:
    """Top-3 weighted aggregation."""
    if not scores:
        return NO_PAPER_FLOOR

    sorted_scores = sorted(scores, reverse=True)
    n = len(sorted_scores)

    if n == 1:
        return sorted_scores[0]
    if n == 2:
        return 0.7 * sorted_scores[0] + 0.3 * sorted_scores[1]
    return 0.5 * sorted_scores[0] + 0.3 * sorted_scores[1] + 0.2 * sorted_scores[2]


def pub_score(
    papers: list[dict],
    field_profile: FieldProfile | None = None,
    *,
    current_year: int | None = None,
) -> float:
    """Compute Pub Score (P) on 4.0 scale.

    Each paper dict needs at least `journal_tier` + `author_position`.
    Optional per-paper fields: `status`, `author_role`, `total_authors`,
    `year`, `contribution_role`, `contribution_evidence` (v2).
    `field_profile` (if provided) flows into paper-status weighting and
    the big-collab guardrail. `current_year` (v2) drives the recency
    multiplier; defaults to `datetime.now().year`.
    """
    paper_scores = [
        paper_score(
            p["journal_tier"],
            p["author_position"],
            p.get("status", "published"),
            author_role=p.get("author_role"),
            field_profile=field_profile,
            year=p.get("year"),
            total_authors=p.get("total_authors"),
            contribution_role=p.get("contribution_role"),
            has_contribution_evidence=bool(p.get("contribution_evidence") or []),
            current_year=current_year,
        )
        for p in papers
    ]
    return aggregate_papers(paper_scores)
