"""Applicant model v2 — how strong the applicant is, independent of any PI.

The v1 engine described the applicant with three numbers: P (papers),
E (the single best research experience) and G (raw GPA). That misses most
of what a PhD admissions committee actually reads:

- **GPA without context.** A 3.6 from Tsinghua and a 3.6 from an unranked
  college scored identically; class rank, major-course GPA, trend and
  graduate coursework were ignored, and a master's degree didn't count.
- **No letters.** Recommendation letters are, by most committee accounts,
  the single most read part of a PhD file. v1 had no place for them.
- **Experience = one best project.** Depth (a second solid project),
  ownership (led vs assisted) and relevance to the target field were
  invisible.
- **No honors / tests.** Olympiad medals, national scholarships, Subject
  GRE and English-test screening risk were invisible.
- **Fully compensatory.** A weighted average lets a strong pillar paper
  over a GPA that would be screened out, and gives nothing extra for a
  genuine standout ("spike").

This module turns the student's own, user-provided facts into an
`ApplicantAssessment` with five pillars on the 4.0 scale (academic,
research output, research experience, letters) plus bounded bonuses
(honors, tests, spike), a tier label, a confidence level from input
coverage, and plain-language strengths / weaknesses / missing inputs.
The matcher uses the same pillars inside CAPEG (see `tier_applicant_score`)
and applies a tier-dependent academic screening floor.

Back-compat contract: a profile with none of the v2 fields set scores
exactly as v1 inside the matcher (same P, E, G, no letters pillar, no
bonuses) unless a pillar is a genuine spike (≥ 3.8), which now earns a
small bonus.

> **Constants are v2 defaults; recalibrate against real outcomes.** They
> are educated guesses built from public admissions-committee guidance,
> not fitted values.
"""

from __future__ import annotations

from phd_matcher.models import (
    ApplicantAssessment,
    ApplicantTier,
    Experience,
    FieldProfile,
    InstitutionTier,
    Recommender,
    StudentProfile,
)
from phd_matcher.scoring import experience as experience_module
from phd_matcher.scoring import gpa as gpa_module
from phd_matcher.scoring import pub as pub_module

SCALE_MAX = 4.0


def _clip(x: float, lo: float = 0.0, hi: float = SCALE_MAX) -> float:
    return max(lo, min(hi, x))


def _interp(x: float, anchors: tuple[tuple[float, float], ...]) -> float:
    """Piecewise-linear interpolation through ascending-x anchors."""
    if x <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:], strict=False):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return anchors[-1][1]


# ===========================================================================
# 1. Academic record (G v2)
# ===========================================================================

# Offset added to the 4.0-scale GPA to account for the institution's
# selectivity and grading. Intentionally small: context, not a second
# prestige pillar.
INSTITUTION_OFFSET: dict[str, float] = {
    "elite":        +0.15,
    "very_strong":  +0.08,
    "strong":        0.00,
    "good":         -0.10,
    "other":        -0.20,
}

# Class rank (fraction of cohort at or above the student) → 4.0 scale.
RANK_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.01, 4.00),
    (0.05, 3.85),
    (0.10, 3.70),
    (0.20, 3.45),
    (0.35, 3.15),
    (0.50, 2.90),
    (0.75, 2.50),
    (1.00, 2.20),
)

W_RANK = 0.5               # rank vs GPA blend when both are known
W_MAJOR_GPA = 0.6          # major-course GPA vs overall GPA blend
TREND_ADJ: dict[str, float] = {"rising": +0.08, "flat": 0.0, "falling": -0.12}
GRAD_COURSE_STEP = 0.04
GRAD_COURSE_CAP = 0.12
W_MASTER = 0.6             # most recent degree weighs more


def institution_offset(tier: InstitutionTier | None) -> float:
    return 0.0 if tier is None else INSTITUTION_OFFSET[tier]


def rank_to_4_0(percentile_from_top: float) -> float:
    return _interp(percentile_from_top, RANK_ANCHORS)


