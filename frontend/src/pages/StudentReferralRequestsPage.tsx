import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../services/auth";
import {
  getMyReferralRequests,
  performReferralAction,
  type ReferralRequest,
} from "../services/alumni";
import "./AlumniPages.css";

function label(value: string) {
  return value.toLowerCase().replaceAll("_", " ");
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function StudentReferralRequestsPage() {
  const [requests, setRequests] = useState<ReferralRequest[]>([]);
  const [responses, setResponses] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRequests = useCallback(async () => {
    try {
      setRequests(await getMyReferralRequests());
      setError("");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void loadRequests();
    });
    return () => { active = false; };
  }, [loadRequests]);

  async function respond(item: ReferralRequest) {
    const note = (responses[item.id] ?? "").trim();
    if (note.length < 10) {
      setError("Please provide at least 10 characters in your response.");
      return;
    }
    setBusy(item.id);
    setError("");
    setNotice("");
    try {
      await performReferralAction(item.id, "respond", note);
      setResponses((current) => ({ ...current, [item.id]: "" }));
      setNotice("Your additional information has been sent to the alumnus.");
      await loadRequests();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="alumni-page">
      <header className="alumni-page-header">
        <div><p className="alumni-eyebrow">STUDENT PORTAL</p><h1>My referral requests</h1><p className="alumni-subtitle">Track each request and respond when an alumnus asks for more information.</p></div>
        <Link className="alumni-primary-button" to="/alumni/network">Find alumni</Link>
      </header>

      {error && <div className="alumni-alert error" role="alert">{error}</div>}
      {notice && <div className="alumni-alert success" role="status">{notice}</div>}

      {loading ? (
        <div className="alumni-state">Loading your referral requests…</div>
      ) : requests.length === 0 ? (
        <div className="alumni-empty-panel"><h2>You have not sent any referral requests</h2><p>Search the verified Alumni Network to find graduates who are open to referrals.</p><Link className="alumni-primary-button" to="/alumni/network">Explore Alumni Network</Link></div>
      ) : (
        <div className="alumni-request-list">
          {requests.map((item) => {
            const latestEvent = item.history[item.history.length - 1];
            const needsResponse = item.status === "PENDING" && latestEvent?.event === "INFORMATION_REQUESTED";
            return (
              <article className="alumni-request-card" key={item.id}>
                <header className="alumni-request-header">
                  <div><p className="alumni-eyebrow">REQUEST #{item.id}</p><h2>{item.alumni_name}</h2><p>{[item.alumni_designation, item.alumni_company].filter(Boolean).join(" · ") || "Alumni"}</p></div>
                  <span className={`alumni-status ${item.status.toLowerCase()}`}>{label(item.status)}</span>
                </header>
                <div className="alumni-request-meta">
                  <div><span>Submitted</span><strong>{formatDate(item.created_at)}</strong></div>
                  <div><span>Opportunity</span><a href={item.opportunity_url} target="_blank" rel="noreferrer">Open target link ↗</a></div>
                </div>
                <section className="alumni-request-note"><span>Your message</span><p>{item.note}</p></section>
                {needsResponse && (
                  <div className="alumni-inline-composer">
                    <h3>The alumnus requested more information</h3>
                    <p>{latestEvent.note}</p>
                    <label htmlFor={`response-${item.id}`}>Your response</label>
                    <textarea id={`response-${item.id}`} rows={3} minLength={10} maxLength={1000} value={responses[item.id] ?? ""} onChange={(event) => setResponses({ ...responses, [item.id]: event.target.value })} placeholder="Provide the additional information requested." />
                    <button className="alumni-primary-button" type="button" disabled={busy === item.id} onClick={() => void respond(item)}>{busy === item.id ? "Sending…" : "Send response"}</button>
                  </div>
                )}
                <section className="alumni-history">
                  <h3>Request history</h3>
                  <ol>
                    {item.history.map((entry) => (
                      <li key={entry.id}>
                        <span className="alumni-history-marker" />
                        <div><strong>{label(entry.event)}</strong><small>{formatDate(entry.created_at)} · {entry.changed_by_username}</small>{entry.note && <p>{entry.note}</p>}</div>
                      </li>
                    ))}
                  </ol>
                </section>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}
