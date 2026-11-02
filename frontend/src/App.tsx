import { RouterProvider, createBrowserRouter } from "react-router-dom";
import Layout from "./Layout";
import Home from "./Home";
import SimplePage from "./SimplePage";
import { opportunityRoutes } from "./features/opportunities/routes";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      ...opportunityRoutes,
      { path: "/saved", element: <SimplePage title="My Saved Jobs" text="Jobs you save will appear here." /> },
      { path: "/applications", element: <SimplePage title="My Applications" text="Track your applications here." /> },
      { path: "/profile", element: <SimplePage title="Profile" text="Your profile details will appear here." /> },
      { path: "/settings", element: <SimplePage title="Settings" text="Account settings will appear here." /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}