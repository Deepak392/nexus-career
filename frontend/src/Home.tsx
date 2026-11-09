import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "./context/AuthContext";
import "./Home.css";

interface WorkspaceAction {
  title: string;
  description: string;
  to: string;
  label: string;
}

export default function Home() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const search = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate(`/opportunities?q=${encodeURIComponent(q.trim())}`);
  };

  if (!user) {
    return (
      <main className="home home-public">
        <section className="home-hero">
          <div className="home-hero-copy">
            <p className="home-eyebrow">THE CAMPUS CAREER NETWORK</p>
            <h1>Move your career forward with the people and opportunities around you.</h1>
            <p className="home-lead">
              Discover jobs and internships, connect with alumni and build a clearer path from campus to career.
            </p>
            <form className="home-search" onSubmit={search}>
              <span className="home-search-mark" aria-hidden="true">⌕</span>
              <input
                aria-label="Search opportunities"
                value={q}
                onChange={(event) => setQ(event.target.value)}
                placeholder="Search roles, companies or skills"
              />
              <button type="submit">Search opportunities</button>
            </form>
            <div className="home-hero-links">
              <Link className="home-primary-link" to="/register/student">Create student account</Link>
              <Link className="home-secondary-link" to="/login">Sign in</Link>
            </div>
          </div>
          <div className="home-hero-aside">
            <div className="home-aside-label">NEXUS CAREER</div>
            <div className="home-aside-rule" />
            <h2>One platform.<br />A stronger network.</h2>
            <p>Career discovery, university-connected talent and alumni engagement in one workspace.</p>
            <div className="home-aside-meta"><span>01</span> Opportunities</div>
            <div className="home-aside-meta"><span>02</span> Alumni network</div>
            <div className="home-aside-meta"><span>03</span> Recruitment workflows</div>
          </div>
        </section>
        <section className="home-feature-grid" aria-label="Platform capabilities">
          <article className="home-feature">
            <span className="home-feature-number">01</span>
            <h2>Discover opportunities</h2>
            <p>Browse published jobs and internships, review requirements and check eligibility.</p>
            <Link to="/opportunities">Explore opportunities <span aria-hidden="true">→</span></Link>
          </article>
          <article className="home-feature">
            <span className="home-feature-number">02</span>
            <h2>Connect through campus</h2>
            <p>Use a shared university career space for students, alumni and recruiting organizations.</p>
            <Link to="/register/alumni">Join as alumni <span aria-hidden="true">→</span></Link>
          </article>
          <article className="home-feature">
            <span className="home-feature-number">03</span>
            <h2>Manage with confidence</h2>
            <p>Role-based workspaces support company verification and opportunity review.</p>
            <Link to="/register/recruiter">Recruiter registration <span aria-hidden="true">→</span></Link>
          </article>
        </section>
      </main>
    );
  }

  const actionsByRole: Record<string, WorkspaceAction[]> = {
    STUDENT: [
      { title: "Explore opportunities", description: "Search published jobs and internships and review eligibility requirements.", to: "/opportunities", label: "Browse opportunities" },
      { title: "Track applications", description: "Review submitted applications and their latest recruitment status.", to: "/applications", label: "View applications" },
      { title: "Maintain your profile", description: "Keep academic details and your resume ready for applications.", to: "/profile", label: "Open profile" },
    ],
    ALUMNI: [
      { title: "Explore opportunities", description: "Keep up with published roles and the wider campus career ecosystem.", to: "/opportunities", label: "Browse opportunities" },
      { title: "Stay informed", description: "Review platform updates and account notifications.", to: "/notifications", label: "View notifications" },
    ],
    RECRUITER: [
      { title: "Manage your organization", description: "Maintain company details and monitor its verification status.", to: "/recruiter", label: "Open recruiter workspace" },
      { title: "Published opportunities", description: "Browse the opportunities currently visible on the platform.", to: "/opportunities", label: "Browse opportunities" },
    ],
    IPC_ADMIN: [
      { title: "Approval queues", description: "Review companies and opportunity submissions awaiting IPC action.", to: "/ipc", label: "Open approval queues" },
      { title: "Published opportunities", description: "Review the current public opportunity catalogue.", to: "/opportunities", label: "Browse opportunities" },
    ],
    SYSTEM_ADMIN: [
      { title: "Platform overview", description: "Access the current application workspace and sign-in controls.", to: "/", label: "Refresh overview" },
    ],
  };

  const roleTitles: Record<string, string> = {
    STUDENT: "Student workspace",
    ALUMNI: "Alumni network",
    RECRUITER: "Recruiter workspace",
    IPC_ADMIN: "Placement operations",
    SYSTEM_ADMIN: "Platform overview",
  };
  const roleSubtitles: Record<string, string> = {
    STUDENT: "Discover relevant roles, manage your applications and keep your profile ready.",
    ALUMNI: "Stay connected to the campus career community and keep track of platform updates.",
    RECRUITER: "Manage your company presence and recruitment activity.",
    IPC_ADMIN: "Coordinate company verification and opportunity approval workflows.",
    SYSTEM_ADMIN: "A central entry point for the Nexus Career platform.",
  };
  const actions = actionsByRole[user.role] ?? actionsByRole.STUDENT;

  return (
    <main className="home home-dashboard">
      <header className="home-dashboard-heading">
        <div>
          <p className="home-eyebrow">{user.role.replaceAll("_", " ")}</p>
          <h1>{roleTitles[user.role] ?? "Workspace"}</h1>
          <p>{roleSubtitles[user.role] ?? "Welcome to Nexus Career."}</p>
        </div>
        <div className="home-user-reference">
          <span className="home-user-initials">{user.username.slice(0, 2).toUpperCase()}</span>
          <span><strong>{user.username}</strong><small>{user.email}</small></span>
        </div>
      </header>
      <section className="home-workspace-intro">
        <div>
          <p className="home-intro-label">NEXUS CAREER / OVERVIEW</p>
          <h2>Good to have you here.</h2>
          <p>Your workspace is organized around the tools and information available to your account type.</p>
        </div>
        <Link to="/opportunities" className="home-intro-link">Explore opportunities <span aria-hidden="true">→</span></Link>
      </section>
      <section className="home-action-grid" aria-label="Workspace actions">
        {actions.map((action, index) => (
          <article className="home-action-card" key={action.title}>
            <span className="home-action-index">0{index + 1}</span>
            <h2>{action.title}</h2>
            <p>{action.description}</p>
            <Link to={action.to}>{action.label} <span aria-hidden="true">→</span></Link>
          </article>
        ))}
      </section>
      {user.role === "ALUMNI" && (
        <div className="home-alumni-note">
          <strong>Alumni access</strong>
          <span>Alumni profiles are subject to the university's verification process. Features will appear as they are enabled for your account.</span>
        </div>
      )}
    </main>
  );
}
