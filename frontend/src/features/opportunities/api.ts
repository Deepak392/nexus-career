import { opportunities } from "../../mocks/opportunities";
import type { Opportunity, OpportunityQuery, PaginatedResponse } from "../../types";

const delay = (ms = 600) => new Promise((r) => setTimeout(r, ms));
const published = () => opportunities.filter((o) => o.status === "PUBLISHED");

export const typeOptions = [...new Set(published().map((o) => o.type))];
export const locationOptions = [...new Set(published().map((o) => o.location))];
export const modeOptions = [...new Set(published().map((o) => o.mode))];
export const sourceOptions = [...new Set(published().map((o) => o.source))];

export async function getOpportunities(
  q: OpportunityQuery
): Promise<PaginatedResponse<Opportunity>> {
  await delay();
  let list = published();

  if (q.search) {
    const s = q.search.toLowerCase();
    list = list.filter(
      (o) =>
        o.title.toLowerCase().includes(s) ||
        o.company.toLowerCase().includes(s) ||
        o.skills.some((k) => k.toLowerCase().includes(s))
    );
  }
  if (q.type) list = list.filter((o) => o.type === q.type);
  if (q.location) list = list.filter((o) => o.location === q.location);
  if (q.mode) list = list.filter((o) => o.mode === q.mode);
  if (q.source) list = list.filter((o) => o.source === q.source);

  if (q.sort === "deadline") list.sort((a, b) => a.deadline.localeCompare(b.deadline));
  else if (q.sort === "title") list.sort((a, b) => a.title.localeCompare(b.title));
  else list.sort((a, b) => b.postedAt.localeCompare(a.postedAt));

  const page = q.page && q.page > 0 ? q.page : 1;
  const limit = q.limit ?? 9;
  const start = (page - 1) * limit;
  return { items: list.slice(start, start + limit), total: list.length, page, limit };
}

export async function getOpportunityById(id: string): Promise<Opportunity | null> {
  await delay();
  return published().find((o) => o.id === id) ?? null;
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
  const next = ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  return next.includes(id);
}
