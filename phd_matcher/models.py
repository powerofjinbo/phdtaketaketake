"""Pydantic models for student profiles, candidate advisors, and match results."""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field


class Paper(BaseModel):
    title: str = ""
    journal: str = ""
    journal_tier: Union[int, str]   # 1-5, or 'S' for cross-disciplinary, 0 for retracted
    author_position: int            # 1-indexed; for big collab papers, real position
    year: Optional[int] = None
    doi: Optional[str] = None


class Experience(BaseModel):
    lab_pi_name: str
    lab_tier: str                    # 'world_class' | 'top_us' | 'strong_us_or_top_cn' | 'good_us_or_985' | '211_or_overseas' | 'other'
    duration_months: int
    output_type: str                 # 'paper' | 'conference_oral' | 'conference_poster' | 'honors_thesis' | 'participation_only'


class CurrentAdvisor(BaseModel):
    id: str
    name: str
    institution: str


class StudentProfile(BaseModel):
    name: Optional[str] = None
    field: str                        # 'physics' | 'mse' | ...
    undergrad_institution: str
    master_institution: Optional[str] = None
    gpa_raw: Union[float, str]
    gpa_scale: str = "4.0"            # '4.0' | '4.3' | '4.5' | '100' | 'uk'
    research_direction: str
    current_advisors: list[CurrentAdvisor] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)


class CandidateAdvisor(BaseModel):
    id: str
    name: str
    institution: str
    school_tier: str                  # 'top_10' | 'top_11_30' | 'top_31_60' | 'top_60_plus'
    field: str
    research_areas: list[str] = Field(default_factory=list)
    recent_papers: list[Paper] = Field(default_factory=list)

    # Connection edges to specific student advisors (by advisor id)
    paths_to_advisors: dict[str, dict] = Field(default_factory=dict)

    # Field-level network strength (0-1)
    normalized_collab_top20pct: float = 0.0
    collab_with_nas: bool = False
    grad_placement_quality: float = 0.0

    # Recruiting signal
    pi_signal: str = "missing"        # 'strong' | 'normal' | 'shrinking' | 'missing' | 'not_recruiting'
    recent_phd_count: Optional[int] = None


class MatchResult(BaseModel):
    candidate: CandidateAdvisor
    c_score: float
    p_score: float
    e_score: float
    g_score: float
    match_score: float
    admit_likelihood: float
    confidence_band: float
    likelihood_label: str             # 'Far Reach' | 'Reach' | 'Target' | 'Match' | 'Safe'
    explanation: Optional[str] = None
