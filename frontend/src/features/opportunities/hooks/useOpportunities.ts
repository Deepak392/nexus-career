import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getOpportunities } from "../api";
import type { Opportunity, OpportunityQuery, PaginatedResponse } from "../../../types";

interface RequestState {
  key: string;
  data: PaginatedResponse<Opportunity> | null;
  error: string | null;
}

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
  const [reloadKey, setReloadKey] = useState(0);
  const [request, setRequest] = useState<RequestState>({
    key: "",
    data: null,
    error: null,
  });

  const queryKey = `${params.toString()}::${reloadKey}`;

  useEffect(() => {
    let cancelled = false;
    const query = readQuery(params);

    getOpportunities(query)
      .then((data) => {
        if (!cancelled) {
          setRequest({ key: queryKey, data, error: null });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRequest({
            key: queryKey,
            data: null,
            error: "Failed to load opportunities.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [params, queryKey]);

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    if (!("page" in changes)) next.delete("page");
    setParams(next);
  };

  const loading = request.key !== queryKey;

  return {
    query: readQuery(params),
    data: loading ? null : request.data,
    loading,
    error: loading ? null : request.error,
    retry: () => setReloadKey((key) => key + 1),
    update,
    clear: () => setParams({}),
  };
}