def academic_components(student: StudentProfile) -> dict[str, float]:
    """Return the academic score and its parts (for transparency)."""
    gpa4 = gpa_module.gpa_score(student.gpa_raw, student.gpa_scale)
    out: dict[str, float] = {"gpa_4_0": gpa4}

    base = gpa4
    if student.major_gpa_raw is not None:
        major4 = gpa_module.gpa_score(student.major_gpa_raw, student.gpa_scale)
        out["major_gpa_4_0"] = major4
        base = (1 - W_MAJOR_GPA) * gpa4 + W_MAJOR_GPA * major4

    if student.class_rank is not None:
        rank4 = rank_to_4_0(student.class_rank.percentile_from_top)
        out["rank_4_0"] = rank4
        base = (1 - W_RANK) * base + W_RANK * rank4

    offset = institution_offset(student.undergrad_tier)
    trend = TREND_ADJ[student.gpa_trend] if student.gpa_trend else 0.0
    grad = 0.0
    if student.graduate_course_count:
        grad = min(GRAD_COURSE_CAP, GRAD_COURSE_STEP * student.graduate_course_count)
    out.update(institution_offset=offset, trend_adj=trend, grad_course_bonus=grad)

    undergrad = _clip(base + offset + trend + grad)
    out["undergrad_academic"] = undergrad

    academic = undergrad
    if student.master_gpa_raw is not None:
        m_scale = student.master_gpa_scale or student.gpa_scale
        master4 = gpa_module.gpa_score(student.master_gpa_raw, m_scale)
        master = _clip(master4 + institution_offset(student.master_tier))
        out["master_academic"] = master
        academic = W_MASTER * master + (1 - W_MASTER) * undergrad

    out["academic"] = _clip(academic)
    return out


def academic_score(student: StudentProfile) -> float:
    return academic_components(student)["academic"]


# ===========================================================================
# 2. Research experience (E v2)
# ===========================================================================

ROLE_ADJ: dict[str, float] = {"lead": +0.15, "core": 0.0, "assistant": -0.15}
RELEVANCE_ADJ: dict[str, float] = {
    "same_subfield": +0.10, "adjacent": 0.0, "different": -0.25,
}
EXP_DEPTH_FLOOR = 3.0
EXP_DEPTH_WEIGHTS: tuple[float, ...] = (0.25, 0.10)


def score_experience_v2(exp: Experience) -> float:
    base = experience_module.score_one_experience(exp.model_dump())
    adj = 0.0
    if exp.role is not None:
        adj += ROLE_ADJ[exp.role]
    if exp.field_relevance is not None:
        adj += RELEVANCE_ADJ[exp.field_relevance]
    return _clip(base + adj)


def research_experience_score(experiences: list[Experience]) -> float:
    """Best experience + headroom-scaled depth bonus from the next two.

    Same shape as the publication aggregate: one experience scores exactly
    its own value (v1 behaviour), extra experiences never lower the score,
    and only experiences above 3.0 add depth (a month of "participation"
    adds nothing).
    """
    if not experiences:
        return 2.0
    ranked = sorted((score_experience_v2(e) for e in experiences), reverse=True)
    best = ranked[0]
    span = SCALE_MAX - EXP_DEPTH_FLOOR
    bonus = sum(
        w * _clip((s - EXP_DEPTH_FLOOR) / span, 0.0, 1.0)
        for w, s in zip(EXP_DEPTH_WEIGHTS, ranked[1:], strict=False)
    )
    return _clip(best + (SCALE_MAX - best) * bonus)


# ===========================================================================
# 3. Letters (L) — new pillar
# ===========================================================================

RELATIONSHIP_SCORE: dict[str, float] = {
    "research_supervisor":   4.0,
    "research_collaborator": 3.6,
    "course_instructor":     3.0,
    "employer":              3.0,
    "other":                 2.5,
}
LETTER_STRENGTH_SCORE: dict[str, float] = {
    "exceptional": 4.0, "strong": 3.6, "good": 3.0, "unknown": 3.2,
}
FAMILIARITY_ANCHORS: tuple[tuple[float, float], ...] = (
    (0, 2.4), (6, 3.0), (12, 3.5), (24, 4.0),
)
W_STANDING = 0.35
W_RELATIONSHIP = 0.30
W_FAMILIARITY = 0.15
W_LETTER_STRENGTH = 0.20

