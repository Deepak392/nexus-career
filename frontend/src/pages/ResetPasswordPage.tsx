import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  confirmPasswordReset,
  getApiErrorMessage,
} from "../services/auth";
import "./AuthPages.css";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!uid || !token) {
      setError("This password reset link is incomplete. Request a new link.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(uid, token, newPassword);
      setSuccess(true);
      setNewPassword("");
      setConfirmPassword("");
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
          <p className="auth-visual-eyebrow">SECURE ACCOUNT ACCESS</p>
          <h2>A fresh start, with a secure password.</h2>
          <p>Choose a strong password that protects your profile and your access to the Nexus Career community.</p>
          <ul className="auth-visual-list">
            <li><span>01</span> Use a unique password</li>
            <li><span>02</span> Avoid easily guessed information</li>
            <li><span>03</span> Sign in with your new credentials</li>
          </ul>
        </div>
        <p className="auth-visual-foot">NEXUS CAREER · UNIVERSITY CAREER PLATFORM</p>
      </aside>

      <div className="auth-card auth-recovery-card">
        <div className="auth-brand">
          <span className="auth-logo">NC</span>
          <span>Nexus Career</span>
        </div>

        {success ? (
          <>
            <h1>Password updated</h1>
            <p className="auth-subtitle">
              Your password has been changed successfully. You can now sign in
              using your new password.
            </p>
            <div className="auth-info" role="status">
              For your security, existing refresh-token sessions have been
              invalidated.
            </div>
            <p className="auth-footer"><Link to="/login">Continue to sign in</Link></p>
          </>
        ) : (
          <>
            <h1>Set a new password</h1>
            <p className="auth-subtitle">
              Enter a new password for your Nexus Career account. Reset links
              are valid for 30 minutes and can only be used once.
            </p>

            {!uid || !token ? (
              <div className="auth-error" role="alert">
                This reset link is incomplete. Request a new password reset link.
              </div>
            ) : null}
            {error && <div className="auth-error" role="alert">{error}</div>}

            <form onSubmit={handleSubmit}>
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="Enter a new password"
                autoComplete="new-password"
                required
                minLength={8}
                disabled={!uid || !token}
              />

              <label htmlFor="confirm-new-password">Confirm new password</label>
              <input
                id="confirm-new-password"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Re-enter your new password"
                autoComplete="new-password"
                required
                minLength={8}
                disabled={!uid || !token}
              />

              <p className="auth-reset-hint">
                Your password must meet the platform’s password security rules.
              </p>

              <button
                className="auth-submit"
                type="submit"
                disabled={loading || !uid || !token}
              >
                {loading ? "Updating password..." : "Update password"}
              </button>
            </form>

            <p className="auth-footer">
              <Link to="/forgot-password">Request another reset link</Link>
            </p>
          </>
        )}
      </div>
    </section>
  );
}
