import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getOpportunities } from "../api";
import type { Opportunity, OpportunityQuery, PaginatedResponse } from "../../../types";

function readQuery(params: URLSearchParams): OpportunityQuery {
  return {
    search: params.get("q") ?? "",
    type: params.get("type") ?? "",
    location: params.get("location") ?? "",
    mode: params.get("mode") ?? "",
    source: params.get("source") ?? "",
    sort: (params.get("sort") as OpportunityQuery["sort"]) ?? "newest",
    page: Number(params.get("page") ?? 1),
    limit: 9,
  };
}

export function useOpportunities() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<PaginatedResponse<Opportunity> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getOpportunities(readQuery(params))
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load opportunities.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params, reloadKey]);

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("page" in changes)) next.delete("page");
    setParams(next);
  };

  return {
    query: readQuery(params),
    data,
    loading,
    error,
    retry: () => setReloadKey((k) => k + 1),
    update,
    clear: () => setParams({}),
  };
}
