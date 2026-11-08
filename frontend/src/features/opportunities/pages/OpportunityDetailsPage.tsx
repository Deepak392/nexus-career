import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getOpportunityById,
  getOpportunities,
  getSavedIds,
  toggleSaved,
} from "../api";
import type { Opportunity } from "../../../types";
import { formatDate } from "../../../utils/format";

interface DetailRequest {
  key: string;
  item: Opportunity | null;
  error: boolean;
}

interface SimilarRequest {
  opportunityId: string;
  items: Opportunity[];
}

export default function OpportunityDetailsPage() {
  const { id = "" } = useParams();
  const [reloadKey, setReloadKey] = useState(0);
  const [detailRequest, setDetailRequest] = useState<DetailRequest>({
    key: "",
    item: null,
    error: false,
  });
  const [similarRequest, setSimilarRequest] = useState<SimilarRequest>({
    opportunityId: "",
    items: [],
  });
  const [savedRequest, setSavedRequest] = useState(() => ({
    opportunityId: id,
    saved: getSavedIds().includes(id),
  }));

  const requestKey = `${id}::${reloadKey}`;
  const loading = detailRequest.key !== requestKey;
  const item = loading ? null : detailRequest.item;
  const error = !loading && detailRequest.error;
  const saved = savedRequest.opportunityId === id
    ? savedRequest.saved
    : getSavedIds().includes(id);
  const similar = item && similarRequest.opportunityId === item.id
    ? similarRequest.items
    : [];

  useEffect(() => {
    let cancelled = false;
    getOpportunityById(id)
      .then((result) => {
        if (!cancelled) {
          setDetailRequest({ key: requestKey, item: result, error: false });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetailRequest({ key: requestKey, item: null, error: true });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, requestKey]);

  useEffect(() => {
    if (!item) return undefined;
    let cancelled = false;
    getOpportunities({ type: item.type, limit: 4 })
      .then((result) => {
        if (!cancelled) {
          setSimilarRequest({
            opportunityId: item.id,
            items: result.items.filter((opportunity) => opportunity.id !== item.id).slice(0, 3),
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSimilarRequest({ opportunityId: item.id, items: [] });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [item]);

  const handleToggleSaved = () => {
    if (!item) return;
    setSavedRequest({
      opportunityId: item.id,
      saved: toggleSaved(item.id),
    });
  };

  return (
    <main className="container">
      <Link to="/opportunities">← Back to opportunities</Link>

      {loading && <div className="card skeleton tall" />}
      {error && (
        <div className="state error">
          <p>Something went wrong while loading this opportunity.</p>
          <button onClick={() => setReloadKey((key) => key + 1)}>Retry</button>
        </div>
      )}
      {!loading && !error && !item && (
        <div className="state"><p>Opportunity not found or no longer accepting applications.</p></div>
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
            {item.compensation} • {item.openings ? `${item.openings} openings` : "Openings not specified"} • Posted by {item.postedBy}
          </p>
          <p className="muted">Apply by {formatDate(item.deadline)}</p>

          {item.eligible === undefined ? (
            <div className="notice">
              <strong>Eligibility assessment is not available yet.</strong>
              <p>The opportunity's criteria are shown below. Automated profile matching will be added in a later increment.</p>
            </div>
          ) : item.eligible ? (
            <div className="notice ok">
              <strong>You are eligible for this opportunity.</strong>
              {item.matchScore !== undefined && (
                <div className="score">
                  <span>Match score: {item.matchScore}%</span>
                  <div className="bar"><div style={{ width: `${item.matchScore}%` }} /></div>
                </div>
              )}
            </div>
          ) : (
            <div className="notice no">
              <strong>Not eligible.</strong> Your profile does not meet the eligibility rules for this opportunity.
            </div>
          )}

          <h3>About this opportunity</h3>
          <p>{item.description}</p>
          <h3>Skills</h3>
          <div className="chips">
            {item.skills.map((skill) => <span key={skill} className="chip">{skill}</span>)}
          </div>
          <h3>Eligibility</h3>
          <p>{item.eligibility}</p>
          <h3>Requirements</h3>
          <ul>{item.requirements.map((requirement) => <li key={requirement}>{requirement}</li>)}</ul>

          <div className="row">
            <button
              className="btn"
              disabled={item.eligible !== true}
              onClick={() => alert("Apply flow will be added in a later sprint")}
            >
              {item.applicationMethod === "External link" ? "Apply on company site" : "Apply"}
            </button>
            <button className="btn secondary" onClick={handleToggleSaved}>
              {saved ? "Saved" : "Save opportunity"}
            </button>
          </div>
        </article>
      )}

      {!loading && !error && item && !item.eligible && similar.length > 0 && (
        <section>
          <h3>Other opportunities you may like</h3>
          <div className="grid">
            {similar.map((opportunity) => (
              <article key={opportunity.id} className="card">
                <span className="badge">{opportunity.type}</span>
                <h3>{opportunity.title}</h3>
                <p className="muted">{opportunity.company} • {opportunity.location}</p>
                <Link className="btn" to={`/opportunities/${opportunity.id}`}>View details</Link>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
