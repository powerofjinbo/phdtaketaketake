"""Applicant-side advice built on the applicant model v2.

Three features, all derived from the student's own profile and the ranked
results — none of them changes a score:

- `tier_readiness` — for each school tier, how the profile compares with
  the typical admit there *before* any PI-specific signal. Answers "which
  tiers is my file competitive for on its own?".
- `improvement_plan` — what-if analysis. Each realistic change (a research
  letter, a first-author preprint, a longer project, graduate courses …) is
  simulated on a copy of the profile and ranked by how much it would move
  the applicant composite. Hypothetical by construction: nothing is written
  back, and every action carries the assumption it rests on.
- `build_application_list` — a balanced shortlist (reach / target / safer)
  from ranked `MatchResult`s, skipping drops, capping PIs per institution,
  and warning when the list has no safer options.

> **Constants are v2 defaults; recalibrate against real outcomes.**
"""

from __future__ import annotations

from collections.abc import Callable

from phd_matcher.models import (
    ApplicantAssessment,
    ApplicationPick,
    ApplicationPlan,
    FieldProfile,
    ImprovementAction,
    MatchResult,
    Paper,
    Recommender,
    StudentProfile,
    TierReadiness,
)
from phd_matcher.scoring import admit
from phd_matcher.scoring import applicant as applicant_module

# ---- Tier readiness ------------------------------------------------------

# Typical admitted applicant composite per tier (4.0 scale, connection and
# PI opportunity excluded). Educated defaults, not fitted.
TYPICAL_ADMIT_BAR: dict[str, float] = {
    "top_10":      3.55,
    "top_11_30":   3.30,
    "top_31_60":   3.05,
    "top_60_plus": 2.75,
}
AT_BAR_TOLERANCE = 0.15


def tier_readiness(assessment: ApplicantAssessment) -> list[TierReadiness]:
    out: list[TierReadiness] = []
    for tier, weights in admit.TIER_WEIGHTS.items():
        s_tier = applicant_module.tier_applicant_score(assessment, weights)
        screen = applicant_module.academic_screen_penalty(
            assessment.academic_score, tier,
        )
        bar = TYPICAL_ADMIT_BAR[tier]
        margin = s_tier - screen - bar
        if margin >= AT_BAR_TOLERANCE:
            verdict, note = "above_bar", "profile alone is competitive here"
        elif margin > -AT_BAR_TOLERANCE:
            verdict, note = "at_bar", (
                "on the bubble; a verified connection or strong research fit "
                "decides it"
            )
        else:
            verdict, note = "below_bar", (
                "profile alone is under the typical admit; apply only where a "
                "strong connection or fit compensates"
            )
        if screen > 0:
            note += f"; academic record is under this tier's screening floor (−{screen:.2f})"
        out.append(TierReadiness(
            school_tier=tier,  # type: ignore[arg-type]
            applicant_score=round(s_tier, 2),
            screen_penalty=round(screen, 2),
            typical_admit_bar=bar,
            margin=round(margin, 2),
            verdict=verdict,  # type: ignore[arg-type]
            note=note,
        ))
    return out


# ---- Improvement plan (what-if) -----------------------------------------

_Mutation = Callable[[StudentProfile], StudentProfile | None]


def _best_lab_standing(student: StudentProfile) -> str:
    order = ["world_class", "top_us", "strong_us_or_top_cn",
             "good_us_or_985", "211_or_overseas", "other"]
    tiers = [e.lab_tier for e in student.experiences]
    return min(tiers, key=order.index) if tiers else "good_us_or_985"


