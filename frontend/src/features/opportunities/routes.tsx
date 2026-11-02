import type { RouteObject } from "react-router-dom";
import OpportunitiesPage from "./pages/OpportunitiesPage";
import OpportunityDetailsPage from "./pages/OpportunityDetailsPage";

export const opportunityRoutes: RouteObject[] = [
  { path: "/opportunities", element: <OpportunitiesPage /> },
  { path: "/opportunities/:id", element: <OpportunityDetailsPage /> },
];
