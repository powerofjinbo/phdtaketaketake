"""Pydantic models for student profiles, candidate advisors, and match results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Evidence — provenance for any claim the agent makes
# ---------------------------------------------------------------------------

class EvidenceEntry(BaseModel):
    """Sources backing a specific signal value, with audit trail.

    Used in:
      - CandidateAdvisor.evidence (keyed by field name)
      - PathEdge / paths_to_advisors[adv_id] (under "sources" key)

    Empty `sources` + non-default value = signal is asserted without proof.
    The matcher's confidence band widens when this happens.
    """

    sources: list[str] = Field(default_factory=list)
    note: str | None = None
    last_checked: str | None = None

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------

# Status weights are applied multiplicatively to paper_score in scoring/pub.py.
PAPER_STATUS_VALUES = (
    "published",
    "accepted",
    "in_press",
    "submitted",
    "preprint",
    "in_prep",
)


class Paper(BaseModel):
    title: str = ""
    journal: str = ""
    journal_tier: int | str
    author_position: int
    year: int | None = None
    doi: str | None = None

    # Maturity at application time — affects pub_score weight.
    # Default is "published" (matches user CV expectation).
    status: str = "published"


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

class Experience(BaseModel):
    lab_pi_name: str
    lab_tier: str
    duration_months: int
    output_type: str


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class CurrentAdvisor(BaseModel):
    id: str
    name: str
    institution: str


class StudentProfile(BaseModel):
    name: str | None = None
    field: str
    undergrad_institution: str
    master_institution: str | None = None
    gpa_raw: float | str
    gpa_scale: str = "4.0"
    research_direction: str
    current_advisors: list[CurrentAdvisor] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Candidate advisor (always agent-generated via web research)
# ---------------------------------------------------------------------------

class CandidateAdvisor(BaseModel):
    id: str
    name: str
    institution: str
    school_tier: str               # 'top_10' | 'top_11_30' | 'top_31_60' | 'top_60_plus'
    field: str
    research_areas: list[str] = Field(default_factory=list)
    recent_papers: list[Paper] = Field(default_factory=list)

    # ---- Connection edges per student advisor id -------------------------
    # Each value is a dict that may contain any subset of:
    #   small_team_coauthor_5y    int   (papers with ≤10 authors)
    #   big_collab_papers_5y      int   (papers with >10 authors — alphabetical
    #                                    author list, weak signal)
    #   same_working_group        bool  (verified subgroup / convener overlap)
    #   analysis_contact_overlap  bool  (shared analysis-contact role on a paper)
    #   genealogy_relation        str   ('same_advisor' | 'uncle_nephew' | 'two_hop')
    #   collaboration_overlap_years  float
    #   committee_co_member       bool, same_period: bool
    #   sources                   list[str]  URLs backing the edges above
    #   note                      str
    paths_to_advisors: dict[str, dict] = Field(default_factory=dict)

    # ---- Field-level network strength (0–1) ------------------------------
    normalized_collab_top20pct: float = 0.0
    collab_with_nas: bool = False
    grad_placement_quality: float = 0.0

    # ---- Recruiting signal ------------------------------------------------
    pi_signal: str = "missing"
    recent_phd_count: int | None = None

    # ---- Provenance registry ---------------------------------------------
    # Keys are field names; values are EvidenceEntry. Use to attach sources
    # to e.g. normalized_collab_top20pct, collab_with_nas, pi_signal.
    evidence: dict[str, EvidenceEntry] = Field(default_factory=dict)

    # Sources the agent searched, including ones that returned nothing —
    # auditability for "did the agent actually look?"
    searched_sources: list[str] = Field(default_factory=list)


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

    # Renamed from admit_likelihood — this is NOT a probability. It's a
    # relative-fit index combining match_score with school competitiveness
    # and PI recruiting signal. See docs/scoring.md.
    application_strength: float
    confidence_band: float
    strength_label: str            # 'Far Reach' | 'Reach' | 'Target' | 'Match' | 'Safe'

    explanation: str | None = None
    unverified_signals: int = 0    # for transparency in result presentation
