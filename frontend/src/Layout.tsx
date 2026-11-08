import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "./context/AuthContext";
import ThemeToggle from "./components/ThemeToggle";
import "./Layout.css";

interface NavigationLink {
  to: string;
  label: string;
  icon: string;
  end?: boolean;
}

const homeLinks: NavigationLink[] = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/opportunities", label: "Opportunities", icon: "💼", end: false },
];

const studentLinks: NavigationLink[] = [
  ...homeLinks,
  { to: "/applications", label: "My Applications", icon: "📄", end: false },
  { to: "/notifications", label: "Notifications", icon: "🔔", end: false },
  { to: "/profile", label: "My Profile", icon: "👤", end: false },
];

const recruiterLinks: NavigationLink[] = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/recruiter", label: "Recruiter Dashboard", icon: "🏢", end: false },
  { to: "/opportunities", label: "Browse Opportunities", icon: "💼", end: false },
];

const ipcAdminLinks: NavigationLink[] = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/ipc", label: "IPC Dashboard", icon: "✅", end: false },
  { to: "/opportunities", label: "Browse Opportunities", icon: "💼", end: false },
];

// Alumni and technical-administration workflows do not have dedicated routes yet.
// Keep their menus limited to pages that currently exist and are shared.
const alumniLinks: NavigationLink[] = homeLinks;
const systemAdminLinks: NavigationLink[] = [
  { to: "/", label: "Home", icon: "🏠", end: true },
];

const navigationByRole: Record<string, NavigationLink[]> = {
  STUDENT: studentLinks,
  RECRUITER: recruiterLinks,
  IPC_ADMIN: ipcAdminLinks,
  ALUMNI: alumniLinks,
  SYSTEM_ADMIN: systemAdminLinks,
};

const guestLinks = homeLinks;
const fallbackAuthenticatedLinks = homeLinks;

export default function Layout() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await logout();
    navigate("/login");
  }

  const initials = user ? user.username.slice(0, 2).toUpperCase() : "?";
  const links = isLoading
    ? []
    : user
      ? navigationByRole[user.role] ?? fallbackAuthenticatedLinks
      : guestLinks;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">Nexus Career</div>
        <ThemeToggle />
        <div className="sidebar-profile">
          <div className="avatar">{initials}</div>
          <div>
            <p className="profile-name">{isLoading ? "Loading..." : user?.username ?? "Guest"}</p>
            {user ? (
              <>
                <p className="muted">{user.role.replaceAll("_", " ")}</p>
                <button className="profile-btn" onClick={() => void handleSignOut()}>Sign out</button>
              </>
            ) : !isLoading ? (
              <div className="auth-nav-links">
                <NavLink to="/login">Sign in</NavLink>
                <NavLink to="/register">Register</NavLink>
              </div>
            ) : null}
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Main navigation" aria-busy={isLoading}>
          {isLoading ? (
            <span aria-live="polite">Loading navigation...</span>
          ) : (
            links.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.end}>
                <span aria-hidden="true">{link.icon}</span>
                {link.label}
              </NavLink>
            ))
          )}
        </nav>
      </aside>
      <main className="app-main"><Outlet /></main>
    </div>
  );
}
