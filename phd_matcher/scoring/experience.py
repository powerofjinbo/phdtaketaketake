"""Experience score (E) — per Scoring Design v0.3 §4."""

# Lab prestige tiers (v0.3 §4.1, 6 tiers)
LAB_PRESTIGE: dict[str, float] = {
    "world_class":           4.0,    # HHMI / Max Planck / NAS member / Top 10 US PI / national lab
    "top_us":                3.7,    # Top 11–40 US PI
    "strong_us_or_top_cn":   3.5,    # Top 41–70 US PI / Tsinghua/PKU/Fudan/SJTU/C9 prominent PI
    "good_us_or_985":        3.0,    # Top 71–100 US / 985 regular PI
    "211_or_overseas":       2.5,    # 211 / overseas regular school
    "other":                 2.0,    # rest
}

OUTPUT_TYPE_SCORE: dict[str, float] = {
    "paper":              3.7,    # paper already counted in P; assign best non-paper output here
    "conference_oral":    3.7,
    "conference_poster":  3.3,
    "honors_thesis":      3.0,
    "participation_only": 2.5,
}

# Sub-component weights (v0.3 §4 — output-dominant)
W_LAB = 0.20
W_DURATION = 0.30
W_OUTPUT = 0.50


def lab_prestige_score(lab_tier: str) -> float:
    return LAB_PRESTIGE.get(lab_tier, 2.0)


def duration_score(months: int) -> float:
    if months >= 24: return 4.0
    if months >= 12: return 3.5
    if months >= 6:  return 3.0
    if months >= 3:  return 2.5
    return 2.0


def output_score(output_type: str) -> float:
    return OUTPUT_TYPE_SCORE.get(output_type, 2.5)


def score_one_experience(exp: dict) -> float:
    """Score a single experience: lab × duration × output, weighted."""
    lab = lab_prestige_score(exp["lab_tier"])
    dur = duration_score(int(exp["duration_months"]))
    out = output_score(exp["output_type"])
    return W_LAB * lab + W_DURATION * dur + W_OUTPUT * out


def experience_score(experiences: list[dict]) -> float:
    """Take strongest single experience (no stacking) per v0.3 §4.4."""
    if not experiences:
        return 2.0
    return max(score_one_experience(e) for e in experiences)
