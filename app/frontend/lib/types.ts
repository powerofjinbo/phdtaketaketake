// Domain types shared by the profile form and results rendering.
// These mirror the phd_matcher engine's Pydantic models.

export type GpaScale = "4.0" | "4.3" | "4.5" | "100" | "uk_honours";
export type PaperStatus =
  | "published"
  | "accepted"
  | "submitted"
  | "preprint"
  | "in_prep";
export type OutputType = "paper" | "poster" | "thesis" | "none";

export interface Advisor {
  id: string;
  name: string;
  institution: string;
}

export interface Paper {
  title: string;
  journal: string;
  journal_tier: number;
  author_position: number;
  status: PaperStatus;
  year: number;
}

export interface Experience {
  lab_pi_name: string;
  lab_tier: number;
  duration_months: number;
  output_type: OutputType;
}

export interface StudentProfile {
  name?: string;
  field: string;
  undergrad_institution: string;
  gpa_raw: number;
  gpa_scale: GpaScale;
  research_direction: string;
  current_advisors: Advisor[];
  papers: Paper[];
  experiences: Experience[];
}

export type ApplyBucket =
  | "priority"
  | "target"
  | "reach"
  | "only_if_space"
  | "drop";

export interface MatchResult {
  candidate: {
    name: string;
    institution: string;
    school_tier: number | string;
    research_areas: string[];
  };
  application_strength: number;
  confidence_band: number;
  strength_label: string;
  difficulty_adjusted_strength: number;
  risk_adjusted_strength: number;
  lower_bound: number;
  explanation: string;
  missing_signal_names: string[];
  unsourced_signal_names: string[];
  research_fit_score: number | null;
  research_fit_summary: string | null;
  strategy: {
    apply_bucket: ApplyBucket;
    recommended_action: string;
    outreach_angle?: string;
  } | null;
}
