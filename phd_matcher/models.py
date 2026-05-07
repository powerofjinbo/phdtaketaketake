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

EvidenceSourceType = Literal[
    "lab_page",
    "faculty_page",
    "google_scholar",
    "openalex",
    "inspire",
    "pubmed",
    "europe_pmc",
    "semantic_scholar",
    "arxiv",
    "biorxiv",
    "dblp",
    "openreview",
    "csrankings",
    "mathscinet",
    "math_genealogy",
    "us_news",
    "nas",
    "hhmi",
    "nih_reporter",
    "clinicaltrials_gov",
    "genealogy",
    "paper",
    "cv",
    "other",
]

VenueSystem = Literal[
    "journal_first",       # physics, chemistry, MSE, biology, clinical
    "conference_first",    # CS / ML / AI / HCI / systems
    "preprint_first",      # math, theoretical CS
    "trial_first",         # clinical / biomedical RCT-driven
    "mixed",
]

SeniorAuthorPosition = Literal["last", "first", "n/a"]


# ---------------------------------------------------------------------------
# Evidence — provenance for any claim the agent makes
# ---------------------------------------------------------------------------

class EvidenceSource(BaseModel):
    """A single, structured piece of evidence for one or more claims.

    Goes inside `EvidenceEntry.items` (preferred over the legacy bare-URL
    `sources` list). A URL alone doesn't tell the matcher *what* it
    supports; this structure binds a URL to a human-readable claim and
    the field name(s) it backs, so an audit can verify each claim
    individually.
    """

    url: str
    source_type: EvidenceSourceType
    claim: str
    supports_fields: list[str] = Field(default_factory=list)
    quote_or_snippet: str | None = None
    last_checked: str | None = None

    model_config = ConfigDict(extra="forbid")


class EvidenceEntry(BaseModel):
    """Sources backing a signal, with audit trail.

    Two formats:
      - `items` (preferred): list of structured `EvidenceSource` records,
        each binding a URL to a specific claim and supports_fields list.
      - `sources` (legacy): list of bare URLs. Kept for back-compat — only
        accepted in default mode. **Strict mode rejects bare sources** as
        claim-level proof.

    Empty both means the agent didn't verify this claim → matcher counts
    it as unverified.
    """

    items: list[EvidenceSource] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    note: str | None = None
    last_checked: str | None = None

    model_config = ConfigDict(extra="forbid")

    @property
    def has_evidence(self) -> bool:
        """True if there is any evidence at all (items or sources).
        For per-claim auditing use `has_evidence_for(field)`."""
        return bool(self.items or self.sources)

    @property
    def is_empty(self) -> bool:
        return not (self.items or self.sources)

    def has_evidence_for(self, field_name: str, *, strict: bool = False) -> bool:
        """Per-claim evidence check.

        - Returns True if any `EvidenceSource` in `items` lists `field_name`
          in its `supports_fields`.
        - In **default** mode, legacy bare `sources` URLs also count as
          evidence (back-compat), since they pre-date the structured
          `supports_fields` model.
        - In **strict** mode, only structured items count.
        """
        for item in self.items:
            if field_name in item.supports_fields:
                return True
        if not strict and self.sources:
            return True
        return False


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
    items: list[EvidenceSource] = Field(default_factory=list)  # preferred
    sources: list[str] = Field(default_factory=list)            # legacy
    note: str | None = None

    model_config = ConfigDict(extra="forbid")

    @property
    def has_evidence(self) -> bool:
        """True if any sources or items at all (regardless of which fields
        they back). For per-claim audit use `has_evidence_for(field)`."""
        return bool(self.items or self.sources)

    @property
    def has_any_edge(self) -> bool:
        """True if any edge field is at non-default — used by the matcher
        to distinguish 'verified-empty' from 'asserted'."""
        return bool(
            self.small_team_coauthor_5y is not None
            or self.big_collab_papers_5y is not None
            or self.same_working_group
            or self.analysis_contact_overlap
            or self.genealogy_relation is not None
            or self.collaboration_overlap_years is not None
            or self.committee_co_member
        )

    def fields_set(self) -> list[str]:
        """Names of edge sub-fields that are at non-default values. Each
        such field needs evidence (items with matching `supports_fields`)."""
        names: list[str] = []
        if self.small_team_coauthor_5y is not None:
            names.append("small_team_coauthor_5y")
        if self.big_collab_papers_5y is not None:
            names.append("big_collab_papers_5y")
        if self.same_working_group:
            names.append("same_working_group")
        if self.analysis_contact_overlap:
            names.append("analysis_contact_overlap")
        if self.genealogy_relation is not None:
            names.append("genealogy_relation")
        if self.collaboration_overlap_years is not None:
            names.append("collaboration_overlap_years")
        if self.committee_co_member:
            names.append("committee_co_member")
        return names

    def has_evidence_for(self, field_name: str, *, strict: bool = False) -> bool:
        """Per-edge-field evidence check. Same semantics as
        `EvidenceEntry.has_evidence_for`."""
        for item in self.items:
            if field_name in item.supports_fields:
                return True
        if not strict and self.sources:
            return True
        return False


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

# ---------------------------------------------------------------------------
# FieldProfile — per-discipline calibration layer
# ---------------------------------------------------------------------------

class FieldProfile(BaseModel):
    """Per-discipline calibration: publication culture, source priorities,
    advisor-influence rules, ranking sources, caveats. Loaded from
    `data/field_profiles/<id>.yaml`.

    The deterministic scoring engine is field-agnostic; FieldProfile is
    metadata that the agent consults to (a) bucket papers correctly,
    (b) search the right primary databases, and (c) surface field-specific
    caveats in the result presentation.
    """

    id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)

    # Publication culture
    venue_system: VenueSystem
    # Total-author count above which a paper is "big collab" (for
    # bucketing into small_team_coauthor_5y vs big_collab_papers_5y).
    big_collab_threshold: int = Field(default=10, ge=2)
    co_first_supported: bool = False
    senior_author_position: SeniorAuthorPosition = "n/a"

    # Source priorities for the agent's web research (per field)
    primary_databases: list[str] = Field(default_factory=list)
    ranking_source_url_template: str | None = None
    genealogy_resources: list[str] = Field(default_factory=list)
    advisor_influence_signals: list[str] = Field(default_factory=list)

    # Field-specific caveats — surfaced in MatchResult.field_caveats so
    # the agent presents them alongside the ranking.
    caveats: list[str] = Field(default_factory=list)

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

    # ---- Evidence coverage (split into clean categories) ----
    # `unverified_signals` = `missing_signals` + `unsourced_signals` (kept
    # for back-compat). The split distinguishes data-absent from
    # claim-without-proof — different risks.
    unverified_signals: int = Field(default=0, ge=0)
    missing_signals: int = Field(default=0, ge=0)
    unsourced_signals: int = Field(default=0, ge=0)
    total_signals: int = Field(default=0, ge=0)
    missing_signal_names: list[str] = Field(default_factory=list)
    unsourced_signal_names: list[str] = Field(default_factory=list)

    # Risk-adjusted strength used as the primary sort key — penalizes wide
    # confidence bands so a candidate with sparse evidence can't outrank a
    # better-sourced peer simply by claiming a higher strength.
    risk_adjusted_strength: float = 0.0

    # Conservative lower-bound reading: even at the wide edge of uncertainty,
    # the application strength is at least this (within the matcher's band).
    lower_bound: float = 0.0

    # Which FieldProfile (if any) was active for this match — for traceability.
    field_profile_id: str | None = None

    model_config = ConfigDict(extra="forbid")
