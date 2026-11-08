
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../services/auth";
import "./AuthPages.css";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register(username.trim(), email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-logo">NC</span>
          <span>Nexus Career</span>
        </div>

        <h1>Create your account</h1>
        <p className="auth-subtitle">
          Join Nexus Career and explore opportunities.
        </p>

        <div className="auth-info">
          Student registration is currently enabled.
          Use your authorized university email address.
        </div>

        {error && (
          <div className="auth-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
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

          <label htmlFor="email">University email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="yourname@university.edu"
            autoComplete="email"
            required
          />

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
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="auth-footer">
          Already registered?{" "}
          <Link to="/login">Sign in</Link>
        </p>
      </div>
    </section>
  );
}
