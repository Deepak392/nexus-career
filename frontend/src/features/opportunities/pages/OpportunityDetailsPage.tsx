import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getOpportunityById, getOpportunities, getSavedIds, toggleSaved } from "../api";
import type { Opportunity } from "../../../types";
import { formatDate } from "../../../utils/format";

export default function OpportunityDetailsPage() {
  const { id = "" } = useParams();
  const [item, setItem] = useState<Opportunity | null>(null);
  const [similar, setSimilar] = useState<Opportunity[]>([]);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    setSaved(getSavedIds().includes(id));
    getOpportunityById(id)
      .then((res) => {
        if (!cancelled) setItem(res);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  useEffect(() => {
    if (!item) return;
    let cancelled = false;
    getOpportunities({ type: item.type, limit: 4 }).then((res) => {
      if (!cancelled) setSimilar(res.items.filter((o) => o.id !== item.id).slice(0, 3));
    });
    return () => {
      cancelled = true;
    };
  }, [item]);

  return (
    <main className="container">
      <Link to="/opportunities">← Back to opportunities</Link>

      {loading && <div className="card skeleton tall" />}

      {error && (
        <div className="state error">
          <p>Something went wrong.</p>
          <button onClick={() => setReloadKey((k) => k + 1)}>Retry</button>
        </div>
      )}

      {!loading && !error && !item && (
        <div className="state">
          <p>Opportunity not found.</p>
        </div>
      )}

      {!loading && !error && item && (
        <article className="card details">
          <div className="row">
            <span className="badge">{item.type}</span>
            {item.source === "External" && <span className="badge ext">External</span>}
          </div>
          <h1>{item.title}</h1>
          <p className="muted">{item.company} • {item.location} • {item.mode}</p>
          <p className="muted">
            {item.compensation} • {item.openings} openings • Posted by {item.postedBy}
          </p>
          <p className="muted">Apply by {formatDate(item.deadline)}</p>

          {item.eligible ? (
            <div className="notice ok">
              <strong>You are eligible for this opportunity.</strong>
              <div className="score">
                <span>Match score: {item.matchScore}%</span>
                <div className="bar"><div style={{ width: `${item.matchScore}%` }} /></div>
              </div>
            </div>
          ) : (
            <div className="notice no">
              <strong>Not eligible.</strong> Your profile does not meet the eligibility rules
              for this opportunity.
            </div>
          )}

          <h3>About this opportunity</h3>
          <p>{item.description}</p>

          <h3>Skills</h3>
          <div className="chips">
            {item.skills.map((s) => (
              <span key={s} className="chip">{s}</span>
            ))}
          </div>

          <h3>Eligibility</h3>
          <p>{item.eligibility}</p>

          <h3>Requirements</h3>
          <ul>
            {item.requirements.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>

          <div className="row">
            <button
              className="btn"
              disabled={!item.eligible}
              onClick={() => alert("Apply flow will be added in a later sprint")}
            >
              {item.applicationMethod === "External link" ? "Apply on company site" : "Apply"}
            </button>
            <button className="btn secondary" onClick={() => setSaved(toggleSaved(item.id))}>
              {saved ? "Saved" : "Save opportunity"}
            </button>
          </div>
        </article>
      )}

      {!loading && !error && item && !item.eligible && similar.length > 0 && (
        <section>
          <h3>Other opportunities you may like</h3>
          <div className="grid">
            {similar.map((o) => (
              <article key={o.id} className="card">
                <span className="badge">{o.type}</span>
                <h3>{o.title}</h3>
                <p className="muted">{o.company} • {o.location}</p>
                <Link className="btn" to={`/opportunities/${o.id}`}>View details</Link>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
