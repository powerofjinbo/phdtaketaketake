"""Publication score (P) — per Scoring Design v0.3, with paper-status weight."""


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

# Paper-status weights (per code review #8). Applied multiplicatively to the
# tier × position score. The user's earlier "all CV papers count fully" rule
# is preserved as the default (status="published"=1.0), but submitted /
# preprint / in-prep get partial credit so they don't game the score.
STATUS_WEIGHT: dict[str, float] = {
    "published":  1.0,
    "accepted":   1.0,
    "in_press":   1.0,
    "submitted":  0.7,
    "preprint":   0.7,
    "in_prep":    0.3,
}


def journal_baseline(tier: int | str) -> float:
    if tier not in TIER_BASELINE:
        raise ValueError(
            f"Unknown journal tier: {tier!r}. Valid: {sorted(TIER_BASELINE.keys(), key=str)}"
        )
    return TIER_BASELINE[tier]


def status_weight(status: str) -> float:
    """Multiplicative weight for a paper status. Raises on unknown status —
    per code review #2, unknown should NOT silently default to 1.0."""
    if status not in STATUS_WEIGHT:
        raise ValueError(
            f"Unknown paper status: {status!r}. "
            f"Valid: {sorted(STATUS_WEIGHT.keys())}"
        )
    return STATUS_WEIGHT[status]


def paper_score(
    journal_tier: int | str,
    author_position: int,
    status: str = "published",
) -> float:
    """Score a single paper. Position 1-4 uses absolute decrement; 5+ uses
    `min(3.5, 4-author-score)` for big-collab credit without tier inversion.
    Result is then multiplied by the paper-status weight."""
    if author_position < 1:
        raise ValueError(f"author_position must be >= 1, got {author_position}")

    baseline = journal_baseline(journal_tier)
    if baseline == 0.0:
        return 0.0

    if author_position <= 4:
        base = baseline - POSITION_DECREMENT[author_position]
    else:
        base = min(BIG_COLLAB_FLOOR, baseline - POSITION_DECREMENT[4])

    return base * status_weight(status)


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


def pub_score(papers: list[dict]) -> float:
    """Compute Pub Score (P) on 4.0 scale. Each paper dict needs at least
    journal_tier + author_position; status defaults to 'published'."""
    paper_scores = [
        paper_score(p["journal_tier"], p["author_position"], p.get("status", "published"))
        for p in papers
    ]
    return aggregate_papers(paper_scores)
