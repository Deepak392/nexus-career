import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../services/auth";
import { getStudentApplications, type StudentApplication } from "../services/student";
import "./StudentPages.css";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusClass(status: string) {
  return status.toLowerCase().replaceAll("_", "-");
}

export default function ApplicationsPage() {
  const { user } = useAuth();
  const [applications, setApplications] = useState<StudentApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.role !== "STUDENT") {
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    getStudentApplications()
      .then((response) => {
        if (active) setApplications(response.results);
      })
      .catch((requestError: unknown) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [user?.role]);

  if (user?.role !== "STUDENT") {
    return (
      <main className="student-page">
        <h1>My applications</h1>
        <p>Sign in with a student account to track applications.</p>
        <Link to="/login">Sign in</Link>
      </main>
    );
  }

  return (
    <main className="student-page">
      <header className="student-page-header">
        <div>
          <p className="student-eyebrow">STUDENT PORTAL</p>
          <h1>My applications</h1>
          <p className="student-muted">Track opportunities you have applied to and review each submission record.</p>
        </div>
        <Link className="student-secondary-button" to="/opportunities">Find opportunities</Link>
      </header>
      {error && <div className="student-alert error" role="alert">{error}</div>}
      {loading ? (
        <div className="student-panel student-state">Loading your applications…</div>
      ) : applications.length === 0 ? (
        <section className="student-panel student-empty">
          <h2>No applications yet</h2>
          <p>When you apply to an eligible platform opportunity, it will appear here.</p>
          <Link className="student-primary-button" to="/opportunities">Explore opportunities</Link>
        </section>
      ) : (
        <div className="student-application-list">
          {applications.map((application) => (
            <article className="student-panel student-application-card" key={application.id}>
              <div className="student-application-heading">
                <div>
                  <p className="student-eyebrow">{application.opportunity_type}</p>
                  <h2>{application.opportunity_title}</h2>
                  <p className="student-muted">{application.company_name}</p>
                </div>
                <span className={"student-status " + statusClass(application.status)}>
                  {statusLabel(application.status)}
                </span>
              </div>
              <p className="student-muted">Submitted {formatDate(application.submitted_at)}</p>
              <div className="student-history">
                <h3>Status history</h3>
                <ol>
                  {application.status_history.map((entry, index) => (
                    <li key={application.id + "-" + entry.status + "-" + entry.created_at + "-" + index}>
                      <strong>{statusLabel(entry.status)}</strong>
                      <span>{entry.note}</span>
                      <time>{formatDate(entry.created_at)}</time>
                    </li>
                  ))}
                </ol>
              </div>
              <Link to={"/opportunities/" + application.opportunity_id}>View opportunity</Link>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