LETTER_SLOT_WEIGHTS: tuple[float, ...] = (0.45, 0.35, 0.20)
LETTER_SLOTS = len(LETTER_SLOT_WEIGHTS)


def score_letter(rec: Recommender) -> float:
    standing = experience_module.lab_prestige_score(rec.standing)
    return (
        W_STANDING * standing
        + W_RELATIONSHIP * RELATIONSHIP_SCORE[rec.relationship]
        + W_FAMILIARITY * _interp(rec.months_known, FAMILIARITY_ANCHORS)
        + W_LETTER_STRENGTH * LETTER_STRENGTH_SCORE[rec.expected_strength]
    )


def letters_score(recommenders: list[Recommender]) -> float | None:
    """Top-3 described letters, slot weights 0.45 / 0.35 / 0.20
    renormalised over the letters actually described. None when no
    recommenders were described (unknown, not zero).

    Undescribed slots are not filled with a guessed value: that made
    describing one real, strong letter score *below* describing none.
    Instead the letters pillar's weight scales with `letters_coverage`.
    """
    if not recommenders:
        return None
    ranked = sorted((score_letter(r) for r in recommenders), reverse=True)[:LETTER_SLOTS]
    weights = LETTER_SLOT_WEIGHTS[:len(ranked)]
    return sum(w * s for w, s in zip(weights, ranked, strict=True)) / sum(weights)


def letters_coverage(recommenders: list[Recommender]) -> float:
    """Fraction of the usual three letters that were described (0-1)."""
    return min(len(recommenders), LETTER_SLOTS) / LETTER_SLOTS


# ===========================================================================
# 4. Bonuses — honors, tests, spike (bounded, never a pillar)
# ===========================================================================

HONOR_LEVEL_BONUS: dict[str, float] = {
    "international": 0.15,
    "national":      0.10,
    "regional":      0.05,
    "university":    0.02,
    "other":         0.00,
}
HONOR_EXTRA_STEP = 0.02     # each further honor at regional level or above
HONORS_CAP = 0.18


def honors_bonus(student: StudentProfile) -> float:
    if not student.honors:
        return 0.0
    values = sorted((HONOR_LEVEL_BONUS[h.level] for h in student.honors), reverse=True)
    extra = sum(HONOR_EXTRA_STEP for v in values[1:] if v >= HONOR_LEVEL_BONUS["regional"])
    return min(HONORS_CAP, values[0] + extra)


# Minimum English scores most US PhD programs list.
ENGLISH_MINIMUM: dict[str, float] = {"toefl": 90, "ielts": 6.5, "duolingo": 110}
ENGLISH_BELOW_MIN_ADJ = -0.08


def standardized_tests_adjustment(student: StudentProfile) -> tuple[float, list[str]]:
    """Small ± adjustment from standardized tests, plus risk flags."""
    t = student.test_scores
    if t is None:
        return 0.0, []
    adj = 0.0
    flags: list[str] = []
    if t.subject_gre_percentile is not None:
        p = t.subject_gre_percentile
        adj += 0.06 if p >= 90 else 0.03 if p >= 75 else -0.05 if p < 40 else 0.0
    if t.gre_quant_percentile is not None:
        q = t.gre_quant_percentile
        adj += 0.02 if q >= 90 else -0.03 if q < 50 else 0.0
    if t.english_test in ENGLISH_MINIMUM and t.english_score is not None:
        minimum = ENGLISH_MINIMUM[t.english_test]
        if t.english_score < minimum:
            adj += ENGLISH_BELOW_MIN_ADJ
            flags.append(
                f"{t.english_test.upper()} {t.english_score:g} is below the common "
                f"minimum of {minimum:g}; some programs screen these files out"
            )
    return adj, flags


