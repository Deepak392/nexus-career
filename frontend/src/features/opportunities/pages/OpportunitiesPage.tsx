import { useOpportunities } from "../hooks/useOpportunities";
import { typeOptions, locationOptions } from "../api";
import OpportunityCard from "../components/OpportunityCard";
import SearchBar from "../components/SearchBar";
import FilterPanel from "../components/FilterPanel";
import Pagination from "../components/Pagination";

export default function OpportunitiesPage() {
  const { query, data, loading, error, retry, update, clear } = useOpportunities();

  return (
    <main className="container">
      <h1>Opportunities</h1>
      <SearchBar value={query.search ?? ""} onChange={(v) => update({ q: v })} />
      <FilterPanel
        query={query}
        types={typeOptions}
        locations={locationOptions}
        onChange={update}
        onClear={clear}
      />

      {error && (
        <div className="state error">
          <p>{error}</p>
          <button onClick={retry}>Retry</button>
        </div>
      )}

      {loading && !error && (
        <div className="grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card skeleton" />
          ))}
        </div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <div className="state">
          <p>No opportunities found.</p>
          <button onClick={clear}>Clear filters</button>
        </div>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <p className="muted">{data.total} result(s)</p>
          <div className="grid">
            {data.items.map((o) => (
              <OpportunityCard key={o.id} opportunity={o} />
            ))}
          </div>
          <Pagination
            page={data.page}
            total={data.total}
            limit={data.limit}
            onChange={(p) => update({ page: String(p) })}
          />
        </>
      )}
    </main>
  );
}
