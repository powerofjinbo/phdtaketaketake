"""Input / output models for the admission-probability estimator.

Kept separate from `phd_matcher.models` so the estimator can evolve
without touching the matcher's schema. It reuses the matcher's building
blocks (`Paper`, `Experience`, `CurrentAdvisor`, `CandidateAdvisor`,
`ProgramProfile`, `EvidenceEntry`) so a candidate researched for the
matcher can be passed straight in as an `AdmissionTarget.pi`.

Required applicant inputs (per product decision): GPA, transcript,
publications (an explicit empty list means "no publications"), research
interests and application direction. GRE / Subject GRE are optional.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    EvidenceEntry,
    Experience,
    GPAScale,
    Paper,
    ProgramProfile,
    SchoolTier,
)

ApplicationStage = Literal["pre_application", "interview", "waitlist"]

ContactStatus = Literal[
    "none",                    # no contact with the PI
    "emailed_no_reply",        # emailed, no answer (weakly negative)
    "positive_reply",          # PI replied and encouraged an application
    "meeting_held",            # video / in-person meeting with the PI went well
    "pi_invited_application",  # PI explicitly asked you to apply / will advocate
]

UndergradTier = Literal["elite", "strong", "regular", "unknown"]

LetterProminence = Literal["field_leader", "established", "junior_or_unknown"]

FellowshipStatus = Literal["none", "applying", "secured"]

GradeScale = Literal["letter", "4.0", "4.3", "4.5", "100"]

CourseLevel = Literal["undergrad", "graduate"]

BaseRateSource = Literal[
    "verified_program_stat", "unverified_program_stat", "field_tier_prior",
]

FeatureState = Literal["known", "uncertain", "missing"]

Verdict = Literal["long_shot", "reach", "possible", "competitive", "strong"]

ConfidenceGrade = Literal["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# Applicant
# ---------------------------------------------------------------------------

class Course(BaseModel):
    """One transcript line. `grade` may be a letter ("A-"), a percentage
    ("93") or a GPA point value (3.7) — interpreted with the transcript's
    `grade_scale`, or inferred per course when that is unset."""

    name: str
    grade: str | float
    credits: float | None = Field(default=None, gt=0)
    level: CourseLevel = "undergrad"
    year: int | None = Field(default=None, ge=1, le=8, description="Year of study (1 = first year)")
    is_core: bool | None = Field(
        default=None,
        description="Core to the application field. None → decided by field keyword match.",
    )

    model_config = ConfigDict(extra="forbid")


class Transcript(BaseModel):
    courses: list[Course] = Field(min_length=1)
    grade_scale: GradeScale | None = None
    class_rank_percentile: float | None = Field(
        default=None, gt=0.0, le=100.0,
        description="Class rank as top-X percent (e.g. 5 = top 5%)",
    )

    model_config = ConfigDict(extra="forbid")


class GREGeneral(BaseModel):
    verbal: int | None = Field(default=None, ge=130, le=170)
    quant: int | None = Field(default=None, ge=130, le=170)
    writing: float | None = Field(default=None, ge=0.0, le=6.0)

    model_config = ConfigDict(extra="forbid")


class SubjectGRE(BaseModel):
    subject: str
    score: int | None = Field(default=None, ge=200, le=990)
    percentile: float = Field(ge=0.0, le=100.0)

    model_config = ConfigDict(extra="forbid")


class LetterWriter(BaseModel):
    name: str
    prominence: LetterProminence
    is_research_supervisor: bool = True

    model_config = ConfigDict(extra="forbid")


class SOPSignals(BaseModel):
    """Structured reading of the uploaded statement of purpose.

    Produced by the agent / LLM from the SOP text the user uploaded —
    never invented when no SOP was provided. Treated as an *uncertain*
    observation (an LLM judgement), so it moves the estimate only a little.
    """

    research_specificity: float = Field(
        ge=0.0, le=1.0,
        description="Concrete questions, methods and past results vs. generic enthusiasm",
    )
    direction_coherence: float = Field(
        ge=0.0, le=1.0,
        description="Past work → stated direction → target program form one story",
    )
    names_target_faculty: bool | None = None
    note: str | None = None

    model_config = ConfigDict(extra="forbid")


class AdmissionApplicant(BaseModel):
    name: str | None = None
    field: str
    undergrad_institution: str
    undergrad_tier: UndergradTier = "unknown"
    master_institution: str | None = None

    # ---- Required ----
    gpa_raw: float | str
    gpa_scale: GPAScale
    transcript: Transcript
    publications: list[Paper] = Field(
        description="Required. An empty list is an explicit 'no publications' answer.",
    )
    research_interests: str
    application_direction: str

    # ---- Optional ----
    gre_general: GREGeneral | None = None
    gre_subject: SubjectGRE | None = None
    current_advisors: list[CurrentAdvisor] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    letters: list[LetterWriter] = Field(default_factory=list)
    is_international: bool | None = None
    external_fellowship: FellowshipStatus = "none"
    fellowship_name: str | None = None
    sop: SOPSignals | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("research_interests", "application_direction", "undergrad_institution")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


# ---------------------------------------------------------------------------
# Target (school + optional professor)
# ---------------------------------------------------------------------------

class ProgramAdmissionStats(BaseModel):
    """Program-level admissions numbers, e.g. from the department's
    admissions-statistics page. Either `reported_admit_rate` or both
    `applicants` and `offers`. Evidence goes in `evidence` with
    `supports_fields=["admission:admit_rate"]`; without it the number is
    used but treated as uncertain."""

    reported_admit_rate: float | None = Field(default=None, gt=0.0, lt=1.0)
    applicants: int | None = Field(default=None, gt=0)
    offers: int | None = Field(default=None, ge=0)
    cycle_year: int | None = None
    evidence: EvidenceEntry | None = None

    model_config = ConfigDict(extra="forbid")

    @property
    def admit_rate(self) -> float | None:
        if self.applicants and self.offers is not None and self.offers < self.applicants:
            return max(0.001, self.offers / self.applicants)
        return self.reported_admit_rate


class AdmissionTarget(BaseModel):
    id: str
    institution: str
    program: str | None = None
    school_tier: SchoolTier | None = None
    field: str | None = None
    pi: CandidateAdvisor | None = Field(
        default=None,
        description="The professor, researched exactly like a matcher candidate",
    )
    program_profile: ProgramProfile | None = None
    stats: ProgramAdmissionStats | None = None
    stage: ApplicationStage = "pre_application"
    contact_status: ContactStatus = "none"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _resolve_tier(self) -> AdmissionTarget:
        if self.school_tier is None:
            if self.pi is None:
                raise ValueError("school_tier is required when no pi is given")
            self.school_tier = self.pi.school_tier
        return self

    @property
    def effective_program_profile(self) -> ProgramProfile | None:
        if self.program_profile is not None:
            return self.program_profile
        return self.pi.program_profile if self.pi is not None else None

    @property
    def tier(self) -> SchoolTier:
        assert self.school_tier is not None  # set by the validator
        return self.school_tier


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

class FactorContribution(BaseModel):
    key: str
    label: str
    label_zh: str
    state: FeatureState
    z: float = Field(description="Posterior mean, in applicant-pool standard deviations")
    weight: float = Field(description="Index weight (admission-model mixture)")
    delta_pp: float = Field(
        description="Percentage-point change vs. an average applicant on this factor",
    )
    note: str | None = None

    model_config = ConfigDict(extra="forbid")


class Lever(BaseModel):
    key: str
    label: str
    label_zh: str
    probability: float
    delta_pp: float

    model_config = ConfigDict(extra="forbid")


class AdmissionEstimate(BaseModel):
    target_id: str
    institution: str
    program: str | None = None
    pi_name: str | None = None
    stage: ApplicationStage

    probability: float = Field(ge=0.0, le=1.0, description="P(offer), posterior mean")
    interval_80: tuple[float, float]
    probability_with_pi: float | None = Field(
        default=None, description="P(offer AND you end up in this PI's group)",
    )
    interval_80_with_pi: tuple[float, float] | None = None

    verdict: Verdict
    confidence: ConfidenceGrade
    base_rate: float
    base_rate_source: BaseRateSource
    p_pi_decides: float = Field(description="Weight on the direct-admit (PI decides) model")
    applicant_index: float
    pool_percentile: float = Field(description="Estimated share of this pool you are ahead of")

    factors: list[FactorContribution] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)
    levers: list[Lever] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PortfolioEstimate(BaseModel):
    estimates: list[AdmissionEstimate]
    p_at_least_one: float
    p_at_least_one_if_independent: float
    expected_offers: float
    note: str

    model_config = ConfigDict(extra="forbid")
