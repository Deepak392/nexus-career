export interface Opportunity {
  id: string;
  title: string;
  company: string;
  location: string;
  type: string;
  mode: "On-site" | "Remote" | "Hybrid";
  compensation: string;
  skills: string[];
  eligibility: string;
  openings: number;
  postedBy: "Recruiter" | "Alumni" | "Placement Cell";
  status: "PUBLISHED" | "PENDING_APPROVAL" | "CLOSED";
  source: "Internal" | "External";
  applicationMethod: "Apply on portal" | "External link";
  eligible?: boolean;
  matchScore?: number;
  deadline: string;
  postedAt: string;
  description: string;
  requirements: string[];
}

export interface OpportunityQuery {
  search?: string;
  type?: string;
  location?: string;
  mode?: string;
  source?: string;
  sort?: "newest" | "deadline" | "title";
  page?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}
