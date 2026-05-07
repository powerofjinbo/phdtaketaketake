"""Pydantic models for student profiles, candidate advisors, and match results.

Strict validation per code-review #2:
  - Enum-shaped strings use Literal (catches typos at construction time)
  - Numeric scores in 0–1 range use Field(ge=0, le=1)
  - Counts use Field(ge=0)
  - PathEdge uses extra='forbid' so unknown edge keys fail loudly
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enum types — Literal so typos fail at construction
# ---------------------------------------------------------------------------

PaperStatus = Literal[
    "published", "accepted", "in_press", "submitted", "preprint", "in_prep"
]

SchoolTier = Literal["top_10", "top_11_30", "top_31_60", "top_60_plus"]

PISignal = Literal["strong", "normal", "shrinking", "missing", "not_recruiting"]

GenealogyRelation = Literal["same_advisor", "uncle_nephew", "two_hop"]

LabTier = Literal[
    "world_class", "top_us", "strong_us_or_top_cn",
    "good_us_or_985", "211_or_overseas", "other",
]

OutputType = Literal[
    "paper", "conference_oral", "conference_poster",
    "honors_thesis", "participation_only",
]

GPAScale = Literal["4.0", "4.3", "4.5", "100", "uk"]

StrengthLabel = Literal["Far Reach", "Reach", "Target", "Match", "Safe"]


# ---------------------------------------------------------------------------
# Evidence — provenance for any claim the agent makes
# ---------------------------------------------------------------------------

class EvidenceEntry(BaseModel):
    """Sources backing a specific signal value, with audit trail.

    Used in CandidateAdvisor.evidence (keyed by field name). Empty `sources`
    means the agent didn't verify this claim — the matcher counts the signal
    as unverified, widening the confidence band accordingly.
    """

    sources: list[str] = Field(default_factory=list)
    note: str | None = None
    last_checked: str | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# PathEdge — connection edges between one student-advisor and a candidate
# ---------------------------------------------------------------------------

class PathEdge(BaseModel):
    """Per-(student-advisor, candidate) connection signals.

    All fields optional. The matcher takes the **max** strength across present
    signals (no stacking). `sources` is required by the data-integrity policy
    for any non-default claim — empty `sources` makes the path count as
    unverified.

    Strict schema: unknown keys raise. Negative counts / out-of-range floats
    raise.
    """

    # ---- Co-authorship (differentiated by team size) ---------------------
    small_team_coauthor_5y: int | None = Field(
        default=None, ge=0,
        description="Distinct papers in last 5y where both names appear, ≤10 total authors",
    )
    big_collab_papers_5y: int | None = Field(
        default=None, ge=0,
        description="Distinct papers in last 5y where both names appear, >10 authors "
                    "(alphabetical author list bulk; weak signal)",
    )

    # ---- Subgroup / analysis-level (high-strength big-collab evidence) ---
    same_working_group: bool = False
    analysis_contact_overlap: bool = False

    # ---- Genealogy --------------------------------------------------------
    genealogy_relation: GenealogyRelation | None = None

    # ---- Generic shared-collab overlap window ----------------------------
    collaboration_overlap_years: float | None = Field(default=None, ge=0.0)

    # ---- Editorial / committee co-membership -----------------------------
    committee_co_member: bool = False
    same_period: bool = False

    # ---- Provenance (required for non-default claims) --------------------
    sources: list[str] = Field(default_factory=list)
    note: str | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------

class Paper(BaseModel):
    title: str = ""
    journal: str = ""
    journal_tier: int | str
    author_position: int = Field(ge=1)
    year: int | None = None
    doi: str | None = None

    # Maturity at application time. Default 'published' matches the typical
    # CV listing; use lower-weight values honestly when the user says
    # "submitted in October" or "still drafting".
    status: PaperStatus = "published"

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

class Experience(BaseModel):
    lab_pi_name: str
    lab_tier: LabTier
    duration_months: int = Field(ge=0)
    output_type: OutputType

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class CurrentAdvisor(BaseModel):
    id: str
    name: str
    institution: str

    model_config = ConfigDict(extra="forbid")


class StudentProfile(BaseModel):
    name: str | None = None
    field: str
    undergrad_institution: str
    master_institution: str | None = None
    gpa_raw: float | str
    gpa_scale: GPAScale = "4.0"
    research_direction: str
    current_advisors: list[CurrentAdvisor] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Candidate advisor (always agent-generated via web research)
# ---------------------------------------------------------------------------

class CandidateAdvisor(BaseModel):
    id: str
    name: str
    institution: str
    school_tier: SchoolTier
    field: str
    research_areas: list[str] = Field(default_factory=list)
    recent_papers: list[Paper] = Field(default_factory=list)

    # Connection edges per student-advisor id. Each value is a PathEdge.
    paths_to_advisors: dict[str, PathEdge] = Field(default_factory=dict)

    # Field-level network strength (0–1). Three-state semantics per code
    # review: `None` means "not checked yet" (distinct from a verified low
    # score). Set to a numeric value only after web verification, with a
    # matching `evidence[<field>]` entry containing source URLs.
    normalized_collab_top20pct: float | None = Field(default=None, ge=0.0, le=1.0)
    collab_with_nas: bool | None = None
    grad_placement_quality: float | None = Field(default=None, ge=0.0, le=1.0)

    pi_signal: PISignal = "missing"
    recent_phd_count: int | None = Field(default=None, ge=0)

    # Provenance registry — keys are field names, values are EvidenceEntry.
    # Use to attach sources to e.g. normalized_collab_top20pct, collab_with_nas,
    # grad_placement_quality, pi_signal.
    evidence: dict[str, EvidenceEntry] = Field(default_factory=dict)

    # Sources searched, including ones that returned nothing — auditability.
    searched_sources: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Match result
# ---------------------------------------------------------------------------

class MatchResult(BaseModel):
    candidate: CandidateAdvisor
    c_score: float
    p_score: float
    e_score: float
    g_score: float
    match_score: float

    # Renamed from admit_likelihood — NOT a probability. 4.0-scale relative-fit
    # index combining match_score with school competitiveness and PI recruiting
    # signal. See docs/scoring.md.
    application_strength: float
    confidence_band: float
    strength_label: StrengthLabel

    explanation: str | None = None
    unverified_signals: int = Field(default=0, ge=0)

    # Risk-adjusted strength used as the primary sort key — penalizes wide
    # confidence bands so a candidate with sparse evidence can't outrank a
    # better-sourced peer simply by claiming a higher strength.
    risk_adjusted_strength: float = 0.0

    model_config = ConfigDict(extra="forbid")
