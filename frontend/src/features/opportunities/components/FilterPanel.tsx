import { useState } from "react";
import type { OpportunityQuery } from "../../../types";
import { modeOptions, sourceOptions } from "../api";

interface Props {
  query: OpportunityQuery;
  types: string[];
  locations: string[];
  onChange: (changes: Record<string, string>) => void;
  onClear: () => void;
}

export default function FilterPanel({ query, types, locations, onChange, onClear }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <section>
      <button className="filter-toggle" onClick={() => setOpen(!open)}>
        {open ? "Hide filters" : "Show filters"}
      </button>
      <div className={`filters ${open ? "open" : ""}`}>
        <select value={query.type} onChange={(e) => onChange({ type: e.target.value })}>
          <option value="">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select value={query.location} onChange={(e) => onChange({ location: e.target.value })}>
          <option value="">All locations</option>
          {locations.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <select value={query.mode} onChange={(e) => onChange({ mode: e.target.value })}>
          <option value="">Any work mode</option>
          {modeOptions.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select value={query.source} onChange={(e) => onChange({ source: e.target.value })}>
          <option value="">All sources</option>
          {sourceOptions.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={query.sort} onChange={(e) => onChange({ sort: e.target.value })}>
          <option value="newest">Newest</option>
          <option value="deadline">Deadline (soonest)</option>
          <option value="title">Title A-Z</option>
        </select>
        <button onClick={onClear}>Clear filters</button>
      </div>
    </section>
  );
}