SPIKE_THRESHOLD = 3.8
SPIKE_ONE = 0.05
SPIKE_TWO = 0.08


def spike_bonus(pillars: dict[str, float | None]) -> float:
    """Committees reward a genuine standout. Applies to research-side
    pillars (P, E, L) only; a perfect GPA alone is not a spike."""
    n = sum(
        1 for k in ("P", "E", "L")
        if pillars.get(k) is not None and pillars[k] >= SPIKE_THRESHOLD  # type: ignore[operator]
    )
    return SPIKE_TWO if n >= 2 else SPIKE_ONE if n == 1 else 0.0


# ===========================================================================
# 5. Composite
# ===========================================================================

# Neutral (tier-free) pillar weights for the stand-alone applicant view.
NEUTRAL_WEIGHTS: dict[str, float] = {"P": 0.30, "E": 0.25, "G": 0.20, "L": 0.25}
# Share of the applicant block given to letters inside the matcher.
LETTERS_SHARE = 0.25


def composite(
    pillars: dict[str, float | None],
    weights: dict[str, float],
    *,
    l_coverage: float = 1.0,
) -> float:
    """Weighted mean over the pillars that are known. The letters weight is
    scaled by `l_coverage`, so an undescribed letter is unknown (its weight
    goes to the other pillars), not weak; confidence reports the gap."""
    w = dict(weights)
    if "L" in w:
        w["L"] *= l_coverage
    known = {k: v for k, v in pillars.items() if v is not None and w.get(k)}
    total_w = sum(w[k] for k in known)
    if total_w <= 0:
        return 0.0
    return sum(w[k] * v for k, v in known.items()) / total_w  # type: ignore[operator]


def tier_label(strength: float) -> ApplicantTier:
    if strength >= 3.70:
        return "exceptional"
    if strength >= 3.35:
        return "strong"
    if strength >= 3.00:
        return "competitive"
    return "developing"


_PILLAR_NAMES = {
    "G": "academic record",
    "P": "publications",
    "E": "research experience",
    "L": "recommendation letters",
}


def _inputs_checklist(student: StudentProfile) -> list[tuple[bool, str]]:
    """(provided?, how to add it) for the optional v2 inputs."""
    exps = student.experiences
    return [
        (student.undergrad_tier is not None,
         "undergraduate institution tier (puts the GPA in context)"),
        (student.class_rank is not None or student.major_gpa_raw is not None,
         "class rank or major-course GPA"),
        (bool(student.recommenders),
         "who will write your recommendation letters and how well they know you"),
        (bool(exps) and all(
            e.role is not None and e.field_relevance is not None for e in exps),
         "your role in each research project and how close it is to the target field"),
        (student.gpa_trend is not None or student.graduate_course_count is not None,
         "GPA trend or number of graduate-level courses taken"),
        (student.test_scores is not None,
         "test scores (Subject GRE / English test), if you have them"),
    ]


