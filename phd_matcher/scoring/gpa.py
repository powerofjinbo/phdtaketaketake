"""GPA score (G) — per Scoring Design v0.3 §3."""



# Anchor points (percent, 4.0) of the conservative 100-point conversion.
# Between anchors the mapping is linear, so 89.9 no longer scores 0.3 below
# 90.0. The anchors themselves are the v0.3 table and stay conservative
# (85 → 3.7, punishing grade inflation).
PERCENT_ANCHORS: tuple[tuple[float, float], ...] = (
    (60.0, 2.0),
    (65.0, 2.3),
    (70.0, 2.7),
    (75.0, 3.0),
    (80.0, 3.3),
    (85.0, 3.7),
    (90.0, 4.0),
)


def percentage_to_4_0(percent: float) -> float:
    """Chinese 100-point scale → 4.0 (conservative; punishes grade inflation).

    Piecewise-linear through `PERCENT_ANCHORS`; ≥90 → 4.0, ≤60 → 2.0.
    """
    if percent >= PERCENT_ANCHORS[-1][0]:
        return PERCENT_ANCHORS[-1][1]
    if percent <= PERCENT_ANCHORS[0][0]:
        return PERCENT_ANCHORS[0][1]
    for (x0, y0), (x1, y1) in zip(PERCENT_ANCHORS, PERCENT_ANCHORS[1:], strict=False):
        if percent <= x1:
            return y0 + (y1 - y0) * (percent - x0) / (x1 - x0)
    return PERCENT_ANCHORS[-1][1]  # unreachable


UK_HONOURS_TO_4_0 = {
    "first": 3.8,
    "high_2_1": 3.5,
    "low_2_1": 3.2,
    "2_1": 3.35,        # if not specified high/low, use midpoint
    "2_2": 2.8,
    "third": 2.3,
}


def uk_class_to_4_0(uk_class: str) -> float:
    return UK_HONOURS_TO_4_0.get(uk_class.lower().strip(), 2.0)


def gpa_score(raw: float | str, scale: str = "4.0") -> float:
    """Normalize GPA to 4.0 scale.

    scale ∈ {'4.0', '4.3', '4.5', '100', 'uk'}.
    """
    s = scale.lower().strip()

    if s == "4.0":
        return min(float(raw), 4.0)
    if s == "4.3":
        # On a 4.3 scale A = 4.0 and A+ = 4.3 (A+ is an extra grade above
        # A, not a stretched scale). Dividing by 4.3 used to turn a
        # straight-A transcript into 3.72; cap instead.
        return min(float(raw), 4.0)
    if s == "4.5":
        return min(float(raw) * 4.0 / 4.5, 4.0)
    if s == "100":
        return percentage_to_4_0(float(raw))
    if s == "uk":
        return uk_class_to_4_0(str(raw))

    raise ValueError(f"Unknown GPA scale: {scale!r}. Valid: '4.0', '4.3', '4.5', '100', 'uk'")
