import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage, requestPasswordReset } from "../services/auth";
import "./AuthPages.css";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await requestPasswordReset(email.trim());
      setSubmitted(true);
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
          <p className="auth-visual-eyebrow">ACCOUNT RECOVERY</p>
          <h2>Get back to your career network.</h2>
          <p>Reset your password securely and return to the opportunities, people and connections that move your career forward.</p>
          <ul className="auth-visual-list">
            <li><span>01</span> Verify through your registered email</li>
            <li><span>02</span> Use a secure, time-limited link</li>
            <li><span>03</span> Choose a new password</li>
          </ul>
        </div>
        <p className="auth-visual-foot">NEXUS CAREER · UNIVERSITY CAREER PLATFORM</p>
      </aside>

      <div className="auth-card auth-recovery-card">
        <div className="auth-brand">
          <span className="auth-logo">NC</span>
          <span>Nexus Career</span>
        </div>
        {submitted ? (
          <>
            <h1>Check your inbox</h1>
            <p className="auth-subtitle">
              If an account is registered with that email address, password reset
              instructions have been sent. Follow the link in the email to choose
              a new password.
            </p>
            <div className="auth-info" role="status">
              For security, this confirmation is shown whether or not the email
              address is associated with an account.
            </div>
            <p className="auth-footer">
              <Link to="/login">Return to sign in</Link>
            </p>
          </>
        ) : (
          <>
            <h1>Forgot your password?</h1>
            <p className="auth-subtitle">
              Enter the email address linked to your Nexus Career account. We’ll
              send you a secure link to reset your password.
            </p>

            {error && <div className="auth-error" role="alert">{error}</div>}

            <form onSubmit={handleSubmit}>
              <label htmlFor="recovery-email">Email address</label>
              <input
                id="recovery-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Enter your registered email"
                autoComplete="email"
                required
              />
              <button className="auth-submit" type="submit" disabled={loading}>
                {loading ? "Sending instructions..." : "Send reset link"}
              </button>
            </form>

            <p className="auth-footer">
              Remember your password? <Link to="/login">Return to sign in</Link>
            </p>
          </>
        )}
      </div>
    </section>
  );
}