def assess_applicant(
    student: StudentProfile,
    field_profile: FieldProfile | None = None,
) -> ApplicantAssessment:
    """Assess the applicant from user-provided facts only."""
    acad = academic_components(student)
    g = acad["academic"]
    p = pub_module.pub_score(
        [pp.model_dump() for pp in student.papers], field_profile=field_profile,
    )
    e = research_experience_score(student.experiences)
    l_score = letters_score(student.recommenders)
    pillars: dict[str, float | None] = {"G": g, "P": p, "E": e, "L": l_score}

    h = honors_bonus(student)
    t_adj, flags = standardized_tests_adjustment(student)
    spike = spike_bonus(pillars)
    l_cov = letters_coverage(student.recommenders)
    strength = _clip(
        composite(pillars, NEUTRAL_WEIGHTS, l_coverage=l_cov) + h + t_adj + spike
    )

    checklist = _inputs_checklist(student)
    provided = sum(1 for ok, _ in checklist if ok)
    confidence = "high" if provided >= 4 else "medium" if provided >= 2 else "low"

    strengths: list[str] = []
    weaknesses: list[str] = []
    for key, value in pillars.items():
        if value is None:
            continue
        if value >= 3.6:
            strengths.append(f"{_PILLAR_NAMES[key]} ({value:.2f})")
        elif value <= 2.8:
            weaknesses.append(f"{_PILLAR_NAMES[key]} ({value:.2f})")
    if not student.papers:
        weaknesses.append("no publications or preprints yet")
    if h >= HONOR_LEVEL_BONUS["national"]:
        strengths.append(f"national-level or higher honors (+{h:.2f})")
    if spike:
        strengths.append(f"standout research-side pillar (+{spike:.2f})")
    if student.gpa_trend == "falling":
        weaknesses.append("falling GPA trend")
    if student.recommenders and len(student.recommenders) < 3:
        flags.append(
            f"only {len(student.recommenders)} recommender(s) described; most "
            f"programs require three letters"
        )
    if student.recommenders and not any(
        r.relationship in ("research_supervisor", "research_collaborator")
        for r in student.recommenders
    ):
        weaknesses.append("no letter from someone who supervised your research")

    components = {k: round(v, 3) for k, v in acad.items()}
    components.update(
        P=round(p, 3), E=round(e, 3), G=round(g, 3),
        **({"L": round(l_score, 3)} if l_score is not None else {}),
    )

    return ApplicantAssessment(
        academic_score=round(g, 4),
        research_output_score=round(p, 4),
        research_experience_score=round(e, 4),
        letters_score=(round(l_score, 4) if l_score is not None else None),
        letters_coverage=round(l_cov, 4),
        honors_bonus=round(h, 4),
        tests_adj=round(t_adj, 4),
        spike_bonus=round(spike, 2),
        applicant_strength=round(strength, 2),
        tier=tier_label(strength),
        confidence=confidence,
        inputs_provided=provided,
        inputs_total=len(checklist),
        strengths=strengths,
        weaknesses=weaknesses,
        risk_flags=flags,
        missing_inputs=[hint for ok, hint in checklist if not ok],
        components=components,
    )


# ===========================================================================
# 6. Matcher integration
# ===========================================================================

def tier_applicant_score(
    assessment: ApplicantAssessment,
    tier_weights: dict[str, float],
) -> float:
    """The applicant block of CAPEG for one school tier, normalised to the
    4.0 scale (multiply by w_P + w_E + w_G to get its match contribution).

    P / E / G keep the tier's relative emphasis; letters, when described,
    take `LETTERS_SHARE × letters_coverage` of the block. Bonuses are added on top. With no v2
    inputs this equals ``(w_P·P + w_E·E + w_G·G) / (w_P + w_E + w_G)`` —
    exactly the v1 contribution — plus any spike bonus.
    """
    w_peg = tier_weights["P"] + tier_weights["E"] + tier_weights["G"]
    core = (
        tier_weights["P"] * assessment.research_output_score
        + tier_weights["E"] * assessment.research_experience_score
        + tier_weights["G"] * assessment.academic_score
    ) / w_peg
    if assessment.letters_score is not None:
        share = LETTERS_SHARE * assessment.letters_coverage
        core = (1 - share) * core + share * assessment.letters_score
    bonuses = assessment.honors_bonus + assessment.tests_adj + assessment.spike_bonus
    return _clip(core + bonuses)


# Academic screening floors (4.0 scale) by target tier. Below the floor a
# file risks being cut before anyone reads the research — strong research
# and connections help, but they don't fully compensate.
SCREEN_FLOOR: dict[str, float] = {
    "top_10":      3.30,
    "top_11_30":   3.10,
    "top_31_60":   2.90,
    "top_60_plus": 2.70,
}
SCREEN_SLOPE = 0.40


def academic_screen_penalty(academic: float, school_tier: str) -> float:
    return SCREEN_SLOPE * max(0.0, SCREEN_FLOOR[school_tier] - academic)
