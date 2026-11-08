import type { Opportunity, OpportunityQuery, PaginatedResponse } from "../../types";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

interface ApiOpportunity {
  id: number;
  title: string;
  description: string;
  company_name: string;
  created_by_username: string;
  opportunity_type: "JOB" | "INTERNSHIP";
  required_skills: string[];
  eligibility_criteria: Record<string, unknown>;
  work_mode: "ONSITE" | "HYBRID" | "REMOTE";
  location: string;
  compensation: string | null;
  application_deadline: string;
  start_date: string | null;
  application_method: "PLATFORM" | "EXTERNAL";
  external_application_url: string;
  status: "PUBLISHED";
  published_at: string | null;
  approved_at: string | null;
  rejection_reason: string;
  created_at: string;
  updated_at: string;
}

interface ApiPage<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const typeOptions = ["Job", "Internship"];
export const modeOptions = ["On-site", "Hybrid", "Remote"];
export const sourceOptions = ["Internal", "External"];

function formatEligibility(criteria: Record<string, unknown>): string {
  const parts: string[] = [];
  const cgpa = criteria.minimum_cgpa;
  if (typeof cgpa === "number") {
    parts.push(`Minimum CGPA: ${cgpa.toFixed(1)}`);
  }

  const graduationYears = criteria.graduation_years;
  if (Array.isArray(graduationYears) && graduationYears.length > 0) {
    parts.push(`Graduation years: ${graduationYears.join(", ")}`);
  }

  const programmes = criteria.degree_programmes;
  if (Array.isArray(programmes) && programmes.length > 0) {
    parts.push(`Programmes: ${programmes.join(", ")}`);
  }

  const departments = criteria.departments;
  if (Array.isArray(departments) && departments.length > 0) {
    parts.push(`Departments: ${departments.join(", ")}`);
  }

  return parts.length > 0
    ? parts.join(" · ")
    : "Eligibility criteria have not been specified.";
}

function mapOpportunity(record: ApiOpportunity): Opportunity {
  const mode = {
    ONSITE: "On-site",
    HYBRID: "Hybrid",
    REMOTE: "Remote",
  }[record.work_mode] as Opportunity["mode"];

  const skills = Array.isArray(record.required_skills)
    ? record.required_skills
    : [];
  const eligibility = formatEligibility(record.eligibility_criteria ?? {});
  const deadline = record.application_deadline;

  return {
    id: String(record.id),
    title: record.title,
    company: record.company_name,
    location: record.location,
    type: record.opportunity_type === "INTERNSHIP" ? "Internship" : "Job",
    mode,
    compensation: record.compensation ?? "Not specified",
    skills,
    eligibility,
    postedBy: "Recruiter",
    status: "PUBLISHED",
    source: record.application_method === "EXTERNAL" ? "External" : "Internal",
    applicationMethod:
      record.application_method === "EXTERNAL" ? "External link" : "Apply on portal",
    deadline,
    postedAt: record.published_at ?? record.created_at,
    description: record.description,
    requirements: [
      ...(skills.length > 0 ? [`Required skills: ${skills.join(", ")}`] : []),
      `Eligibility: ${eligibility}`,
      ...(record.start_date ? [`Expected start date: ${record.start_date}`] : []),
    ],
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new Error("Cannot connect to the Nexus Career backend.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : "Failed to load opportunities.";
    throw new Error(detail);
  }
  return data as T;
}

function buildQuery(query: OpportunityQuery): URLSearchParams {
  const params = new URLSearchParams();
  params.set("page", String(query.page && query.page > 0 ? query.page : 1));
  params.set("page_size", String(query.limit ?? 9));

  if (query.search?.trim()) {
    params.set("search", query.search.trim());
  }
  if (query.type) {
    params.set("opportunity_type", query.type === "Internship" ? "INTERNSHIP" : "JOB");
  }
  if (query.mode) {
    params.set(
      "work_mode",
      query.mode === "On-site" ? "ONSITE" : query.mode.toUpperCase()
    );
  }
  if (query.location?.trim()) {
    params.set("location", query.location.trim());
  }
  if (query.source) {
    params.set("application_method", query.source === "External" ? "EXTERNAL" : "PLATFORM");
  }
  params.set(
    "ordering",
    query.sort === "deadline"
      ? "deadline"
      : query.sort === "title"
        ? "title"
        : "newest"
  );
  return params;
}

export async function getOpportunities(
  query: OpportunityQuery
): Promise<PaginatedResponse<Opportunity>> {
  const params = buildQuery(query);
  const page = await fetchJson<ApiPage<ApiOpportunity>>(
    `${API_BASE_URL}/opportunities/?${params.toString()}`
  );

  return {
    items: page.results.map(mapOpportunity),
    total: page.count,
    page: query.page && query.page > 0 ? query.page : 1,
    limit: query.limit ?? 9,
  };
}

export async function getOpportunityById(id: string): Promise<Opportunity | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/opportunities/${encodeURIComponent(id)}/`, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new Error("Cannot connect to the Nexus Career backend.");
  }

  if (response.status === 404) {
    return null;
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error("Failed to load this opportunity.");
  }
  return mapOpportunity(data as ApiOpportunity);
}

const SAVED_KEY = "savedOpportunityIds";

export function getSavedIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function toggleSaved(id: string): boolean {
  const ids = getSavedIds();
  const next = ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(next));
  } catch {
    // Storage can be unavailable in private browsing contexts.
  }
  return next.includes(id);
}
