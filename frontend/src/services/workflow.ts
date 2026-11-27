import { authenticatedRequest } from "./auth";

export interface CompanyProfile {
  id: number;
  name: string;
  website: string;
  industry: string;
  contact_email: string;
  contact_phone: string;
  description: string;
  verification_status: "PENDING" | "VERIFIED" | "REJECTED";
  verification_rejection_reason: string;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityRecord {
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
  status: "DRAFT" | "PENDING_APPROVAL" | "PUBLISHED" | "REJECTED" | "CLOSED" | "ARCHIVED";
  published_at: string | null;
  approved_at: string | null;
  rejection_reason: string;
  created_at: string;
  updated_at: string;
}

export interface OpportunityPayload {
  title: string;
  description: string;
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
}

interface Paginated<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

function extractResults<T>(response: Paginated<T> | T[]): T[] {
  return Array.isArray(response) ? response : response.results;
}

export function getCompanyProfile(): Promise<CompanyProfile> {
  return authenticatedRequest<CompanyProfile>("/recruiters/company/");
}

export function saveCompanyProfile(
  payload: Partial<CompanyProfile>,
  exists: boolean
): Promise<CompanyProfile> {
  return authenticatedRequest<CompanyProfile>("/recruiters/company/", {
    method: exists ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRecruiterOpportunities(): Promise<OpportunityRecord[]> {
  const response = await authenticatedRequest<
    Paginated<OpportunityRecord> | OpportunityRecord[]
  >("/recruiters/opportunities/");
  return extractResults(response);
}

export function createOpportunity(payload: OpportunityPayload): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>("/recruiters/opportunities/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateOpportunity(
  id: number,
  payload: Partial<OpportunityPayload>
): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/recruiters/opportunities/${id}/`,
    { method: "PATCH", body: JSON.stringify(payload) }
  );
}

export function submitOpportunity(id: number): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/recruiters/opportunities/${id}/submit/`,
    { method: "POST" }
  );
}

export function closeOpportunity(id: number): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/recruiters/opportunities/${id}/close/`,
    { method: "POST" }
  );
}

export function archiveOpportunity(id: number): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/recruiters/opportunities/${id}/archive/`,
    { method: "POST" }
  );
}

export async function getPendingCompanies(): Promise<CompanyProfile[]> {
  const response = await authenticatedRequest<
    Paginated<CompanyProfile> | CompanyProfile[]
  >("/ipc/companies/pending/");
  return extractResults(response);
}

export function verifyCompany(id: number): Promise<CompanyProfile> {
  return authenticatedRequest<CompanyProfile>(
    `/ipc/companies/${id}/verify/`,
    { method: "POST" }
  );
}

export function rejectCompany(id: number, reason: string): Promise<CompanyProfile> {
  return authenticatedRequest<CompanyProfile>(
    `/ipc/companies/${id}/reject/`,
    { method: "POST", body: JSON.stringify({ reason }) }
  );
}

export async function getPendingOpportunities(): Promise<OpportunityRecord[]> {
  const response = await authenticatedRequest<
    Paginated<OpportunityRecord> | OpportunityRecord[]
  >("/ipc/opportunities/pending/");
  return extractResults(response);
}

export function approveOpportunity(id: number): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/ipc/opportunities/${id}/approve/`,
    { method: "POST" }
  );
}

export function rejectOpportunity(
  id: number,
  reason: string
): Promise<OpportunityRecord> {
  return authenticatedRequest<OpportunityRecord>(
    `/ipc/opportunities/${id}/reject/`,
    { method: "POST", body: JSON.stringify({ reason }) }
  );
}
