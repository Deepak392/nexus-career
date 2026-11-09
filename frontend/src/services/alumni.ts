import {
  authenticatedBlobRequest,
  authenticatedRequest,
} from "./auth";

export type ReferralStatus = "PENDING" | "ACCEPTED" | "REFERRED" | "DECLINED";

export interface AlumniProfile {
  id: number;
  username: string;
  full_name: string;
  email: string;
  department: string;
  degree_programme: string;
  graduation_year: number;
  current_company: string;
  designation: string;
  industry: string;
  is_open_to_referrals: boolean;
  verification_status: "PENDING" | "VERIFIED" | "REJECTED";
  verification_rejection_reason: string;
  verified_at: string | null;
  has_graduation_proof: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlumniSearchResult {
  id: number;
  full_name: string;
  department: string;
  degree_programme: string;
  graduation_year: number;
  current_company: string;
  designation: string;
  industry: string;
  is_open_to_referrals: boolean;
}

export interface ReferralHistoryEvent {
  id: number;
  event: string;
  previous_status: ReferralStatus | "";
  new_status: ReferralStatus;
  changed_by_username: string;
  note: string;
  created_at: string;
}

export interface ReferralRequest {
  id: number;
  student_username: string;
  student_name: string;
  student_department: string;
  student_graduation_year: number | null;
  alumni_name: string;
  alumni_company: string;
  alumni_designation: string;
  opportunity_url: string;
  note: string;
  has_resume: boolean;
  status: ReferralStatus;
  history: ReferralHistoryEvent[];
  created_at: string;
  updated_at: string;
}

export interface AlumniMetrics {
  total: number;
  pending: number;
  accepted: number;
  referred: number;
  declined: number;
  student_interactions: number;
  is_open_to_referrals: boolean;
  verification_status: AlumniProfile["verification_status"];
}

export interface AlumniSearchFilters {
  company?: string;
  designation?: string;
  department?: string;
  available?: boolean;
}

export async function getAlumniProfile(): Promise<AlumniProfile> {
  return authenticatedRequest<AlumniProfile>("/alumni/profile/");
}

export async function updateAlumniProfile(
  data: Partial<Pick<AlumniProfile, "department" | "degree_programme" | "graduation_year" | "current_company" | "designation" | "industry" | "is_open_to_referrals">>
): Promise<AlumniProfile> {
  return authenticatedRequest<AlumniProfile>("/alumni/profile/", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getAlumniMetrics(): Promise<AlumniMetrics> {
  return authenticatedRequest<AlumniMetrics>("/alumni/metrics/");
}

export async function getMyReferralRequests(): Promise<ReferralRequest[]> {
  return authenticatedRequest<ReferralRequest[]>("/alumni/referral-requests/");
}

export async function searchAlumni(
  filters: AlumniSearchFilters = {}
): Promise<{ count: number; results: AlumniSearchResult[] }> {
  const params = new URLSearchParams();
  if (filters.company?.trim()) params.set("company", filters.company.trim());
  if (filters.designation?.trim()) params.set("designation", filters.designation.trim());
  if (filters.department?.trim()) params.set("department", filters.department.trim());
  if (filters.available !== undefined) params.set("available", String(filters.available));
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return authenticatedRequest<{ count: number; results: AlumniSearchResult[] }>(
    `/alumni/search/${suffix}`
  );
}

export async function createReferralRequest(
  alumniProfileId: number,
  opportunityUrl: string,
  resume: File,
  note: string
): Promise<ReferralRequest> {
  const data = new FormData();
  data.set("alumni_profile_id", String(alumniProfileId));
  data.set("opportunity_url", opportunityUrl);
  data.set("resume", resume);
  data.set("note", note);
  return authenticatedRequest<ReferralRequest>("/alumni/referral-requests/", {
    method: "POST",
    body: data,
  });
}

export async function performReferralAction(
  id: number,
  action: "accept" | "decline" | "request-information" | "mark-referred" | "respond",
  note = ""
): Promise<ReferralRequest> {
  return authenticatedRequest<ReferralRequest>(
    `/alumni/referral-requests/${id}/${action}/`,
    {
      method: "POST",
      body: JSON.stringify({ note }),
    }
  );
}

export async function downloadReferralResume(id: number): Promise<Blob> {
  return authenticatedBlobRequest(`/alumni/referral-requests/${id}/resume/`);
}


export async function uploadGraduationProof(file: File): Promise<AlumniProfile> {
  const data = new FormData();
  data.set("graduation_proof", file);
  return authenticatedRequest<AlumniProfile>("/alumni/graduation-proof/", {
    method: "POST",
    body: data,
  });
}

export async function getPendingAlumniVerifications(): Promise<{
  count: number;
  results: AlumniProfile[];
}> {
  return authenticatedRequest<{ count: number; results: AlumniProfile[] }>(
    "/alumni/ipc/pending-verification/"
  );
}

export async function downloadAlumniGraduationProof(id: number): Promise<Blob> {
  return authenticatedBlobRequest(`/alumni/ipc/${id}/proof/`);
}

export async function verifyAlumniProfile(id: number): Promise<AlumniProfile> {
  return authenticatedRequest<AlumniProfile>(`/alumni/ipc/${id}/verify/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function rejectAlumniProfile(id: number, reason: string): Promise<AlumniProfile> {
  return authenticatedRequest<AlumniProfile>(`/alumni/ipc/${id}/reject/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