def _add_research_letter(s: StudentProfile) -> StudentProfile | None:
    has_strong_research_letter = any(
        r.relationship == "research_supervisor" and r.months_known >= 12
        and r.expected_strength in ("strong", "exceptional")
        for r in s.recommenders
    )
    # With no letters described the letters pillar is unknown (excluded,
    # not zero), so a what-if against it would compare apples to nothing.
    # That case is an information gap, reported via `missing_inputs`.
    if has_strong_research_letter or not s.experiences or not s.recommenders:
        return None
    new = Recommender(
        name="(hypothetical) research supervisor",
        standing=_best_lab_standing(s),  # type: ignore[arg-type]
        relationship="research_supervisor",
        months_known=max(12, max(e.duration_months for e in s.experiences)),
        expected_strength="strong",
    )
    recs = sorted(s.recommenders, key=applicant_module.score_letter, reverse=True)
    recs = (recs[:2] if len(recs) >= 3 else recs) + [new]
    return s.model_copy(update={"recommenders": recs})


def _first_author_preprint(s: StudentProfile) -> StudentProfile | None:
    if any(p.author_position == 1 and p.status != "in_prep" for p in s.papers):
        return None
    if not s.experiences:
        return None
    paper = Paper(title="(hypothetical) first-author preprint",
                  journal_tier=3, author_position=1, status="preprint")
    return s.model_copy(update={"papers": [*s.papers, paper]})


def _submit_in_prep(s: StudentProfile) -> StudentProfile | None:
    if not any(p.status == "in_prep" for p in s.papers):
        return None
    papers = [
        p.model_copy(update={"status": "submitted"}) if p.status == "in_prep" else p
        for p in s.papers
    ]
    return s.model_copy(update={"papers": papers})


def _extend_project(s: StudentProfile) -> StudentProfile | None:
    if not s.experiences:
        return None
    best = max(s.experiences, key=applicant_module.score_experience_v2)
    if best.duration_months >= 12:
        return None
    exps = [
        e.model_copy(update={"duration_months": 12}) if e is best else e
        for e in s.experiences
    ]
    return s.model_copy(update={"experiences": exps})


def _graduate_courses(s: StudentProfile) -> StudentProfile | None:
    current = s.graduate_course_count or 0
    if current >= 3:
        return None
    return s.model_copy(update={"graduate_course_count": current + 2})


def _clear_english_minimum(s: StudentProfile) -> StudentProfile | None:
    t = s.test_scores
    if t is None or t.english_test not in applicant_module.ENGLISH_MINIMUM:
        return None
    minimum = applicant_module.ENGLISH_MINIMUM[t.english_test]
    if t.english_score is None or t.english_score >= minimum:
        return None
    return s.model_copy(update={
        "test_scores": t.model_copy(update={"english_score": minimum}),
    })


_ACTIONS: tuple[tuple[str, str, str, str, _Mutation], ...] = (
    ("Secure a strong letter from a research supervisor who knows your work",
     "L", "medium",
     "a supervisor from your strongest lab, ≥12 months, writes a strong letter",
     _add_research_letter),
    ("Write up your current project as a first-author preprint",
     "P", "high",
     "a tier-3-equivalent first-author preprint (0.7 credit until accepted)",
     _first_author_preprint),
    ("Submit your in-prep manuscript(s) before applying",
     "P", "medium",
     "in-prep papers move to submitted (0.3 → 0.7 credit)",
     _submit_in_prep),
    ("Extend your strongest project to 12 months",
     "E", "medium",
     "the same project continues to 12 months with the same output",
     _extend_project),
    ("Take two more graduate-level courses",
     "G", "medium",
     "two additional graduate courses completed before applying",
     _graduate_courses),
    ("Retake the English test to clear the common minimum",
     "tests", "low",
     "the retake reaches the usual minimum score",
     _clear_english_minimum),
)


def improvement_plan(
    student: StudentProfile,
    field_profile: FieldProfile | None = None,
    *,
    min_delta: float = 0.01,
) -> list[ImprovementAction]:
    """Simulate each applicable action and rank by gain in
    `applicant_strength`. Actions that don't apply or don't help are
    omitted."""
    base = applicant_module.assess_applicant(student, field_profile)
    out: list[ImprovementAction] = []
    for action, pillar, effort, assumption, mutate in _ACTIONS:
        changed = mutate(student)
        if changed is None:
            continue
        after = applicant_module.assess_applicant(changed, field_profile)
        delta = after.applicant_strength - base.applicant_strength
        if delta < min_delta:
            continue
        out.append(ImprovementAction(
            action=action,
            pillar=pillar,  # type: ignore[arg-type]
            effort=effort,  # type: ignore[arg-type]
            delta_strength=round(delta, 2),
            new_strength=after.applicant_strength,
            assumption=assumption,
        ))
    effort_rank = {"low": 0, "medium": 1, "high": 2}
    out.sort(key=lambda a: (-a.delta_strength, effort_rank[a.effort]))
    return out


