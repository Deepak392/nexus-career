import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css";

const links = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/opportunities", label: "Opportunities", icon: "💼", end: false },
  { to: "/saved", label: "My Saved Jobs", icon: "🔖", end: false },
  { to: "/applications", label: "My Applications", icon: "📄", end: false },
  { to: "/profile", label: "Profile", icon: "👤", end: false },
  { to: "/settings", label: "Settings", icon: "⚙️", end: false },
];

export default function Layout() {
  const [user, setUser] = useState<string | null>(() =>
    localStorage.getItem("user")
  );

  const signIn = () => {
    const name = "Varun Sundar";
    localStorage.setItem("user", name);
    setUser(name);
  };

  const signOut = () => {
    localStorage.removeItem("user");
    setUser(null);
  };

  const initials = user
    ? user.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">Opportunities Hub</div>

        <div className="sidebar-profile">
          <div className="avatar">{initials}</div>
          <div>
            <p className="profile-name">{user ?? "Guest"}</p>
            {user ? (
              <button className="profile-btn" onClick={signOut}>Sign out</button>
            ) : (
              <button className="profile-btn" onClick={signIn}>Sign in</button>
            )}
          </div>
        </div>

        <nav className="sidebar-nav">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              <span>{l.icon}</span>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}