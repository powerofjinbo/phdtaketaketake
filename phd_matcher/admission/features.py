"""Applicant / target → standardized feature observations.

Every factor is expressed as a z-score: how many applicant-pool standard
deviations this applicant sits above the *typical applicant to programs of
this tier* (pools self-select, so the same CV is further above the pool at
a top-60 program than at a top-10 one). Each observation carries a state:

  known      the user's own facts (GPA, transcript, papers…) or a claim
             backed by structured evidence — small measurement sd
  uncertain  a claim without evidence, or an LLM judgement (SOP reading,
             keyword-overlap fit) — mean shrunk toward the pool, wide sd
  missing    nothing to go on — the estimator imputes it from what *is*
             known (one-factor model), so the uncertainty shows up as a
             wider interval instead of a guess

Applicant sub-scores come from the matcher's applicant model v2
(`scoring.applicant.assess_applicant`: academic record, research output,
research experience, letters), so the matcher and the estimator describe
the applicant the same way. The transcript, class rank and undergraduate
tier feed the academic score rather than standing as separate factors,
because v2 already folds them in (institution offset, rank blend, major
GPA, trend, graduate courses). Connection and research fit reuse the
matcher's per-PI scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

from phd_matcher.admission.models import AdmissionApplicant, AdmissionTarget, FeatureState
from phd_matcher.admission.priors import FieldPriors
from phd_matcher.admission.transcript import coursework_signals
from phd_matcher.data.loaders import load_field_profile
from phd_matcher.matching.direction import direction_relevance
from phd_matcher.matching.ranker import evidence_coverage
from phd_matcher.models import (
    ClassRank,
    InstitutionTier,
    LabTier,
    Recommender,
    StandardizedTests,
    StudentProfile,
)
from phd_matcher.scoring import applicant as applicant_model
from phd_matcher.scoring import connection, gpa
from phd_matcher.scoring import research_fit as research_fit_module

_N = NormalDist()

# Correlation between applicant-quality features in the pool (strong
# researchers tend to have strong letters, grades, …). Drives both the
# calibration of the intercept and the imputation of missing features.
RHO = 0.4
APPLICANT_LOADING = math.sqrt(RHO)

# Pool (mean, sd) of each sub-score on the 4.0 scale, by school tier.
# Field-specific overrides live in priors.yaml (`pool_overrides`).
POOL: dict[str, dict[str, tuple[float, float]]] = {
    "research": {
        "top_10": (2.5, 0.60), "top_11_30": (2.35, 0.55),
        "top_31_60": (2.25, 0.50), "top_60_plus": (2.15, 0.45),
    },
    "experience": {
        "top_10": (3.25, 0.40), "top_11_30": (3.10, 0.40),
        "top_31_60": (2.95, 0.42), "top_60_plus": (2.80, 0.45),
    },
    # v2 academic score: GPA in context (institution offset, class rank,
    # major GPA, trend, graduate courses). A typical pool applicant from a
    # "strong" school has offset 0, so the old GPA pool still applies.
    "academic": {
        "top_10": (3.75, 0.20), "top_11_30": (3.65, 0.25),
        "top_31_60": (3.50, 0.30), "top_60_plus": (3.35, 0.35),
    },
    # v2 letters score. With only prominence and role known (no months /
    # expected strength), a field leader who supervised your research
    # scores 3.60 and a junior course instructor 2.95; at a top-31-60
    # program those land at about +1.7 and -0.6 sd, as before v2.
    "letters": {
        "top_10": (3.22, 0.28), "top_11_30": (3.17, 0.28),
        "top_31_60": (3.12, 0.28), "top_60_plus": (3.07, 0.28),
    },
}

# Typical Subject-GRE percentile of the pool.
POOL_SUBJECT_GRE_PCT = {"top_10": 0.80, "top_11_30": 0.70, "top_31_60": 0.60, "top_60_plus": 0.50}

# Estimator inputs → applicant model v2 inputs.
UNDERGRAD_TIER_V2: dict[str, InstitutionTier | None] = {
    "elite": "elite", "strong": "strong", "regular": "good", "unknown": None,
}
LETTER_STANDING_V2: dict[str, LabTier] = {
    "field_leader": "world_class",
    "established": "top_us",
    "junior_or_unknown": "good_us_or_985",
}
# Late-minus-early grade points beyond which the trend counts as rising/falling.
TREND_THRESHOLD = 0.15
# Synthetic cohort used to express a top-X% class rank as rank / cohort.
RANK_COHORT = 1000

GRE_QUANT_WEIGHT = 0.02

UNCERTAIN_SHRINK = 0.5
UNCERTAIN_SD = 0.8


@dataclass
class Feature:
    key: str
    label: str
    label_zh: str
    state: FeatureState
    mean: float = 0.0
    sd: float = 0.0
    loading: float = APPLICANT_LOADING
    note: str | None = None


@dataclass
class BonusFeature:
    key: str
    label: str
    label_zh: str
    weight: float
    z: float
    note: str | None = None


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _pool(feature: str, tier: str, fp: FieldPriors) -> tuple[float, float]:
    override = fp.pool_overrides.get(feature, {}).get(tier)
    if override is None and feature == "academic":  # older priors call it "gpa"
        override = fp.pool_overrides.get("gpa", {}).get(tier)
    return override if override is not None else POOL[feature][tier]


def _from_4_0(value: float, scale: str) -> float | None:
    """Inverse of `gpa.gpa_score`: a 4.0-scale value on the profile's own
    GPA scale (on the 100 scale that is a percentage). None for "uk"."""
    if scale in ("4.0", "4.3"):
        return value
    if scale == "4.5":
        return value * 4.5 / 4.0
    if scale == "100":
        anchors = gpa.PERCENT_ANCHORS
        if value >= anchors[-1][1]:
            return anchors[-1][0]
        if value <= anchors[0][1]:
            return anchors[0][0]
        for (x0, y0), (x1, y1) in zip(anchors, anchors[1:], strict=False):
            if value <= y1:
                return x0 + (x1 - x0) * (value - y0) / (y1 - y0)
    return None


def to_student_profile(
    applicant: AdmissionApplicant, core_keywords: list[str] | None = None,
) -> StudentProfile:
    """Project the applicant onto the matcher's StudentProfile so the
    matcher's applicant model v2, scoring and evidence-coverage functions
    can be reused. Only facts the applicant gave are mapped; anything the
    estimator does not ask for stays unset (unknown, not low)."""
    profile = StudentProfile(
        name=applicant.name,
        field=applicant.field,
        undergrad_institution=applicant.undergrad_institution,
        master_institution=applicant.master_institution,
        gpa_raw=applicant.gpa_raw,
        gpa_scale=applicant.gpa_scale,
        research_direction=f"{applicant.application_direction}. {applicant.research_interests}",
        current_advisors=applicant.current_advisors,
        papers=applicant.publications,
        experiences=applicant.experiences,
        undergrad_tier=UNDERGRAD_TIER_V2[applicant.undergrad_tier],
        recommenders=[
            Recommender(
                name=w.name,
                standing=LETTER_STANDING_V2[w.prominence],
                relationship=("research_supervisor" if w.is_research_supervisor
                              else "course_instructor"),
            )
            for w in applicant.letters
        ],
        test_scores=(StandardizedTests(subject_gre_percentile=applicant.gre_subject.percentile)
                     if applicant.gre_subject is not None else None),
    )
    if core_keywords is None:
        return profile

    cw = coursework_signals(applicant.transcript, core_keywords, applicant.gpa_scale)
    update: dict = {}
    if cw.core_gpa is not None and not cw.used_all_courses_as_core:
        major = _from_4_0(cw.core_gpa, applicant.gpa_scale)
        if major is not None:
            update["major_gpa_raw"] = round(major, 3)
    if cw.n_graduate_good:
        update["graduate_course_count"] = cw.n_graduate_good
    if cw.trend is not None:
        update["gpa_trend"] = ("rising" if cw.trend > TREND_THRESHOLD
                               else "falling" if cw.trend < -TREND_THRESHOLD else "flat")
    rank = applicant.transcript.class_rank_percentile
    if rank is not None:
        update["class_rank"] = ClassRank(
            rank=max(1, round(rank / 100.0 * RANK_COHORT)), cohort_size=RANK_COHORT)
    return profile.model_copy(update=update)


def _uncertain(key: str, label: str, label_zh: str, claimed_z: float, note: str,
               loading: float) -> Feature:
    return Feature(key, label, label_zh, "uncertain", UNCERTAIN_SHRINK * claimed_z,
                   UNCERTAIN_SD, loading, note)


def academic_z(g: float, tier: str, fp: FieldPriors) -> float:
    """The academic record works like a threshold: falling below the pool
    hurts a lot, rising above it helps only half as much."""
    mu, sd = _pool("academic", tier, fp)
    z = (g - mu) / sd
    if z > 0:
        z *= 0.5
    return _clip(z, -3.0, 1.25)


def build_features(
    applicant: AdmissionApplicant,
    target: AdmissionTarget,
    fp: FieldPriors,
    data_dir: Path,
) -> tuple[list[Feature], list[BonusFeature]]:
    tier = target.tier
    field_profile = load_field_profile(data_dir, applicant.field)
    student = to_student_profile(applicant, fp.core_course_keywords)
    assessment = applicant_model.assess_applicant(student, field_profile)
    comp = assessment.components
    feats: list[Feature] = []

    # ---- Research output (publications are a required answer) ----------
    p = assessment.research_output_score
    mu, sd = _pool("research", tier, fp)
    note = (f"{len(applicant.publications)} publication(s), score {p:.2f}/4"
            if applicant.publications else "no publications (explicit)")
    feats.append(Feature("research", "Research output", "科研产出（论文）", "known",
                         _clip((p - mu) / sd, -2.5, 3.0), 0.15, note=note))

    # ---- Research experience (v2: role, field relevance, depth) ---------
    if applicant.experiences:
        e = assessment.research_experience_score
        mu, sd = _pool("experience", tier, fp)
        feats.append(Feature("experience", "Research experience", "科研经历", "known",
                             _clip((e - mu) / sd, -2.5, 2.5), 0.15,
                             note=f"{len(applicant.experiences)} experience(s), "
                                  f"score {e:.2f}/4"))
    else:
        feats.append(Feature("experience", "Research experience", "科研经历", "missing",
                             note="no research experience listed"))

    # ---- Academic record (v2: GPA + transcript + rank + institution) ----
    a = assessment.academic_score
    parts = [f"GPA {comp['gpa_4_0']:.2f}/4.0"]
    if "major_gpa_4_0" in comp:
        parts.append(f"core-course GPA {comp['major_gpa_4_0']:.2f}")
    if student.class_rank is not None:
        parts.append(f"rank top {applicant.transcript.class_rank_percentile:g}%")
    if student.graduate_course_count:
        parts.append(f"{student.graduate_course_count} graduate course(s) at B+ or above")
    if student.gpa_trend is not None:
        parts.append(f"{student.gpa_trend} trend")
    if student.undergrad_tier is not None:
        parts.append(f"{applicant.undergrad_tier} institution "
                     f"({comp['institution_offset']:+.2f})")
    cw = coursework_signals(applicant.transcript, fp.core_course_keywords, applicant.gpa_scale)
    parts.extend(cw.notes)
    feats.append(Feature("academic", "Academic record", "学业成绩（GPA / 成绩单）", "known",
                         academic_z(a, tier, fp), 0.15,
                         note=f"score {a:.2f}/4: " + "; ".join(parts)))

    # ---- Letters (v2 letters score; fewer letters → wider) --------------
    if assessment.letters_score is not None:
        mu, sd = _pool("letters", tier, fp)
        n_sup = sum(1 for w in applicant.letters if w.is_research_supervisor)
        cov = max(assessment.letters_coverage, 1e-6)
        feats.append(Feature("letters", "Recommendation letters", "推荐信", "known",
                             _clip((assessment.letters_score - mu) / sd, -2.5, 2.5),
                             0.4 / math.sqrt(cov),
                             note=f"{len(applicant.letters)} writer(s), "
                                  f"{n_sup} research supervisor(s), "
                                  f"score {assessment.letters_score:.2f}/4"))
    else:
        feats.append(Feature("letters", "Recommendation letters", "推荐信", "missing",
                             note="letter writers not listed"))

    # ---- SOP (uploaded → LLM-read) -------------------------------------
    if applicant.sop is not None:
        s = applicant.sop
        z = _clip((0.6 * s.research_specificity + 0.4 * s.direction_coherence - 0.55) / 0.18,
                  -2.0, 2.0)
        if s.names_target_faculty and target.pi is not None:
            z += 0.2
        feats.append(Feature("sop", "Statement of purpose", "个人陈述（SOP）", "uncertain",
                             0.7 * z, 0.6, note=s.note or "LLM reading of the uploaded SOP"))
    else:
        feats.append(Feature("sop", "Statement of purpose", "个人陈述（SOP）", "missing",
                             note="no SOP uploaded"))

    # ---- Target-specific: connection to this PI ------------------------
    feats.append(_connection_feature(applicant, target, student))

    # ---- Target-specific: research fit with this PI --------------------
    feats.append(_fit_feature(applicant, target, student))

    # ---- Optional tests (only ever add information) ---------------------
    bonus: list[BonusFeature] = []
    if applicant.gre_subject is not None and fp.subject_gre_weight > 0:
        pct = _clip(applicant.gre_subject.percentile / 100.0, 0.01, 0.99)
        z = _N.inv_cdf(pct) - _N.inv_cdf(POOL_SUBJECT_GRE_PCT[tier])
        bonus.append(BonusFeature("gre_subject", "Subject GRE", "GRE Sub", fp.subject_gre_weight,
                                  z, note=f"{applicant.gre_subject.subject} "
                                          f"{applicant.gre_subject.percentile:g}th pct"))
    if applicant.gre_general is not None and applicant.gre_general.quant is not None:
        z = _clip((applicant.gre_general.quant - 165) / 3.0, -3.0, 1.0)
        bonus.append(BonusFeature("gre_quant", "GRE Quant", "GRE 数学", GRE_QUANT_WEIGHT, z,
                                  note=f"Q{applicant.gre_general.quant}"))
    return feats, bonus


def _connection_feature(
    applicant: AdmissionApplicant, target: AdmissionTarget, student: StudentProfile,
) -> Feature:
    label, label_zh = "Network connection to the PI", "与导师的学术关系"
    if target.pi is None:
        return Feature("connection", label, label_zh, "missing", loading=0.0,
                       note="no professor specified")
    if not applicant.current_advisors:
        return Feature("connection", label, label_zh, "missing", loading=0.0,
                       note="add your current research advisor(s) to evaluate this")
    cov = evidence_coverage(student, target.pi)
    best_raw: float | None = None
    best_state: FeatureState = "missing"
    for adv in applicant.current_advisors:
        edge = target.pi.paths_to_advisors.get(adv.id)
        name = f"path:{adv.id}"
        if edge is None or name in cov.missing_names:
            continue
        raw = connection.path_strength(edge)
        state: FeatureState = "uncertain" if name in cov.unsourced_names else "known"
        better = best_raw is None or raw > best_raw or (raw == best_raw and state == "known")
        if better:
            best_raw, best_state = raw, state
    if best_raw is None:
        return Feature("connection", label, label_zh, "missing", loading=0.0,
                       note="connection to your advisor(s) not researched yet")
    z = _clip(-0.35 + 3.0 * best_raw, -0.35, 2.5)
    note = (f"strongest verified path {best_raw:.2f}/1" if best_raw > 0
            else "searched, no path found")
    if best_state == "uncertain":
        return _uncertain("connection", label, label_zh, z, note + " (unsourced)", 0.0)
    return Feature("connection", label, label_zh, "known", z, 0.15, loading=0.0, note=note)


def _fit_feature(
    applicant: AdmissionApplicant, target: AdmissionTarget, student: StudentProfile,
) -> Feature:
    label, label_zh = "Research fit with the PI", "研究方向匹配度"
    if target.pi is None:
        return Feature("fit", label, label_zh, "missing", loading=0.0,
                       note="no professor specified")
    f = research_fit_module.effective_research_fit_score(target.pi)
    if f is not None:
        z = _clip((f - 0.55) / 0.18, -2.5, 2.5)
        cov = evidence_coverage(student, target.pi)
        if "research_fit" in cov.unsourced_names:
            return _uncertain("fit", label, label_zh, z, f"fit {f:.2f} (unsourced)", 0.0)
        return Feature("fit", label, label_zh, "known", z, 0.2, loading=0.0, note=f"fit {f:.2f}/1")
    rel = direction_relevance(student.research_direction, target.pi.research_areas)
    if rel > 0:
        z = _clip((rel - 0.3) / 0.2, -1.5, 1.5)
        return _uncertain("fit", label, label_zh, z,
                          f"keyword overlap {rel:.2f} only — structured research_fit "
                          "not given", 0.0)
    return Feature("fit", label, label_zh, "missing", loading=0.0,
                   note="research fit not assessed")
