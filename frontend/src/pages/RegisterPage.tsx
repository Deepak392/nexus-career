import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import {
  getApiErrorMessage,
  RegistrationSignInError,
  type LoginRole,
} from "../services/auth";
import "./AuthPages.css";

const accountTypes: {
  role: LoginRole;
  label: string;
  description: string;
}[] = [
  {
    role: "STUDENT",
    label: "Student",
    description: "University student",
  },
  {
    role: "ALUMNI",
    label: "Alumni",
    description: "Graduate of the university",
  },
  {
    role: "RECRUITER",
    label: "Recruiter",
    description: "Hiring for an organization",
  },
];

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const { role: routeRole } = useParams<{ role?: string }>();
  const [searchParams] = useSearchParams();
  const requestedRole = routeRole ?? searchParams.get("role");
  const selectedRole =
    accountTypes.find((accountType) => accountType.role === requestedRole?.toUpperCase())?.role ?? "STUDENT";
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [department, setDepartment] = useState("");
  const [degreeProgramme, setDegreeProgramme] = useState("");
  const [graduationYear, setGraduationYear] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [requiresManualSignIn, setRequiresManualSignIn] = useState(false);
  const [loading, setLoading] = useState(false);

  const selectedAccountType = accountTypes.find((item) => item.role === selectedRole);

  const registrationSubtitle = selectedRole === "STUDENT"
    ? "Register with your university email to access student opportunities."
    : selectedRole === "ALUMNI"
      ? "Create your alumni account with your academic details."
      : "Create a recruiter account to manage your organization’s opportunities.";

  const emailLabel = selectedRole === "STUDENT"
    ? "University email"
    : selectedRole === "ALUMNI"
      ? "Personal or alumni email"
      : "Email address";

  const emailPlaceholder = selectedRole === "STUDENT"
    ? "yourname@university.edu"
    : selectedRole === "ALUMNI"
      ? "you@example.com"
      : "you@example.com";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register(
        username.trim(),
        email.trim(),
        password,
        selectedRole,
        selectedRole === "ALUMNI"
          ? {
              department: department.trim(),
              degree_programme: degreeProgramme.trim(),
              graduation_year: Number(graduationYear),
            }
          : undefined
      );

      if (selectedRole === "ALUMNI") {
        setSuccess(
          "Your alumni account has been created. Your alumni profile is pending verification. " +
          "It will appear in alumni search after it has been verified."
        );
      } else {
        const destination = selectedRole === "RECRUITER" ? "/recruiter" : "/profile";
        navigate(destination, { replace: true });
      }
    } catch (err) {
      if (err instanceof RegistrationSignInError) {
        setRequiresManualSignIn(true);
        setSuccess(err.message);
      } else {
        setError(getApiErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-page">
      <aside className="auth-visual">
        <div className="auth-visual-brand"><span className="auth-visual-logo">N</span><span>Nexus Career</span></div>
        <div className="auth-visual-copy">
          <p className="auth-visual-eyebrow">JOIN THE CAMPUS NETWORK</p>
          <h2>Build meaningful connections beyond graduation.</h2>
          <p>Create an account that reflects your role in the campus career community. Your registration fields and access are tailored to your account type.</p>
          <ul className="auth-visual-list">
            <li><span>01</span> Student opportunity discovery</li>
            <li><span>02</span> Alumni engagement</li>
            <li><span>03</span> Recruiter and company workflows</li>
          </ul>
        </div>
        <p className="auth-visual-foot">NEXUS CAREER · UNIVERSITY CAREER PLATFORM</p>
      </aside>
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-logo">NC</span>
          <span>Nexus Career</span>
        </div>

        <h1>Create your {selectedAccountType?.label ?? "Student"} account</h1>
        <p className="auth-subtitle">{registrationSubtitle}</p>

        {success ? (
          <>
            <div className="auth-info" role="status">{success}</div>
            <button
              className="auth-submit"
              type="button"
              onClick={() =>
                navigate(
                  requiresManualSignIn ? `/login/${selectedRole.toLowerCase()}` : "/",
                  { replace: true }
                )
              }
            >
              {requiresManualSignIn
                ? `Sign in as ${selectedAccountType?.label ?? "Student"}`
                : "Continue to Nexus Career"}
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
          <fieldset className="auth-role-fieldset" disabled={loading}>
            <legend>Register as</legend>
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
                    navigate(`/register/${accountType.role.toLowerCase()}`, { replace: true });
                    setError("");
                  }}
                >
                  <span className="auth-role-label">{accountType.label}</span>
                  <span className="auth-role-description">{accountType.description}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {selectedRole === "STUDENT" && (
            <div className="auth-info">
              Use your university-approved email address. Student registration
              is restricted to the configured university email domain.
            </div>
          )}

          {selectedRole === "ALUMNI" && (
            <div className="auth-info">
              Provide your academic details to create an alumni account.
              Your alumni profile will remain pending until it is reviewed.
            </div>
          )}

          {selectedRole === "RECRUITER" && (
            <div className="auth-info">
              Use any valid email address; a university email is not required.
              After registering, create your company profile. The IPC must
              verify the company before you can submit opportunities.
            </div>
          )}

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
            placeholder="Choose a username"
            autoComplete="username"
            required
            minLength={3}
          />

          <label htmlFor="email">{emailLabel}</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={emailPlaceholder}
            autoComplete="email"
            required
          />

          {selectedRole === "ALUMNI" && (
            <>
              <div className="auth-registration-grid">
                <div>
                  <label htmlFor="department">Department</label>
                  <input
                    id="department"
                    type="text"
                    value={department}
                    onChange={(event) => setDepartment(event.target.value)}
                    placeholder="Computer Science"
                    maxLength={100}
                    required
                  />
                </div>
                <div>
                  <label htmlFor="degree-programme">Degree programme</label>
                  <input
                    id="degree-programme"
                    type="text"
                    value={degreeProgramme}
                    onChange={(event) => setDegreeProgramme(event.target.value)}
                    placeholder="B.Tech"
                    maxLength={100}
                    required
                  />
                </div>
              </div>

              <label htmlFor="graduation-year">Graduation year</label>
              <input
                id="graduation-year"
                type="number"
                min="1900"
                max={new Date().getFullYear()}
                step="1"
                value={graduationYear}
                onChange={(event) => setGraduationYear(event.target.value)}
                placeholder="2024"
                required
              />

            </>
          )}

          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Create a password"
            autoComplete="new-password"
            required
            minLength={8}
          />

          <label htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder="Re-enter your password"
            autoComplete="new-password"
            required
          />

          <button
            className="auth-submit"
            type="submit"
            disabled={loading}
          >
            {loading ? "Creating account..." : `Create ${accountTypes.find((item) => item.role === selectedRole)?.label} account`}
          </button>
          </form>
        )}

        <p className="auth-footer">
          Already have a {selectedAccountType?.label ?? "Student"} account?{" "}
          <Link to={`/login/${selectedRole.toLowerCase()}`}>Sign in as {selectedAccountType?.label ?? "Student"}</Link>
        </p>
      </div>
    </section>
  );
}
