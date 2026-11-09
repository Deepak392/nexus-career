import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../services/auth";
import {
  downloadReferralResume,
  getMyReferralRequests,
  performReferralAction,
  type ReferralRequest,
  type ReferralStatus,
} from "../services/alumni";
import "./AlumniPages.css";

const filters: Array<"ALL" | ReferralStatus> = ["ALL", "PENDING", "ACCEPTED", "REFERRED", "DECLINED"];

function label(value: string) {
  return value.toLowerCase().replaceAll("_", " ");
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AlumniReferralsPage() {
  const [requests, setRequests] = useState<ReferralRequest[]>([]);
  const [filter, setFilter] = useState<"ALL" | ReferralStatus>("ALL");
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [infoOpen, setInfoOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);
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

  async function runAction(
    item: ReferralRequest,
    action: "accept" | "decline" | "request-information" | "mark-referred"
  ) {
    const note = notes[item.id] ?? "";
    if (action === "request-information" && note.trim().length < 10) {
      setError("Please explain what additional information you need (at least 10 characters).");
      return;
    }
    setBusy(item.id);
    setError("");
    setNotice("");
    try {
      await performReferralAction(item.id, action, note.trim());
      setNotice(action === "accept" ? "Referral request accepted."
        : action === "decline" ? "Referral request declined."
          : action === "mark-referred" ? "Referral marked as completed."
            : "Request for additional information sent to the student.");
      setInfoOpen(null);
      setNotes((current) => ({ ...current, [item.id]: "" }));
      await loadRequests();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setBusy(null);
    }
  }

  async function handleDownload(item: ReferralRequest) {
    setDownloading(item.id);
    setError("");
    try {
      const blob = await downloadReferralResume(item.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `referral-${item.student_username}-resume.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setDownloading(null);
    }
  }

  const visibleRequests = requests.filter((item) => filter === "ALL" || item.status === filter);

  return (
    <main className="alumni-page">
      <header className="alumni-page-header">
        <div><p className="alumni-eyebrow">ALUMNI PORTAL</p><h1>Referral requests</h1><p className="alumni-subtitle">Review student requests and keep each referral up to date.</p></div>
        <Link to="/alumni" className="alumni-secondary-button">Back to dashboard</Link>
      </header>

      {error && <div className="alumni-alert error" role="alert">{error}</div>}
      {notice && <div className="alumni-alert success" role="status">{notice}</div>}

      <div className="alumni-filter-row" aria-label="Filter referral requests">
        {filters.map((value) => (
          <button key={value} type="button" className={filter === value ? "alumni-filter active" : "alumni-filter"} onClick={() => setFilter(value)}>
            {value === "ALL" ? "All requests" : label(value)}
            <span>{value === "ALL" ? requests.length : requests.filter((item) => item.status === value).length}</span>
          </button>
        ))}
        <button type="button" className="alumni-filter-refresh" onClick={() => void loadRequests()}>Refresh</button>
      </div>

      {loading ? (
        <div className="alumni-state">Loading referral requests…</div>
      ) : visibleRequests.length === 0 ? (
        <div className="alumni-empty-panel"><h2>No {filter === "ALL" ? "" : label(filter) + " "}requests</h2><p>Referral requests from students will appear here.</p></div>
      ) : (
        <div className="alumni-request-list">
          {visibleRequests.map((item) => (
            <article className="alumni-request-card" key={item.id}>
              <header className="alumni-request-header">
                <div><p className="alumni-eyebrow">REQUEST #{item.id}</p><h2>{item.student_name}</h2><p>{[item.student_department, item.student_graduation_year ? `Class of ${item.student_graduation_year}` : ""].filter(Boolean).join(" · ") || item.student_username}</p></div>
                <span className={`alumni-status ${item.status.toLowerCase()}`}>{label(item.status)}</span>
              </header>
              <div className="alumni-request-meta">
                <div><span>Received</span><strong>{formatDate(item.created_at)}</strong></div>
                <div><span>Target opportunity</span><a href={item.opportunity_url} target="_blank" rel="noreferrer">Open link ↗</a></div>
                <div><span>Resume</span><button className="alumni-inline-action" type="button" disabled={!item.has_resume || downloading === item.id} onClick={() => void handleDownload(item)}>{downloading === item.id ? "Downloading…" : "Download PDF ↓"}</button></div>
              </div>
              <section className="alumni-request-note"><span>Student's note</span><p>{item.note}</p></section>

              {item.status === "PENDING" && (
                <div className="alumni-request-actions">
                  <button className="alumni-primary-button" type="button" disabled={busy === item.id} onClick={() => void runAction(item, "accept")}>{busy === item.id ? "Saving…" : "Accept request"}</button>
                  <button className="alumni-secondary-button" type="button" disabled={busy === item.id} onClick={() => void runAction(item, "decline")}>Decline</button>
                  <button className="alumni-link-button" type="button" onClick={() => setInfoOpen(infoOpen === item.id ? null : item.id)}>Request more information</button>
                  {infoOpen === item.id && (
                    <div className="alumni-inline-composer">
                      <label htmlFor={`info-${item.id}`}>What would you like the student to clarify?</label>
                      <textarea id={`info-${item.id}`} rows={3} value={notes[item.id] ?? ""} onChange={(event) => setNotes({ ...notes, [item.id]: event.target.value })} />
                      <button className="alumni-primary-button" type="button" disabled={busy === item.id} onClick={() => void runAction(item, "request-information")}>Send request</button>
                    </div>
                  )}
                </div>
              )}
              {item.status === "ACCEPTED" && (
                <div className="alumni-request-actions">
                  <button className="alumni-primary-button" type="button" disabled={busy === item.id} onClick={() => void runAction(item, "mark-referred")}>{busy === item.id ? "Saving…" : "Mark as referred"}</button>
                  <span className="alumni-muted">Use this after you have submitted the referral through your organization.</span>
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
          ))}
        </div>
      )}
    </main>
  );
}
