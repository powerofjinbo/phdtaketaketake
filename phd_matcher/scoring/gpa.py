"""GPA score (G) — per Scoring Design v0.3 §3."""



def percentage_to_4_0(percent: float) -> float:
    """Chinese 100-point scale → 4.0 (conservative; punishes grade inflation)."""
    if percent >= 90: return 4.0
    if percent >= 85: return 3.7
    if percent >= 80: return 3.3
    if percent >= 75: return 3.0
    if percent >= 70: return 2.7
    if percent >= 65: return 2.3
    return 2.0


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
        return min(float(raw) * 4.0 / 4.3, 4.0)
    if s == "4.5":
        return min(float(raw) * 4.0 / 4.5, 4.0)
    if s == "100":
        return percentage_to_4_0(float(raw))
    if s == "uk":
        return uk_class_to_4_0(str(raw))

    raise ValueError(f"Unknown GPA scale: {scale!r}. Valid: '4.0', '4.3', '4.5', '100', 'uk'")
