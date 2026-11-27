import { ApiError, authenticatedRequest } from "./auth";

export interface StudentProfile {
  id: number;
  student_id: string | null;
  department: string;
  degree_programme: string;
  graduation_year: number;
  cgpa: string | null;
  skills: string[];
  areas_of_interest: string[];
  experience: string;
  preferred_roles: string[];
  preferred_locations: string[];
  work_mode: string;
  has_resume: boolean;
  created_at: string;
  updated_at: string;
}
export interface EligibilityCheck {
  key: string;
  label: string;
  status: "MET" | "NOT_MET" | "MISSING";
  expected: string;
  actual: string | null;
  reason: string;
}
export interface EligibilityResult {
  status: "ELIGIBLE" | "INELIGIBLE" | "INCOMPLETE_PROFILE";
  eligible: boolean | null;
  checks: EligibilityCheck[];
  reasons: string[];
  missing_fields: string[];
  has_resume: boolean;
  resume_required: boolean;
  application_method: "PLATFORM" | "EXTERNAL";
  external_application_url: string;
  ready_to_apply: boolean;
  resume_message: string;
  already_applied: boolean;
}
export interface ApplicationStatusHistory {
  status: string;
  note: string;
  changed_by_username: string;
  created_at: string;
}
export interface StudentApplication {
  id: number;
  opportunity_id: number;
  opportunity_title: string;
  company_name: string;
  opportunity_type: "JOB" | "INTERNSHIP";
  status: string;
  eligibility_snapshot: Pick<EligibilityResult, "status" | "eligible" | "checks" | "reasons" | "missing_fields">;
  submitted_at: string;
  updated_at: string;
  status_history: ApplicationStatusHistory[];
}
export interface InAppNotification {
  id: number;
  notification_type: "APPLICATION_SUBMITTED" | string;
  title: string;
  message: string;
  application_id: number | null;
  referral_request_id: number | null;
  created_at: string;
  read_at: string | null;
}
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function getStudentProfile(): Promise<StudentProfile> {
  return authenticatedRequest<StudentProfile>("/students/profile/");
}
export async function saveStudentProfile(data: FormData, exists: boolean): Promise<StudentProfile> {
  return authenticatedRequest<StudentProfile>("/students/profile/", {
    method: exists ? "PATCH" : "POST",
    body: data,
  });
}
export async function getEligibility(opportunityId: string): Promise<EligibilityResult> {
  return authenticatedRequest<EligibilityResult>(
    "/opportunities/" + encodeURIComponent(opportunityId) + "/eligibility/",
  );
}
export async function createApplication(opportunityId: string): Promise<StudentApplication> {
  return authenticatedRequest<StudentApplication>("/applications/", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: Number(opportunityId) }),
  });
}
export async function getStudentApplications(): Promise<PaginatedResponse<StudentApplication>> {
  return authenticatedRequest<PaginatedResponse<StudentApplication>>("/applications/");
}
export async function getNotifications(): Promise<PaginatedResponse<InAppNotification>> {
  return authenticatedRequest<PaginatedResponse<InAppNotification>>("/notifications/");
}
export async function markNotificationRead(id: number): Promise<InAppNotification> {
  return authenticatedRequest<InAppNotification>("/notifications/" + id + "/read/", {
    method: "POST",
  });
}
export function isProfileNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
