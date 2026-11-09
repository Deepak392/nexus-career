import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

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
  { to: "/", label: "Overview", icon: "⌂", end: true },
  { to: "/opportunities", label: "Opportunities", icon: "◇" },
];

const navigationByRole: Record<string, NavigationLink[]> = {
  STUDENT: [
    ...homeLinks,
    { to: "/applications", label: "Applications", icon: "▤" },
    { to: "/alumni/network", label: "Alumni network", icon: "◎" },
    { to: "/referrals", label: "My referrals", icon: "↗" },
    { to: "/notifications", label: "Notifications", icon: "◉" },
    { to: "/profile", label: "My profile", icon: "◌" },
  ],
  ALUMNI: [
    { to: "/", label: "Overview", icon: "⌂", end: true },
    { to: "/alumni", label: "Alumni dashboard", icon: "▦" },
    { to: "/alumni/profile", label: "Professional profile", icon: "◌" },
    { to: "/alumni/referrals", label: "Referral requests", icon: "↗" },
    { to: "/notifications", label: "Notifications", icon: "◉" },
  ],
  RECRUITER: [
    { to: "/", label: "Overview", icon: "⌂", end: true },
    { to: "/recruiter", label: "Recruiter workspace", icon: "▣" },
    { to: "/opportunities", label: "Browse opportunities", icon: "◇" },
  ],
  IPC_ADMIN: [
    { to: "/", label: "Overview", icon: "⌂", end: true },
    { to: "/ipc", label: "Approval queues", icon: "✓" },
    { to: "/opportunities", label: "Published opportunities", icon: "◇" },
  ],
  SYSTEM_ADMIN: [{ to: "/", label: "Overview", icon: "⌂", end: true }],
};

function areaLabel(pathname: string): string {
  if (pathname.startsWith("/register")) return "Create account";
  if (pathname.startsWith("/login")) return "Sign in";
  if (pathname.startsWith("/opportunities")) return "Opportunities";
  if (pathname.startsWith("/applications")) return "Applications";
  if (pathname.startsWith("/alumni/network")) return "Alumni network";
  if (pathname.startsWith("/alumni/referrals")) return "Referral requests";
  if (pathname.startsWith("/alumni/profile")) return "Professional profile";
  if (pathname.startsWith("/alumni")) return "Alumni dashboard";
  if (pathname.startsWith("/referrals")) return "My referrals";
  if (pathname.startsWith("/notifications")) return "Notifications";
  if (pathname.startsWith("/profile")) return "Profile";
  if (pathname.startsWith("/recruiter")) return "Recruiter workspace";
  if (pathname.startsWith("/ipc")) return "Approval queues";
  return "Overview";
}

export default function Layout() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthPage = location.pathname.startsWith("/login") || location.pathname.startsWith("/register");

  async function handleSignOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  const initials = user ? user.username.slice(0, 2).toUpperCase() : "GC";
  const links = isLoading ? [] : user ? navigationByRole[user.role] ?? homeLinks : homeLinks;

  return (
    <div className={isAuthPage ? "app-shell auth-shell" : "app-shell"}>
      {!isAuthPage && (
        <aside className="sidebar">
          <NavLink to="/" className="sidebar-brand" aria-label="Nexus Career home">
            <span className="sidebar-brand-mark">N</span>
            <span className="sidebar-brand-name">Nexus <strong>Career</strong></span>
          </NavLink>

          <div className="sidebar-section-label">WORKSPACE</div>
          <nav className="sidebar-nav" aria-label="Main navigation" aria-busy={isLoading}>
            {isLoading ? (
              <span className="sidebar-loading">Loading navigation...</span>
            ) : (
              links.map((link) => (
                <NavLink key={link.to} to={link.to} end={link.end} className="sidebar-link">
                  <span className="sidebar-icon" aria-hidden="true">{link.icon}</span>
                  <span>{link.label}</span>
                </NavLink>
              ))
            )}
          </nav>

          <div className="sidebar-spacer" />
          <ThemeToggle />
          <div className="sidebar-profile">
            <div className="avatar">{initials}</div>
            <div className="sidebar-profile-copy">
              <p className="profile-name">{isLoading ? "Loading..." : user?.username ?? "Guest user"}</p>
              <p className="sidebar-role">{isLoading ? "Checking access" : user?.role.replaceAll("_", " ") ?? "Public access"}</p>
            </div>
            {user ? (
              <button className="profile-btn" type="button" onClick={() => void handleSignOut()} aria-label="Sign out" title="Sign out">↗</button>
            ) : !isLoading ? (
              <NavLink className="profile-btn" to="/login" aria-label="Sign in" title="Sign in">↗</NavLink>
            ) : null}
          </div>
        </aside>
      )}

      <main className="app-main">
        {!isAuthPage && (
          <header className="workspace-topbar">
            <div>
              <p className="workspace-breadcrumb">NEXUS CAREER <span>/</span> WORKSPACE</p>
              <h2>{areaLabel(location.pathname)}</h2>
            </div>
            <div className="workspace-topbar-right">
              {user && <span className="workspace-access">{user.role.replaceAll("_", " ")}</span>}
              <span className="workspace-topbar-avatar">{initials}</span>
            </div>
          </header>
        )}
        <Outlet />
      </main>
    </div>
  );
}
