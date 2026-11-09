import { useCallback, useEffect, useState, type FormEvent } from "react";

import { getApiErrorMessage } from "../services/auth";
import {
  createReferralRequest,
  searchAlumni,
  type AlumniSearchResult,
} from "../services/alumni";
import "./AlumniPages.css";

interface ReferralForm {
  opportunityUrl: string;
  resume: File | null;
  note: string;
}

const emptyForm: ReferralForm = { opportunityUrl: "", resume: null, note: "" };

export default function AlumniNetworkPage() {
  const [alumni, setAlumni] = useState<AlumniSearchResult[]>([]);
  const [count, setCount] = useState(0);
  const [company, setCompany] = useState("");
  const [designation, setDesignation] = useState("");
  const [department, setDepartment] = useState("");
  const [activeId, setActiveId] = useState<number | null>(null);
  const [form, setForm] = useState<ReferralForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadAlumni = useCallback(async () => {
    setLoading(true);
    try {
      const response = await searchAlumni({
        company,
        designation,
        department,
        available: true,
      });
      setAlumni(response.results);
      setCount(response.count);
      setError("");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [company, designation, department]);

  useEffect(() => { void loadAlumni(); }, [loadAlumni]);

  function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    void loadAlumni();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activeId === null || !form.resume) {
      setError("Attach a PDF resume to submit the referral request.");
      return;
    }
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      await createReferralRequest(
        activeId,
        form.opportunityUrl.trim(),
        form.resume,
        form.note.trim()
      );
      setNotice("Your referral request has been sent to the alumnus.");
      setActiveId(null);
      setForm(emptyForm);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="alumni-page">
      <header className="alumni-page-header">
        <div><p className="alumni-eyebrow">STUDENT PORTAL</p><h1>Alumni network</h1><p className="alumni-subtitle">Find verified alumni who are open to supporting students with referrals.</p></div>
        <span className="alumni-result-count">{count} available alumni</span>
      </header>

      {error && <div className="alumni-alert error" role="alert">{error}</div>}
      {notice && <div className="alumni-alert success" role="status">{notice}</div>}

      <form className="alumni-filter-panel" onSubmit={handleFilter}>
        <label>Company<input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Search company" /></label>
        <label>Designation<input value={designation} onChange={(event) => setDesignation(event.target.value)} placeholder="Search job title" /></label>
        <label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} placeholder="Search department" /></label>
        <button className="alumni-primary-button" type="submit">Search alumni</button>
      </form>

      {loading ? (
        <div className="alumni-state">Searching verified alumni…</div>
      ) : alumni.length === 0 ? (
        <div className="alumni-empty-panel"><h2>No available alumni found</h2><p>Try another company, designation or department.</p></div>
      ) : (
        <div className="alumni-directory-grid">
          {alumni.map((person) => (
            <article className="alumni-directory-card" key={person.id}>
              <div className="alumni-directory-heading">
                <span className="alumni-profile-monogram">{person.full_name.slice(0, 1).toUpperCase()}</span>
                <div><h2>{person.full_name}</h2><p>{[person.designation, person.current_company].filter(Boolean).join(" · ") || "Professional details not provided"}</p></div>
              </div>
              <dl className="alumni-directory-details">
                <div><dt>Department</dt><dd>{person.department}</dd></div>
                <div><dt>Degree / batch</dt><dd>{person.degree_programme} · {person.graduation_year}</dd></div>
                <div><dt>Industry</dt><dd>{person.industry || "Not specified"}</dd></div>
              </dl>
              <div className="alumni-directory-actions">
                <span className="alumni-status available">Open to referrals</span>
                <button className="alumni-primary-button" type="button" onClick={() => { setActiveId(activeId === person.id ? null : person.id); setForm(emptyForm); setError(""); }}>
                  {activeId === person.id ? "Close request" : "Request referral"}
                </button>
              </div>
              {activeId === person.id && (
                <form className="alumni-inline-form" onSubmit={handleSubmit}>
                  <h3>Send a referral request</h3>
                  <label>Target opportunity URL<input type="url" required maxLength={500} value={form.opportunityUrl} onChange={(event) => setForm({ ...form, opportunityUrl: event.target.value })} placeholder="https://careers.company.com/job/123" /></label>
                  <label>Resume (PDF, max 5 MB)<input type="file" accept="application/pdf,.pdf" required onChange={(event) => setForm({ ...form, resume: event.target.files?.[0] ?? null })} /></label>
                  <label>Message to alumnus<textarea required minLength={10} maxLength={2000} rows={4} value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} placeholder="Briefly explain your interest in the opportunity and why you are requesting a referral." /></label>
                  <button className="alumni-primary-button" type="submit" disabled={submitting}>{submitting ? "Sending request…" : "Send referral request"}</button>
                </form>
              )}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
