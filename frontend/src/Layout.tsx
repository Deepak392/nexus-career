import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "./context/AuthContext";
import ThemeToggle from "./components/ThemeToggle";
import "./Layout.css";

const studentLinks = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/opportunities", label: "Opportunities", icon: "💼", end: false },
  { to: "/saved", label: "My Saved Jobs", icon: "🔖", end: false },
  { to: "/applications", label: "My Applications", icon: "📄", end: false },
  { to: "/notifications", label: "Notifications", icon: "🔔", end: false },
  { to: "/profile", label: "Profile", icon: "👤", end: false },
  { to: "/settings", label: "Settings", icon: "⚙️", end: false },
];

export default function Layout() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await logout();
    navigate("/login");
  }

  const initials = user ? user.username.slice(0, 2).toUpperCase() : "?";
  const links = [
    ...studentLinks.slice(0, 2),
    ...(user?.role === "RECRUITER"
      ? [{ to: "/recruiter", label: "Recruiter dashboard", icon: "🏢", end: false }]
      : []),
    ...(user?.role === "IPC_ADMIN"
      ? [{ to: "/ipc", label: "IPC approvals", icon: "✅", end: false }]
      : []),
    ...studentLinks.slice(2),
  ];

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
            ) : (
              <div className="auth-nav-links">
                <NavLink to="/login">Sign in</NavLink>
                <NavLink to="/register">Register</NavLink>
              </div>
            )}
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              <span aria-hidden="true">{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="app-main"><Outlet /></main>
    </div>
  );
}
