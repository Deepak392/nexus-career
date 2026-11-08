import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError, getApiErrorMessage } from "../services/auth";
import {
  archiveOpportunity,
  closeOpportunity,
  createOpportunity,
  getCompanyProfile,
  getRecruiterOpportunities,
  saveCompanyProfile,
  submitOpportunity,
  updateOpportunity,
  type CompanyProfile,
  type OpportunityPayload,
  type OpportunityRecord,
} from "../services/workflow";
import "./WorkflowPages.css";

interface CompanyForm {
  name: string;
  website: string;
  industry: string;
  contact_email: string;
  contact_phone: string;
  description: string;
}

interface OpportunityForm {
  title: string;
  description: string;
  opportunity_type: "JOB" | "INTERNSHIP";
  required_skills: string;
  eligibility_criteria: string;
  work_mode: "ONSITE" | "HYBRID" | "REMOTE";
  location: string;
  compensation: string;
  application_deadline: string;
  start_date: string;
  application_method: "PLATFORM" | "EXTERNAL";
  external_application_url: string;
}

const emptyCompany: CompanyForm = {
  name: "",
  website: "",
  industry: "",
  contact_email: "",
  contact_phone: "",
  description: "",
};

function localDateTime(daysFromNow = 14): string {
  const date = new Date(Date.now() + daysFromNow * 86400000);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

function emptyOpportunity(): OpportunityForm {
  return {
    title: "",
    description: "",
    opportunity_type: "INTERNSHIP",
    required_skills: "",
    eligibility_criteria: "{\n  \"minimum_cgpa\": 7.0,\n  \"graduation_years\": [2027, 2028]\n}",
    work_mode: "HYBRID",
    location: "",
    compensation: "",
    application_deadline: localDateTime(),
    start_date: "",
    application_method: "PLATFORM",
    external_application_url: "",
  };
}

function toCompanyForm(company: CompanyProfile): CompanyForm {
  return {
    name: company.name,
    website: company.website,
    industry: company.industry,
    contact_email: company.contact_email,
    contact_phone: company.contact_phone,
    description: company.description,
  };
}

function toOpportunityForm(item: OpportunityRecord): OpportunityForm {
  const deadline = new Date(item.application_deadline);
  const localDeadline = new Date(deadline.getTime() - deadline.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  return {
    title: item.title,
    description: item.description,
    opportunity_type: item.opportunity_type,
    required_skills: item.required_skills.join(", "),
    eligibility_criteria: JSON.stringify(item.eligibility_criteria, null, 2),
    work_mode: item.work_mode,
    location: item.location,
    compensation: item.compensation ?? "",
    application_deadline: localDeadline,
    start_date: item.start_date ?? "",
    application_method: item.application_method,
    external_application_url: item.external_application_url,
  };
}

function toPayload(form: OpportunityForm): OpportunityPayload {
  let parsed: unknown;
  try {
    parsed = JSON.parse(form.eligibility_criteria || "{}");
  } catch {
    throw new Error("Enter valid JSON for eligibility criteria.");
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Eligibility criteria must be a JSON object.");
  }

  return {
    title: form.title.trim(),
    description: form.description.trim(),
    opportunity_type: form.opportunity_type,
    required_skills: form.required_skills.split(",").map((v) => v.trim()).filter(Boolean),
    eligibility_criteria: parsed as Record<string, unknown>,
    work_mode: form.work_mode,
    location: form.location.trim(),
    compensation: form.compensation.trim() || null,
    application_deadline: new Date(form.application_deadline).toISOString(),
    start_date: form.start_date || null,
    application_method: form.application_method,
    external_application_url: form.application_method === "EXTERNAL"
      ? form.external_application_url.trim()
      : "",
  };
}

function statusLabel(value: OpportunityRecord["status"]): string {
  return value.replaceAll("_", " ");
}

export default function RecruiterDashboardPage() {
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [companyForm, setCompanyForm] = useState<CompanyForm>(emptyCompany);
  const [companyFormOpen, setCompanyFormOpen] = useState(false);
  const [opportunities, setOpportunities] = useState<OpportunityRecord[]>([]);
  const [form, setForm] = useState<OpportunityForm>(emptyOpportunity());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const companyVerified = company?.verification_status === "VERIFIED";
  const counts = useMemo(() => ({
    draft: opportunities.filter((item) => item.status === "DRAFT").length,
    pending: opportunities.filter((item) => item.status === "PENDING_APPROVAL").length,
    published: opportunities.filter((item) => item.status === "PUBLISHED").length,
  }), [opportunities]);

  const loadWorkspace = useCallback(async () => {
    try {
      const currentCompany = await getCompanyProfile();
      setCompany(currentCompany);
      setCompanyForm(toCompanyForm(currentCompany));
      setCompanyFormOpen(false);
      setOpportunities(await getRecruiterOpportunities());
      setError("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setCompany(null);
        setOpportunities([]);
        setCompanyFormOpen(true);
        setError("");
      } else {
        setError(getApiErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  async function refreshWorkspace() {
    setLoading(true);
    await loadWorkspace();
  }

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  async function handleCompanySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await saveCompanyProfile(companyForm, Boolean(company));
      setCompany(saved);
      setCompanyForm(toCompanyForm(saved));
      setCompanyFormOpen(false);
      setNotice(company
        ? "Company details updated. IPC verification is required again."
        : "Company profile created and sent for IPC verification.");
      await loadWorkspace();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  function resetOpportunityForm() {
    setEditingId(null);
    setForm(emptyOpportunity());
  }

  function beginEdit(item: OpportunityRecord) {
    setEditingId(item.id);
    setForm(toOpportunityForm(item));
    setError("");
    setNotice("");
    document.getElementById("opportunity-form")?.scrollIntoView({ behavior: "smooth" });
  }

  async function handleOpportunitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = toPayload(form);
      if (editingId === null) {
        await createOpportunity(payload);
        setNotice("Opportunity saved as a draft.");
      } else {
        await updateOpportunity(editingId, payload);
        setNotice("Opportunity updated.");
      }
      resetOpportunityForm();
      await loadWorkspace();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function runAction(
    action: (id: number) => Promise<OpportunityRecord>,
    id: number,
    message: string
  ) {
    setError("");
    setNotice("");
    try {
      await action(id);
      setNotice(message);
      await loadWorkspace();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  }

  if (loading) {
    return <div className="workflow-state">Loading recruiter workspace...</div>;
  }

  return (
    <section className="workflow-page">
      <header className="workflow-header">
        <div>
          <p className="workflow-eyebrow">RECRUITER PORTAL</p>
          <h1>Recruiter dashboard</h1>
          <p className="workflow-subtitle">Manage your company and opportunities.</p>
        </div>
        <button
          className="workflow-button"
          disabled={!company}
          onClick={() => {
            resetOpportunityForm();
            document.getElementById("opportunity-form")?.scrollIntoView({ behavior: "smooth" });
          }}
        >Create opportunity</button>
      </header>

      {error && <div className="workflow-alert error" role="alert">{error}</div>}
      {notice && <div className="workflow-alert success" role="status">{notice}</div>}

      <div className="workflow-stat-grid">
        <div className="workflow-stat"><span>Drafts</span><strong>{counts.draft}</strong></div>
        <div className="workflow-stat"><span>Awaiting approval</span><strong>{counts.pending}</strong></div>
        <div className="workflow-stat"><span>Published</span><strong>{counts.published}</strong></div>
      </div>

      <section className="workflow-panel">
        <div className="workflow-panel-heading">
          <div><h2>Company profile</h2><p>Company details are reviewed by IPC.</p></div>
          {company && <span className={`workflow-status ${company.verification_status.toLowerCase()}`}>{company.verification_status}</span>}
        </div>

        {company && !companyFormOpen ? (
          <div className="workflow-company-summary">
            <div>
              <strong>{company.name}</strong>
              <p>{company.industry} · {company.contact_email}</p>
              {company.website && <a href={company.website} target="_blank" rel="noreferrer">{company.website}</a>}
              {company.verification_rejection_reason && <p className="workflow-rejection">IPC feedback: {company.verification_rejection_reason}</p>}
            </div>
            <button className="workflow-button secondary" onClick={() => setCompanyFormOpen(true)}>Edit company</button>
          </div>
        ) : (
          <form className="workflow-form" onSubmit={handleCompanySubmit}>
            <div className="workflow-form-grid">
              <label>Company name<input required maxLength={200} value={companyForm.name} onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })} /></label>
              <label>Industry<input required maxLength={100} value={companyForm.industry} onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })} /></label>
              <label>Website<input type="url" value={companyForm.website} onChange={(e) => setCompanyForm({ ...companyForm, website: e.target.value })} placeholder="https://example.com" /></label>
              <label>Contact email<input type="email" required value={companyForm.contact_email} onChange={(e) => setCompanyForm({ ...companyForm, contact_email: e.target.value })} /></label>
              <label>Contact phone<input value={companyForm.contact_phone} onChange={(e) => setCompanyForm({ ...companyForm, contact_phone: e.target.value })} /></label>
            </div>
            <label>Description<textarea rows={3} value={companyForm.description} onChange={(e) => setCompanyForm({ ...companyForm, description: e.target.value })} /></label>
            <div className="workflow-actions">
              <button className="workflow-button" type="submit" disabled={saving}>{saving ? "Saving..." : company ? "Save company changes" : "Create company profile"}</button>
              {company && <button type="button" className="workflow-button secondary" onClick={() => setCompanyFormOpen(false)}>Cancel</button>}
            </div>
          </form>
        )}
        {company && !companyVerified && (
          <p className="workflow-hint">You can prepare draft opportunities, but cannot submit until IPC verifies the company.</p>
        )}
      </section>

      <section className="workflow-panel" id="opportunity-form">
        <div className="workflow-panel-heading">
          <div><h2>{editingId === null ? "Create an opportunity" : "Edit opportunity"}</h2><p>New opportunities are saved as drafts.</p></div>
        </div>
        <form className="workflow-form" onSubmit={handleOpportunitySubmit}>
          <div className="workflow-form-grid">
            <label>Title<input required maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            <label>Type<select value={form.opportunity_type} onChange={(e) => setForm({ ...form, opportunity_type: e.target.value as OpportunityForm["opportunity_type"] })}><option value="JOB">Job</option><option value="INTERNSHIP">Internship</option></select></label>
            <label>Work mode<select value={form.work_mode} onChange={(e) => setForm({ ...form, work_mode: e.target.value as OpportunityForm["work_mode"] })}><option value="ONSITE">On-site</option><option value="HYBRID">Hybrid</option><option value="REMOTE">Remote</option></select></label>
            <label>Location<input required value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label>
            <label>Compensation / stipend<input type="number" min="0" step="0.01" value={form.compensation} onChange={(e) => setForm({ ...form, compensation: e.target.value })} /></label>
            <label>Application deadline<input required type="datetime-local" value={form.application_deadline} onChange={(e) => setForm({ ...form, application_deadline: e.target.value })} /></label>
            <label>Start date<input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
            <label>Application method<select value={form.application_method} onChange={(e) => setForm({ ...form, application_method: e.target.value as OpportunityForm["application_method"] })}><option value="PLATFORM">Apply on Nexus Career</option><option value="EXTERNAL">External link</option></select></label>
          </div>
          <label>Description<textarea required minLength={20} rows={5} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <label>Required skills (comma-separated)<input value={form.required_skills} onChange={(e) => setForm({ ...form, required_skills: e.target.value })} placeholder="Python, Django, PostgreSQL" /></label>
          <label>Eligibility criteria (JSON)<textarea rows={5} spellCheck={false} value={form.eligibility_criteria} onChange={(e) => setForm({ ...form, eligibility_criteria: e.target.value })} /></label>
          {form.application_method === "EXTERNAL" && <label>External application URL<input required type="url" value={form.external_application_url} onChange={(e) => setForm({ ...form, external_application_url: e.target.value })} placeholder="https://jobs.example.com/apply" /></label>}
          <div className="workflow-actions">
            <button className="workflow-button" type="submit" disabled={saving || !company}>{saving ? "Saving..." : editingId === null ? "Save as draft" : "Update draft"}</button>
            {editingId !== null && <button type="button" className="workflow-button secondary" onClick={resetOpportunityForm}>Cancel edit</button>}
          </div>
        </form>
      </section>

      <section className="workflow-panel">
        <div className="workflow-panel-heading">
          <div><h2>Your opportunities</h2><p>Only records associated with your company are shown.</p></div>
          <button className="workflow-button secondary" onClick={() => void refreshWorkspace()}>Refresh</button>
        </div>
        {opportunities.length === 0 ? (
          <div className="workflow-empty">No opportunities yet. Create your first draft above.</div>
        ) : (
          <div className="workflow-list">
            {opportunities.map((item) => (
              <article className="workflow-list-card" key={item.id}>
                <div className="workflow-list-main">
                  <div className="workflow-list-title">
                    <h3>{item.title}</h3>
                    <span className={`workflow-status ${item.status.toLowerCase()}`}>{statusLabel(item.status)}</span>
                  </div>
                  <p>{item.opportunity_type} · {item.location} · Deadline {new Date(item.application_deadline).toLocaleString()}</p>
                  {item.rejection_reason && <p className="workflow-rejection">IPC feedback: {item.rejection_reason}</p>}
                </div>
                <div className="workflow-actions wrap">
                  {(item.status === "DRAFT" || item.status === "REJECTED") && (
                    <>
                      <button className="workflow-button secondary" onClick={() => beginEdit(item)}>Edit</button>
                      <button className="workflow-button" disabled={!companyVerified} onClick={() => void runAction(submitOpportunity, item.id, "Opportunity submitted for IPC approval.")}>Submit for approval</button>
                    </>
                  )}
                  {item.status === "PUBLISHED" && <button className="workflow-button secondary" onClick={() => void runAction(closeOpportunity, item.id, "Opportunity closed.")}>Close</button>}
                  {["DRAFT", "REJECTED", "CLOSED"].includes(item.status) && <button className="workflow-button danger" onClick={() => void runAction(archiveOpportunity, item.id, "Opportunity archived.")}>Archive</button>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
