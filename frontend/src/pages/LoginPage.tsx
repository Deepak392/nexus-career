import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage, type LoginRole } from "../services/auth";
import "./AuthPages.css";

const accountTypes: { role: LoginRole; label: string; description: string }[] = [
  { role: "STUDENT", label: "Student", description: "Explore jobs and internships" },
  { role: "ALUMNI", label: "Alumni", description: "Support students and share referrals" },
  { role: "RECRUITER", label: "Recruiter", description: "Manage company opportunities" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { role: routeRole } = useParams<{ role?: string }>();
  const [searchParams] = useSearchParams();

  const requestedRole = routeRole ?? searchParams.get("role");
  const selectedRole =
    accountTypes.find((item) => item.role === requestedRole?.toUpperCase())?.role ?? "STUDENT";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const locationState = location.state as
    | { from?: { pathname?: string } }
    | null;

  const redirectTo = locationState?.from?.pathname || "/";
  const selectedAccountType = accountTypes.find((item) => item.role === selectedRole);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username.trim(), password, selectedRole);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-page">
      <aside className="auth-visual">
        <div className="auth-visual-brand"><span className="auth-visual-logo">N</span><span>Nexus Career</span></div>
        <div className="auth-visual-copy">
          <p className="auth-visual-eyebrow">THE CAMPUS CAREER NETWORK</p>
          <h2>Your campus career network, connected.</h2>
          <p>Discover opportunities, build professional connections and move from campus to career with a platform designed around your university community.</p>
          <ul className="auth-visual-list">
            <li><span>01</span> Find jobs and internships</li>
            <li><span>02</span> Connect with verified alumni</li>
            <li><span>03</span> Access university-reviewed opportunities</li>
          </ul>
        </div>
        <p className="auth-visual-foot">NEXUS CAREER · UNIVERSITY CAREER PLATFORM</p>
      </aside>
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-logo">NC</span>
          <span>Nexus Career</span>
        </div>

        <h1>Welcome back</h1>
        <p className="auth-subtitle">
          Choose your account type and sign in to continue.
        </p>

        <form onSubmit={handleSubmit}>
          <fieldset className="auth-role-fieldset" disabled={loading}>
            <legend>Continue as</legend>
            <div className="auth-role-options">
              {accountTypes.map((accountType) => (
                <button
                  key={accountType.role}
                  className={
                    selectedRole === accountType.role
                      ? "auth-role-option selected"
                      : "auth-role-option"
                  }
                  type="button"
                  aria-pressed={selectedRole === accountType.role}
                  onClick={() => {
                    navigate(`/login/${accountType.role.toLowerCase()}`, { replace: true });
                    setError("");
                  }}
                >
                  <span className="auth-role-label">{accountType.label}</span>
                  <span className="auth-role-description">{accountType.description}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Enter your username"
            autoComplete="username"
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            autoComplete="current-password"
            required
          />

          <div className="auth-form-link-row">
            <Link className="auth-form-link" to="/forgot-password">
              Forgot password?
            </Link>
          </div>

          <button
            className="auth-submit"
            type="submit"
            disabled={loading}
          >
            {loading ? "Signing in..." : `Sign in as ${accountTypes.find((item) => item.role === selectedRole)?.label}`}
          </button>
        </form>

        <p className="auth-footer">
          New to Nexus Career as a {selectedAccountType?.label ?? "Student"}?{" "}
          <Link to={`/register/${selectedRole.toLowerCase()}`}>
            Create a {selectedAccountType?.label ?? "Student"} account
          </Link>
        </p>
      </div>
    </section>
  );
}
