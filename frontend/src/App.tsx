import { RouterProvider, createBrowserRouter } from "react-router-dom";

import Layout from "./Layout";
import Home from "./Home";
import SimplePage from "./SimplePage";
import { opportunityRoutes } from "./features/opportunities/routes";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import RecruiterDashboardPage from "./pages/RecruiterDashboardPage";
import IpcDashboardPage from "./pages/IpcDashboardPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import StudentProfilePage from "./pages/StudentProfilePage";
import NotificationsPage from "./pages/NotificationsPage";
import RequireRole from "./components/RequireRole";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      ...opportunityRoutes,
      {
        path: "/recruiter",
        element: <RequireRole allowedRoles={["RECRUITER"]}><RecruiterDashboardPage /></RequireRole>,
      },
      {
        path: "/ipc",
        element: <RequireRole allowedRoles={["IPC_ADMIN"]}><IpcDashboardPage /></RequireRole>,
      },
      { path: "/saved", element: <SimplePage title="My Saved Jobs" text="Jobs you save will appear here." /> },
      { path: "/applications", element: <ApplicationsPage /> },
      { path: "/notifications", element: <NotificationsPage /> },
      { path: "/profile", element: <StudentProfilePage /> },
      { path: "/settings", element: <SimplePage title="Settings" text="Account settings will appear here." /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
