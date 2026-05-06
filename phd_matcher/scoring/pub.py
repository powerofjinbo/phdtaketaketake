"""Publication score (P) — per Scoring Design v0.3 §2."""

from typing import Union

# Journal tier baseline scores (4.0 scale)
TIER_BASELINE: dict[Union[int, str], float] = {
    "S": 4.0,    # cross-disciplinary top (Nature / Science / Cell)
    1: 4.0,      # field flagship
    2: 3.7,      # field upper tier
    3: 3.3,      # field mid tier
    4: 2.8,      # general SCI
    5: 2.3,      # weak / workshop
    0: 0.0,      # retracted / predatory
}

# Absolute decrement per author position (1-indexed)
POSITION_DECREMENT: dict[int, float] = {
    1: 0.0,
    2: 0.10,
    3: 0.25,
    4: 0.45,
}

# 5+ author rule: paper_score = min(BIG_COLLAB_FLOOR, 4-author-score)
BIG_COLLAB_FLOOR = 3.5

# No-paper floor
NO_PAPER_FLOOR = 3.0


def journal_baseline(tier: Union[int, str]) -> float:
    if tier not in TIER_BASELINE:
        raise ValueError(f"Unknown journal tier: {tier!r}. Valid: {sorted(TIER_BASELINE.keys(), key=str)}")
    return TIER_BASELINE[tier]


def paper_score(journal_tier: Union[int, str], author_position: int) -> float:
    """Score a single paper.

    Position 1-4: baseline - decrement.
    Position 5+: min(3.5, 4-author-score) — handles big-collab papers
    (ATLAS/CMS) without inverting low-tier journals.
    """
    if author_position < 1:
        raise ValueError(f"author_position must be >= 1, got {author_position}")

    baseline = journal_baseline(journal_tier)
    if baseline == 0.0:  # retracted
        return 0.0

    if author_position <= 4:
        return baseline - POSITION_DECREMENT[author_position]
    # 5+ rule
    fourth_score = baseline - POSITION_DECREMENT[4]
    return min(BIG_COLLAB_FLOOR, fourth_score)


def aggregate_papers(scores: list[float]) -> float:
    """Top-3 weighted aggregation.

    - 0 papers: NO_PAPER_FLOOR (3.0)
    - 1 paper: that paper's score
    - 2 papers: 0.7 * best + 0.3 * 2nd
    - 3+ papers: 0.5 * best + 0.3 * 2nd + 0.2 * 3rd (only top-3 used)
    """
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
    """Compute Pub Score (P) on 4.0 scale.

    Each paper dict needs: journal_tier, author_position.
    """
    paper_scores = [paper_score(p["journal_tier"], p["author_position"]) for p in papers]
    return aggregate_papers(paper_scores)
