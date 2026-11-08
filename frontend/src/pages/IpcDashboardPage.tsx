import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "../services/auth";
import {
  approveOpportunity,
  getPendingCompanies,
  getPendingOpportunities,
  rejectCompany,
  rejectOpportunity,
  verifyCompany,
  type CompanyProfile,
  type OpportunityRecord,
} from "../services/workflow";
import "./WorkflowPages.css";

export default function IpcDashboardPage() {
  const [companies, setCompanies] = useState<CompanyProfile[]>([]);
  const [opportunities, setOpportunities] = useState<OpportunityRecord[]>([]);
  const [companyReasons, setCompanyReasons] = useState<Record<number, string>>({});
  const [opportunityReasons, setOpportunityReasons] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadQueues = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [pendingCompanies, pendingOpportunities] = await Promise.all([
        getPendingCompanies(),
        getPendingOpportunities(),
      ]);
      setCompanies(pendingCompanies);
      setOpportunities(pendingOpportunities);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadQueues();
  }, [loadQueues]);

  async function performAction(
    key: string,
    action: () => Promise<unknown>,
    message: string
  ) {
    setBusyKey(key);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await loadQueues();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusyKey("");
    }
  }

  if (loading) {
    return <div className="workflow-state">Loading IPC approval queues...</div>;
  }

  return (
    <section className="workflow-page">
      <header className="workflow-header">
        <div>
          <p className="workflow-eyebrow">IPC ADMINISTRATION</p>
          <h1>Approval dashboard</h1>
          <p className="workflow-subtitle">Verify companies and review job or internship submissions.</p>
        </div>
        <button className="workflow-button secondary" onClick={() => void loadQueues()}>Refresh queues</button>
      </header>

      {error && <div className="workflow-alert error" role="alert">{error}</div>}
      {notice && <div className="workflow-alert success" role="status">{notice}</div>}

      <div className="workflow-stat-grid">
        <div className="workflow-stat"><span>Companies awaiting verification</span><strong>{companies.length}</strong></div>
        <div className="workflow-stat"><span>Opportunities awaiting approval</span><strong>{opportunities.length}</strong></div>
      </div>

      <section className="workflow-panel">
        <div className="workflow-panel-heading">
          <div><h2>Company verification</h2><p>Review company details before recruiters can submit opportunities.</p></div>
        </div>
        {companies.length === 0 ? (
          <div className="workflow-empty">No companies are waiting for verification.</div>
        ) : (
          <div className="workflow-list">
            {companies.map((company) => (
              <article className="workflow-list-card" key={company.id}>
                <div className="workflow-list-main">
                  <div className="workflow-list-title"><h3>{company.name}</h3><span className="workflow-status pending">PENDING</span></div>
                  <p>{company.industry} · {company.contact_email} · {company.contact_phone || "No phone provided"}</p>
                  {company.website && <a href={company.website} target="_blank" rel="noreferrer">{company.website}</a>}
                  {company.description && <p>{company.description}</p>}
                  <label className="workflow-inline-field">
                    Rejection reason
                    <input
                      value={companyReasons[company.id] ?? ""}
                      onChange={(event) => setCompanyReasons({ ...companyReasons, [company.id]: event.target.value })}
                      placeholder="Explain what needs to be corrected"
                    />
                  </label>
                </div>
                <div className="workflow-actions">
                  <button
                    className="workflow-button"
                    disabled={busyKey !== ""}
                    onClick={() => void performAction(`company-${company.id}`, () => verifyCompany(company.id), `${company.name} verified.`)}
                  >{busyKey === `company-${company.id}` ? "Verifying..." : "Verify company"}</button>
                  <button
                    className="workflow-button danger"
                    disabled={busyKey !== "" || (companyReasons[company.id] ?? "").trim().length < 5}
                    onClick={() => void performAction(`company-reject-${company.id}`, () => rejectCompany(company.id, companyReasons[company.id].trim()), `${company.name} rejected.`)}
                  >Reject</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="workflow-panel">
        <div className="workflow-panel-heading">
          <div><h2>Opportunity approval</h2><p>Only submissions from verified companies can be published.</p></div>
        </div>
        {opportunities.length === 0 ? (
          <div className="workflow-empty">No opportunities are waiting for approval.</div>
        ) : (
          <div className="workflow-list">
            {opportunities.map((item) => (
              <article className="workflow-list-card" key={item.id}>
                <div className="workflow-list-main">
                  <div className="workflow-list-title"><h3>{item.title}</h3><span className="workflow-status pending">PENDING APPROVAL</span></div>
                  <p>{item.company_name} · {item.opportunity_type} · {item.location}</p>
                  <p>{item.description}</p>
                  <p>Deadline: {new Date(item.application_deadline).toLocaleString()}</p>
                  {item.required_skills.length > 0 && <p>Skills: {item.required_skills.join(", ")}</p>}
                  <label className="workflow-inline-field">
                    Rejection reason
                    <input
                      value={opportunityReasons[item.id] ?? ""}
                      onChange={(event) => setOpportunityReasons({ ...opportunityReasons, [item.id]: event.target.value })}
                      placeholder="Explain why this listing is rejected"
                    />
                  </label>
                </div>
                <div className="workflow-actions">
                  <button
                    className="workflow-button"
                    disabled={busyKey !== ""}
                    onClick={() => void performAction(`approve-${item.id}`, () => approveOpportunity(item.id), `${item.title} approved and published.`)}
                  >{busyKey === `approve-${item.id}` ? "Approving..." : "Approve and publish"}</button>
                  <button
                    className="workflow-button danger"
                    disabled={busyKey !== "" || (opportunityReasons[item.id] ?? "").trim().length < 5}
                    onClick={() => void performAction(`reject-${item.id}`, () => rejectOpportunity(item.id, opportunityReasons[item.id].trim()), `${item.title} rejected.`)}
                  >Reject</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
