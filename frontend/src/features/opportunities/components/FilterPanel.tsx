import { useState } from "react";
import type { OpportunityQuery } from "../../../types";
import { modeOptions, sourceOptions } from "../api";

interface Props {
  query: OpportunityQuery;
  types: string[];
  onChange: (changes: Record<string, string>) => void;
  onClear: () => void;
}

export default function FilterPanel({ query, types, onChange, onClear }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <button className="filter-toggle" onClick={() => setOpen(!open)}>
        {open ? "Hide filters" : "Show filters"}
      </button>
      <div className={`filters ${open ? "open" : ""}`}>
        <select value={query.type} onChange={(event) => onChange({ type: event.target.value })}>
          <option value="">All types</option>
          {types.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
        <input
          aria-label="Filter by location"
          type="search"
          placeholder="Filter by location"
          value={query.location ?? ""}
          onChange={(event) => onChange({ location: event.target.value })}
        />
        <select value={query.mode} onChange={(event) => onChange({ mode: event.target.value })}>
          <option value="">Any work mode</option>
          {modeOptions.map((mode) => <option key={mode} value={mode}>{mode}</option>)}
        </select>
        <select value={query.source} onChange={(event) => onChange({ source: event.target.value })}>
          <option value="">All sources</option>
          {sourceOptions.map((source) => <option key={source} value={source}>{source}</option>)}
        </select>
        <select value={query.sort} onChange={(event) => onChange({ sort: event.target.value })}>
          <option value="newest">Newest</option>
          <option value="deadline">Deadline (soonest)</option>
          <option value="title">Title A-Z</option>
        </select>
        <button onClick={onClear}>Clear filters</button>
      </div>
    </section>
  );
}
