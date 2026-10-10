"""Transcript → coursework signals.

The overall GPA says how well you did on average; the transcript says
*where*. Admissions readers look at three things beyond the headline GPA,
and those are what this module extracts:

  core_gpa     credit-weighted grade points on courses core to the field
               (quantum / E&M / stat-mech for physics, algorithms / systems
               for CS, …). Marked per course via `is_core`, else matched
               against the field's keyword list in data/admission/priors.yaml.
  n_graduate   graduate-level courses passed with B+ or better — the most
               direct signal that you can already handle PhD coursework.
  trend        late-years minus early-years grade points (upward trends are
               read favourably; a late slump is a flag).

All grades are normalized to the 4.0 scale used by the rest of the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from phd_matcher.admission.models import Course, Transcript
from phd_matcher.scoring import gpa

LETTER_POINTS: dict[str, float] = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
    # Five-level Chinese grading
    "优": 4.0, "优秀": 4.0, "良": 3.3, "良好": 3.3,
    "中": 2.7, "中等": 2.7, "及格": 2.0, "不及格": 0.0,
}

# Pass/fail style grades carry no grade points and are skipped.
NON_GRADED = {"P", "PASS", "S", "CR", "通过", "合格", "W", "I", "NP"}

GOOD_GRADE_POINTS = 3.3


def grade_points(
    grade: str | float, scale: str | None, gpa_scale_hint: str = "4.0",
) -> float | None:
    """Convert one course grade to 4.0-scale points. None = not graded."""
    if isinstance(grade, str):
        g = grade.strip()
        if not g:
            return None
        if g.upper() in NON_GRADED or g in NON_GRADED:
            return None
        if g.upper() in LETTER_POINTS:
            return LETTER_POINTS[g.upper()]
        if g in LETTER_POINTS:
            return LETTER_POINTS[g]
        try:
            value = float(g)
        except ValueError:
            return None
    else:
        value = float(grade)

    if scale == "letter":
        scale = None  # numeric grade on a letter transcript → infer
    if scale is None:
        if value > 5.0:
            scale = "100"
        elif gpa_scale_hint in ("4.3", "4.5") and value <= float(gpa_scale_hint):
            scale = gpa_scale_hint
        elif value <= 4.0:
            scale = "4.0"
        elif value <= 4.3:
            scale = "4.3"
        else:
            scale = "4.5"
    # Same conversion as the headline GPA (scoring.gpa), so the transcript
    # and the GPA agree on what a grade is worth.
    return gpa.gpa_score(value, scale)


def is_core_course(course: Course, keywords: list[str]) -> bool:
    if course.is_core is not None:
        return course.is_core
    name = course.name.lower()
    return any(k.lower() in name for k in keywords)


@dataclass
class CourseworkSignals:
    core_gpa: float | None
    overall_course_gpa: float | None
    n_core: int
    n_graded: int
    n_graduate_good: int
    trend: float | None
    used_all_courses_as_core: bool
    notes: list[str] = field(default_factory=list)


def _weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return None
    return sum(v * w for v, w in pairs) / total_w


def coursework_signals(
    transcript: Transcript, core_keywords: list[str], gpa_scale_hint: str = "4.0",
) -> CourseworkSignals:
    graded: list[tuple[Course, float]] = []
    for c in transcript.courses:
        pts = grade_points(c.grade, transcript.grade_scale, gpa_scale_hint)
        if pts is not None:
            graded.append((c, pts))

    notes: list[str] = []
    all_pairs = [(pts, c.credits or 1.0) for c, pts in graded]
    core_pairs = [(pts, c.credits or 1.0) for c, pts in graded if is_core_course(c, core_keywords)]
    used_all = False
    if not core_pairs and all_pairs:
        core_pairs = all_pairs
        used_all = True
        notes.append("no core courses identified — mark is_core on transcript lines")

    n_grad_good = sum(
        1 for c, pts in graded if c.level == "graduate" and pts >= GOOD_GRADE_POINTS
    )

    early = [(pts, c.credits or 1.0) for c, pts in graded if c.year is not None and c.year <= 2]
    late = [(pts, c.credits or 1.0) for c, pts in graded if c.year is not None and c.year >= 3]
    trend: float | None = None
    if len(early) >= 2 and len(late) >= 2:
        e, lt = _weighted_mean(early), _weighted_mean(late)
        if e is not None and lt is not None:
            trend = lt - e

    return CourseworkSignals(
        core_gpa=_weighted_mean(core_pairs),
        overall_course_gpa=_weighted_mean(all_pairs),
        n_core=len(core_pairs) if not used_all else 0,
        n_graded=len(graded),
        n_graduate_good=n_grad_good,
        trend=trend,
        used_all_courses_as_core=used_all,
        notes=notes,
    )
