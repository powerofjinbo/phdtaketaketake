export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("phdtake_token");
}

export function setToken(token: string) {
  localStorage.setItem("phdtake_token", token);
  window.dispatchEvent(new Event("phdtake-auth"));
}

export function clearToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("phdtake_token");
  window.dispatchEvent(new Event("phdtake-auth"));
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ---------- Types ---------- */

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

export type Provider = "anthropic" | "openai" | "custom";

export interface LlmSettings {
  provider: Provider;
  model: string | null;
  base_url: string | null;
  has_key: boolean;
}

export interface CvParseResponse {
  profile: Partial<StudentProfile>;
  warnings: string[];
}

/** Multipart upload helper (no JSON content-type; browser sets the boundary). */
export async function apiUpload<T = unknown>(
  path: string,
  formData: FormData
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export type RunStatus = "queued" | "researching" | "scoring" | "done" | "error";

export interface RunSummary {
  id: string;
  status: RunStatus;
  created_at: string;
  target: string;
  progress_note: string | null;
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

export interface RunDetail {
  id: string;
  status: RunStatus;
  progress_note: string | null;
  results: MatchResult[] | null;
  portfolio_summary: string | null;
  error: string | null;
}
