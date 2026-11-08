import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../../context/AuthContext";
import {
  getOpportunityById,
  getOpportunityEligibility,
  getOpportunities,
  getSavedIds,
  toggleSaved,
} from "../api";
import type { Opportunity } from "../../../types";
import { createApplication, type EligibilityResult } from "../../../services/student";
import { getApiErrorMessage } from "../../../services/auth";
import { formatDate } from "../../../utils/format";

interface DetailRequest { key: string; item: Opportunity | null; error: boolean; }
interface SimilarRequest { opportunityId: string; items: Opportunity[]; }
interface EligibilityRequest { key: string; result: EligibilityResult | null; error: string; }

export default function OpportunityDetailsPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [reloadKey, setReloadKey] = useState(0);
  const [detailRequest, setDetailRequest] = useState<DetailRequest>({ key: "", item: null, error: false });
  const [similarRequest, setSimilarRequest] = useState<SimilarRequest>({ opportunityId: "", items: [] });
  const [eligibilityRequest, setEligibilityRequest] = useState<EligibilityRequest>({ key: "", result: null, error: "" });
  const [savedRequest, setSavedRequest] = useState(() => ({
    opportunityId: id,
    saved: getSavedIds().includes(id),
  }));
  const [applying, setApplying] = useState(false);
  const [applicationError, setApplicationError] = useState("");

  const requestKey = id + "::" + reloadKey;
  const loading = detailRequest.key !== requestKey;
  const item = loading ? null : detailRequest.item;
  const error = !loading && detailRequest.error;
  const saved = savedRequest.opportunityId === id ? savedRequest.saved : getSavedIds().includes(id);
  const similar = item && similarRequest.opportunityId === item.id ? similarRequest.items : [];

  const isStudent = user?.role === "STUDENT";
  const eligibilityKey = id + "::" + String(user?.id ?? "guest");
  const eligibility = isStudent && eligibilityRequest.key === eligibilityKey
    ? eligibilityRequest.result
    : null;
  const eligibilityLoading = Boolean(isStudent && item && eligibilityRequest.key !== eligibilityKey);
  const eligibilityError = isStudent && eligibilityRequest.key === eligibilityKey
    ? eligibilityRequest.error
    : "";

  useEffect(() => {
    let cancelled = false;
    getOpportunityById(id)
      .then((result) => {
        if (!cancelled) setDetailRequest({ key: requestKey, item: result, error: false });
      })
      .catch(() => {
        if (!cancelled) setDetailRequest({ key: requestKey, item: null, error: true });
      });
    return () => { cancelled = true; };
  }, [id, requestKey]);

  useEffect(() => {
    if (!isStudent) return undefined;
    let cancelled = false;
    getOpportunityEligibility(id)
      .then((result) => {
        if (!cancelled) setEligibilityRequest({ key: eligibilityKey, result, error: "" });
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setEligibilityRequest({
            key: eligibilityKey,
            result: null,
            error: getApiErrorMessage(requestError),
          });
        }
      });
    return () => { cancelled = true; };
  }, [id, eligibilityKey, isStudent]);

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
        if (!cancelled) setSimilarRequest({ opportunityId: item.id, items: [] });
      });
    return () => { cancelled = true; };
  }, [item]);

  const handleToggleSaved = () => {
    if (!item) return;
    setSavedRequest({ opportunityId: item.id, saved: toggleSaved(item.id) });
  };

  async function handleApply() {
    if (!item || !eligibility?.ready_to_apply || item.applicationMethod !== "Apply on portal") return;
    setApplying(true);
    setApplicationError("");
    try {
      await createApplication(item.id);
      navigate("/applications", { replace: true });
    } catch (requestError) {
      const message = getApiErrorMessage(requestError);
      setApplicationError(message);
      if (message.toLowerCase().includes("already applied")) {
        setEligibilityRequest((current) => ({
          ...current,
          result: current.result
            ? { ...current.result, already_applied: true, ready_to_apply: false }
            : null,
        }));
      }
    } finally {
      setApplying(false);
    }
  }

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
            {item.compensation} • {item.openings ? item.openings + " openings" : "Openings not specified"} • Posted by {item.postedBy}
          </p>
          <p className="muted">Apply by {formatDate(item.deadline)}</p>

          {!user && (
            <div className="notice">
              <strong>Sign in with your student account to check eligibility.</strong>
              <p><Link to="/login">Sign in</Link> or <Link to="/register">create a student account</Link>.</p>
            </div>
          )}
          {user && !isStudent && (
            <div className="notice">Eligibility assessment and student applications are available to student accounts.</div>
          )}
          {isStudent && eligibilityLoading && (
            <div className="notice">Checking your profile against this opportunity’s eligibility criteria…</div>
          )}
          {isStudent && eligibilityError && (
            <div className="notice no" role="alert">
              <strong>Unable to check eligibility.</strong>
              <p>{eligibilityError}</p>
              <Link to="/profile">Review your student profile</Link>
            </div>
          )}
          {isStudent && eligibility && (
            <section className={"eligibility-result " + (
              eligibility.status === "ELIGIBLE" ? "eligible" :
              eligibility.status === "INELIGIBLE" ? "ineligible" : "incomplete"
            )}>
              <div className="eligibility-heading">
                <div>
                  <p className="eligibility-eyebrow">ELIGIBILITY CHECK</p>
                  <h2>
                    {eligibility.status === "ELIGIBLE"
                      ? "You meet the listed criteria"
                      : eligibility.status === "INELIGIBLE"
                        ? "You do not meet all listed criteria"
                        : "More profile information is needed"}
                  </h2>
                </div>
                <span className="eligibility-status">{eligibility.status.replaceAll("_", " ")}</span>
              </div>
              <p className="eligibility-summary">{eligibility.reasons[0]}</p>
              {eligibility.checks.length > 0 && (
                <div className="eligibility-check-list">
                  {eligibility.checks.map((check) => (
                    <div className="eligibility-check" key={check.key}>
                      <span className={"eligibility-check-mark " + check.status.toLowerCase()}>
                        {check.status === "MET" ? "✓" : check.status === "NOT_MET" ? "!" : "…"}
                      </span>
                      <div>
                        <strong>{check.label}</strong>
                        <p>{check.reason}</p>
                        <small>Required: {check.expected}{check.actual ? " · Your profile: " + check.actual : ""}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {eligibility.missing_fields.length > 0 && (
                <p className="eligibility-missing">Missing profile information: {eligibility.missing_fields.join(", ")}.</p>
              )}
              {eligibility.resume_message && <p className="eligibility-missing">{eligibility.resume_message}</p>}
              {eligibility.already_applied && (
                <p className="eligibility-summary">
                  You have already submitted an application for this opportunity. <Link to="/applications">View your applications</Link>.
                </p>
              )}
              {(eligibility.status !== "ELIGIBLE" || (eligibility.resume_required && !eligibility.has_resume)) && (
                <Link className="eligibility-profile-link" to="/profile">Complete or update my profile</Link>
              )}
            </section>
          )}

          {applicationError && <div className="notice no" role="alert">{applicationError}</div>}
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
            {item.applicationMethod === "External link" ? (
              eligibility?.ready_to_apply && item.externalApplicationUrl ? (
                <a className="btn" href={item.externalApplicationUrl} target="_blank" rel="noopener noreferrer">
                  Continue to company application
                </a>
              ) : (
                <button className="btn" type="button" disabled>Apply on company site</button>
              )
            ) : (
              <button
                className="btn"
                type="button"
                disabled={!eligibility?.ready_to_apply || applying || !isStudent}
                onClick={() => void handleApply()}
              >
                {applying ? "Submitting…" : eligibility?.already_applied ? "Already applied" : "Apply"}
              </button>
            )}
            <button className="btn secondary" onClick={handleToggleSaved}>
              {saved ? "Saved" : "Save opportunity"}
            </button>
          </div>
          {item.applicationMethod === "External link" && eligibility?.ready_to_apply && (
            <p className="muted external-application-note">
              You will complete this application on the company website. External submissions cannot be confirmed or tracked by Nexus Career.
            </p>
          )}
        </article>
      )}

      {!loading && !error && item && eligibility?.eligible === false && similar.length > 0 && (
        <section>
          <h3>Other opportunities you may like</h3>
          <div className="grid">
            {similar.map((opportunity) => (
              <article key={opportunity.id} className="card">
                <span className="badge">{opportunity.type}</span>
                <h3>{opportunity.title}</h3>
                <p className="muted">{opportunity.company} • {opportunity.location}</p>
                <Link className="btn" to={"/opportunities/" + opportunity.id}>View details</Link>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
