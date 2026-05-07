"""Publication score (P) — per Scoring Design v0.3, with paper-status
weight and (P1) field-aware author-role + per-field status overrides."""

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
    author_position: int, author_role: str | None = None
) -> int:
    """Compute the position used for tier × decrement scoring.

    Without an `author_role`, returns `author_position` as-is. With a role,
    applies the role override (e.g., `co_first` → 1 regardless of byline).
    """
    if author_role is None:
        return author_position
    return _ROLE_TO_EFFECTIVE_POSITION.get(author_role, author_position)


def paper_score(
    journal_tier: int | str,
    author_position: int,
    status: str = "published",
    *,
    author_role: str | None = None,
    field_profile: FieldProfile | None = None,
) -> float:
    """Score a single paper.

    Position 1–4 (after `author_role` override): `baseline − decrement`.
    Position 5+: `min(3.5, 4-author-score)` — big-collab credit without
    tier inversion.

    Author role (P1, optional): if set, overrides `author_position` for
    scoring (`co_first` / `corresponding` / `senior` → 1).

    Field profile (P1, optional): consulted for per-field status weight
    overrides.
    """
    if author_position < 1:
        raise ValueError(f"author_position must be >= 1, got {author_position}")

    baseline = journal_baseline(journal_tier)
    if baseline == 0.0:
        return 0.0

    pos = effective_position(author_position, author_role)
    if pos <= 4:
        base = baseline - POSITION_DECREMENT[pos]
    else:
        base = min(BIG_COLLAB_FLOOR, baseline - POSITION_DECREMENT[4])

    return base * status_weight(status, field_profile)


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
) -> float:
    """Compute Pub Score (P) on 4.0 scale.

    Each paper dict needs at least `journal_tier` + `author_position`.
    Optional per-paper fields: `status`, `author_role`.
    `field_profile` (if provided) flows into paper-status weighting.
    """
    paper_scores = [
        paper_score(
            p["journal_tier"],
            p["author_position"],
            p.get("status", "published"),
            author_role=p.get("author_role"),
            field_profile=field_profile,
        )
        for p in papers
    ]
    return aggregate_papers(paper_scores)
