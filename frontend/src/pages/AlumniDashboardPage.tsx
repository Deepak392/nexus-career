import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../services/auth";
import {
  getAlumniMetrics,
  getAlumniProfile,
  getMyReferralRequests,
  type AlumniMetrics,
  type AlumniProfile,
  type ReferralRequest,
} from "../services/alumni";
import "./AlumniPages.css";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function statusLabel(value: string) {
  return value.toLowerCase().replaceAll("_", " ");
}

export default function AlumniDashboardPage() {
  const [profile, setProfile] = useState<AlumniProfile | null>(null);
  const [metrics, setMetrics] = useState<AlumniMetrics | null>(null);
  const [requests, setRequests] = useState<ReferralRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getAlumniProfile(), getAlumniMetrics(), getMyReferralRequests()])
      .then(([currentProfile, currentMetrics, currentRequests]) => {
        if (!active) return;
        setProfile(currentProfile);
        setMetrics(currentMetrics);
        setRequests(currentRequests);
        setError("");
      })
      .catch((requestError: unknown) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  if (loading) {
    return <main className="alumni-page"><div className="alumni-state">Loading alumni workspace…</div></main>;
  }

  return (
    <main className="alumni-page">
      <header className="alumni-page-header">
        <div>
          <p className="alumni-eyebrow">ALUMNI PORTAL</p>
          <h1>Alumni workspace</h1>
          <p className="alumni-subtitle">Stay connected to your campus community and support the next generation.</p>
        </div>
        <Link className="alumni-primary-button" to="/alumni/referrals">Review referral requests</Link>
      </header>

      {error && <div className="alumni-alert error" role="alert">{error}</div>}

      {profile && (
        <section className="alumni-profile-summary">
          <div className="alumni-profile-monogram">{profile.full_name.slice(0, 1).toUpperCase()}</div>
          <div className="alumni-profile-copy">
            <p className="alumni-eyebrow">PROFILE</p>
            <h2>{profile.full_name}</h2>
            <p>{[profile.designation, profile.current_company].filter(Boolean).join(" · ") || "Add your current role and company"}</p>
          </div>
          <div className="alumni-summary-status">
            <span className={`alumni-status ${profile.verification_status.toLowerCase()}`}>
              {statusLabel(profile.verification_status)}
            </span>
            <Link to="/alumni/profile">Manage profile →</Link>
          </div>
        </section>
      )}

      {profile?.verification_status !== "VERIFIED" && (
        <div className="alumni-alert info" role="status">
          Your alumni profile is {statusLabel(profile?.verification_status ?? "PENDING")}. Only verified alumni are visible in the student directory.
        </div>
      )}

      {metrics && (
        <section className="alumni-metric-grid" aria-label="Alumni engagement summary">
          <article className="alumni-metric"><span>Total requests</span><strong>{metrics.total}</strong><small>All referral requests received</small></article>
          <article className="alumni-metric"><span>Pending</span><strong>{metrics.pending}</strong><small>Awaiting your response</small></article>
          <article className="alumni-metric"><span>Accepted</span><strong>{metrics.accepted}</strong><small>Accepted referrals</small></article>
          <article className="alumni-metric"><span>Referred</span><strong>{metrics.referred}</strong><small>Marked as referred</small></article>
          <article className="alumni-metric"><span>Students supported</span><strong>{metrics.student_interactions}</strong><small>Unique students who contacted you</small></article>
        </section>
      )}

      <section className="alumni-workspace-grid">
        <article className="alumni-panel">
          <div className="alumni-panel-heading">
            <div><h2>Referral availability</h2><p>Control whether students can send you new requests.</p></div>
            <span className={`alumni-status ${profile?.is_open_to_referrals ? "available" : "unavailable"}`}>
              {profile?.is_open_to_referrals ? "Available" : "Unavailable"}
            </span>
          </div>
          <p className="alumni-muted">
            {profile?.is_open_to_referrals
              ? "Your verified profile is eligible to appear in the student referral directory."
              : "Students cannot send you new referral requests while availability is off."}
          </p>
          <Link to="/alumni/profile" className="alumni-text-link">Change availability and profile details →</Link>
        </article>

        <article className="alumni-panel">
          <div className="alumni-panel-heading">
            <div><h2>Quick links</h2><p>Manage your Alumni activity.</p></div>
          </div>
          <div className="alumni-quick-links">
            <Link to="/alumni/profile">Professional profile <span>→</span></Link>
            <Link to="/alumni/referrals">Referral request inbox <span>→</span></Link>
            <Link to="/notifications">Notifications <span>→</span></Link>
          </div>
        </article>
      </section>

      <section className="alumni-panel">
        <div className="alumni-panel-heading">
          <div><h2>Recent referral requests</h2><p>Latest activity from students.</p></div>
          <Link to="/alumni/referrals" className="alumni-text-link">View all →</Link>
        </div>
        {requests.length === 0 ? (
          <div className="alumni-empty">No referral requests yet. New requests will appear here.</div>
        ) : (
          <div className="alumni-table-wrap">
            <table className="alumni-table">
              <thead><tr><th>Student</th><th>Opportunity</th><th>Received</th><th>Status</th></tr></thead>
              <tbody>
                {requests.slice(0, 5).map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.student_name}</strong><small>{item.student_department || "Department not provided"}</small></td>
                    <td><a href={item.opportunity_url} target="_blank" rel="noreferrer">View opportunity</a></td>
                    <td>{formatDate(item.created_at)}</td>
                    <td><span className={`alumni-status ${item.status.toLowerCase()}`}>{statusLabel(item.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
