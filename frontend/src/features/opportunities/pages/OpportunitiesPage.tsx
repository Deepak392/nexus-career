import { useOpportunities } from "../hooks/useOpportunities";
import { typeOptions } from "../api";
import OpportunityCard from "../components/OpportunityCard";
import SearchBar from "../components/SearchBar";
import FilterPanel from "../components/FilterPanel";
import Pagination from "../components/Pagination";

export default function OpportunitiesPage() {
  const { query, data, loading, error, retry, update, clear } = useOpportunities();

  return (
    <main className="container">
      <h1>Opportunities</h1>
      <p className="muted">Published jobs and internships approved by the Internship and Placement Cell.</p>
      <SearchBar value={query.search ?? ""} onChange={(value) => update({ q: value })} />
      <FilterPanel
        query={query}
        types={typeOptions}
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
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="card skeleton" />
          ))}
        </div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <div className="state">
          <p>No published opportunities match your search.</p>
          <button onClick={clear}>Clear filters</button>
        </div>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <p className="muted">{data.total} result(s)</p>
          <div className="grid">
            {data.items.map((opportunity) => (
              <OpportunityCard key={opportunity.id} opportunity={opportunity} />
            ))}
          </div>
          <Pagination
            page={data.page}
            total={data.total}
            limit={data.limit}
            onChange={(page) => update({ page: String(page) })}
          />
        </>
      )}
    </main>
  );
}
