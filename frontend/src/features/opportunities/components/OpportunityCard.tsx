import { Link } from "react-router-dom";
import type { Opportunity } from "../../../types";
import { formatDate } from "../../../utils/format";

export default function OpportunityCard({ opportunity: o }: { opportunity: Opportunity }) {
  return (
    <article className="card">
      <div className="row">
        <span className="badge">{o.type}</span>
        {o.source === "External" && <span className="badge ext">External</span>}
      </div>
      <h3>{o.title}</h3>
      <p className="muted">{o.company} • {o.location} • {o.mode}</p>
      <p className="muted">{o.compensation}</p>
      <div className="chips">
        {o.skills.slice(0, 3).map((s) => (
          <span key={s} className="chip">{s}</span>
        ))}
      </div>
      <p className="muted">Apply by {formatDate(o.deadline)}</p>
      <Link className="btn" to={`/opportunities/${o.id}`}>View details</Link>
    </article>
  );
}