# ---- Application list builder ------------------------------------------

REACH_BELOW = 2.5      # difficulty_adjusted_strength under this → reach
SAFER_FROM = 3.0       # at or above this → safer
MAX_PER_INSTITUTION = 2
DEFAULT_LIST_SIZE = 12
BAND_SHARE = {"reach": 0.25, "target": 0.50, "safer": 0.25}


def _band(r: MatchResult) -> str:
    d = r.difficulty_adjusted_strength
    if d < REACH_BELOW:
        return "reach"
    if d >= SAFER_FROM:
        return "safer"
    return "target"


def build_application_list(
    results: list[MatchResult],
    size: int = DEFAULT_LIST_SIZE,
) -> ApplicationPlan:
    """Pick a balanced list from ranked results (best first within band).

    Skips candidates whose strategy says skip/drop, keeps at most two PIs
    per institution, aims for 25% reach / 50% target / 25% safer and fills
    any shortfall from the other bands in rank order.
    """
    plan = ApplicationPlan()
    eligible: list[MatchResult] = []
    for r in results:
        if r.strategy is not None and (
            r.strategy.apply_bucket == "drop"
            or r.strategy.recommended_action == "skip"
        ):
            plan.excluded.append(r.candidate.id)
            continue
        eligible.append(r)

    by_band: dict[str, list[MatchResult]] = {"reach": [], "target": [], "safer": []}
    for r in eligible:
        by_band[_band(r)].append(r)

    per_inst: dict[str, int] = {}
    chosen: list[tuple[str, MatchResult]] = []

    def take(band: str, quota: int) -> None:
        for r in list(by_band[band]):
            if quota <= 0 or len(chosen) >= size:
                return
            inst = r.candidate.institution
            if per_inst.get(inst, 0) >= MAX_PER_INSTITUTION:
                continue
            per_inst[inst] = per_inst.get(inst, 0) + 1
            chosen.append((band, r))
            by_band[band].remove(r)
            quota -= 1

    for band, share in BAND_SHARE.items():
        take(band, max(1, round(size * share)))
    for band in ("target", "safer", "reach"):
        take(band, size - len(chosen))

    order = {"reach": 0, "target": 1, "safer": 2}
    chosen.sort(key=lambda br: (order[br[0]], -br[1].difficulty_adjusted_strength))
    for band, r in chosen:
        why = f"{r.strength_label} (difficulty-adjusted {r.difficulty_adjusted_strength:.2f})"
        if r.strategy is not None:
            why += f"; strategy: {r.strategy.apply_bucket}, {r.strategy.recommended_action}"
        plan.picks.append(ApplicationPick(
            candidate_id=r.candidate.id,
            institution=r.candidate.institution,
            band=band,  # type: ignore[arg-type]
            difficulty_adjusted_strength=r.difficulty_adjusted_strength,
            why=why,
        ))
    plan.reach_count = sum(1 for b, _ in chosen if b == "reach")
    plan.target_count = sum(1 for b, _ in chosen if b == "target")
    plan.safer_count = sum(1 for b, _ in chosen if b == "safer")

    if plan.picks and plan.safer_count == 0:
        plan.notes.append(
            "No safer options in this list. Add candidates from lower-difficulty "
            "programs or with verified connections before finalizing."
        )
    if plan.picks and plan.reach_count == 0:
        plan.notes.append(
            "No reach options. Consider one or two ambitious programs where you "
            "have a real connection."
        )
    if len(plan.picks) < size:
        plan.notes.append(
            f"Only {len(plan.picks)} eligible candidates for a list of {size}; "
            f"discover more PIs to fill it."
        )
    return plan
