
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../services/auth";
import {
  getAlumniProfile,
  updateAlumniProfile,
  uploadGraduationProof,
  type AlumniProfile,
} from "../services/alumni";
import "./AlumniPages.css";

interface ProfileForm {
  department: string;
  degree_programme: string;
  graduation_year: string;
  current_company: string;
  designation: string;
  industry: string;
  linkedin_url: string;
  is_open_to_referrals: boolean;
}

function toForm(profile: AlumniProfile): ProfileForm {
  return {
    department: profile.department,
    degree_programme: profile.degree_programme,
    graduation_year: String(profile.graduation_year),
    current_company: profile.current_company,
    designation: profile.designation,
    industry: profile.industry,
    linkedin_url: profile.linkedin_url || "",
    is_open_to_referrals: profile.is_open_to_referrals,
  };
}

export default function AlumniProfilePage() {
  const [profile, setProfile] = useState<AlumniProfile | null>(null);
  const [form, setForm] = useState<ProfileForm | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [proofFile, setProofFile] = useState<File | null>(null);
  const [uploadingProof, setUploadingProof] = useState(false);

  useEffect(() => {
    let active = true;

    getAlumniProfile()
      .then((result) => {
        if (!active) return;

        setProfile(result);
        setForm(toForm(result));
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!form) return;

    setSaving(true);
    setError("");
    setNotice("");

    try {
      const updated = await updateAlumniProfile({
        department: form.department.trim(),
        degree_programme: form.degree_programme.trim(),
        graduation_year: Number(form.graduation_year),
        current_company: form.current_company.trim(),
        designation: form.designation.trim(),
        industry: form.industry.trim(),
        linkedin_url: form.linkedin_url.trim(),
        is_open_to_referrals: form.is_open_to_referrals,
      });

      setProfile(updated);
      setForm(toForm(updated));
      setNotice("Your Alumni profile has been updated.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function handleProofUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!proofFile) {
      setError("Choose a PDF graduation proof before submitting.");
      return;
    }

    setUploadingProof(true);
    setError("");
    setNotice("");

    try {
      const updated = await uploadGraduationProof(proofFile);

      setProfile(updated);
      setProofFile(null);
      setNotice(
        "Graduation proof submitted. Your profile is awaiting IPC verification."
      );
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setUploadingProof(false);
    }
  }

  if (loading) {
    return (
      <main className="alumni-page">
        <div className="alumni-state">Loading profile…</div>
      </main>
    );
  }

  if (!form || !profile) {
    return (
      <main className="alumni-page">
        <header className="alumni-page-header">
          <div>
            <p className="alumni-eyebrow">ALUMNI PORTAL</p>
            <h1>My profile</h1>
          </div>
        </header>

        <div className="alumni-alert error" role="alert">
          {error || "Your Alumni profile could not be loaded."}
        </div>

        <Link className="alumni-text-link" to="/alumni">
          Return to dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="alumni-page">
      <header className="alumni-page-header">
        <div>
          <p className="alumni-eyebrow">ALUMNI PORTAL</p>
          <h1>Professional profile</h1>
          <p className="alumni-subtitle">
            Keep your academic and professional information up to date.
          </p>
        </div>

        <Link to="/alumni" className="alumni-secondary-button">
          Back to dashboard
        </Link>
      </header>

      <div className="alumni-profile-verification">
        <span
          className={`alumni-status ${profile.verification_status.toLowerCase()}`}
        >
          {profile.verification_status.replaceAll("_", " ")}
        </span>

        <p>
          {profile.verification_status === "VERIFIED"
            ? "Your profile is verified and can be discovered by students when referral availability is enabled."
            : "Your profile is pending university verification. It will be discoverable after it is verified."}
        </p>
      </div>

      {error && (
        <div className="alumni-alert error" role="alert">
          {error}
        </div>
      )}

      {notice && (
        <div className="alumni-alert success" role="status">
          {notice}
        </div>
      )}

      <section className="alumni-panel alumni-form">
        <div className="alumni-panel-heading">
          <div>
            <h2>Graduation verification</h2>
            <p>
              Submit a PDF document so the IPC can verify your alumni status.
              The document is stored privately and is not visible in the
              student directory.
            </p>
          </div>
        </div>

        {profile.has_graduation_proof && (
          <p className="alumni-muted">
            A graduation proof document is on file.
          </p>
        )}

        {profile.verification_rejection_reason && (
          <div className="alumni-alert error" role="alert">
            IPC review note: {profile.verification_rejection_reason}
          </div>
        )}

        <form className="alumni-inline-form" onSubmit={handleProofUpload}>
          <label>
            Graduation proof (PDF, max 5 MB)
            <input
              type="file"
              accept="application/pdf,.pdf"
              required
              onChange={(event) =>
                setProofFile(event.target.files?.[0] ?? null)
              }
            />
          </label>

          <button
            className="alumni-primary-button"
            type="submit"
            disabled={uploadingProof}
          >
            {uploadingProof ? "Uploading…" : "Submit for verification"}
          </button>
        </form>
      </section>

      <form className="alumni-panel alumni-form" onSubmit={handleSubmit}>
        <div className="alumni-panel-heading">
          <div>
            <h2>Academic information</h2>
            <p>Information associated with your Alumni registration.</p>
          </div>
        </div>

        <div className="alumni-form-grid">
          <label>
            Department
            <input
              required
              maxLength={100}
              value={form.department}
              onChange={(event) =>
                setForm({ ...form, department: event.target.value })
              }
            />
          </label>

          <label>
            Degree programme
            <input
              required
              maxLength={100}
              value={form.degree_programme}
              onChange={(event) =>
                setForm({ ...form, degree_programme: event.target.value })
              }
            />
          </label>

          <label>
            Graduation year
            <input
              required
              type="number"
              min="1900"
              max={new Date().getFullYear()}
              value={form.graduation_year}
              onChange={(event) =>
                setForm({ ...form, graduation_year: event.target.value })
              }
            />
          </label>
        </div>

        <div className="alumni-panel-heading">
          <div>
            <h2>Professional information</h2>
            <p>Help students find relevant alumni experience.</p>
          </div>
        </div>

        <div className="alumni-form-grid">
          <label>
            Current company
            <input
              maxLength={150}
              value={form.current_company}
              onChange={(event) =>
                setForm({ ...form, current_company: event.target.value })
              }
              placeholder="Company name"
            />
          </label>

          <label>
            Designation
            <input
              maxLength={150}
              value={form.designation}
              onChange={(event) =>
                setForm({ ...form, designation: event.target.value })
              }
              placeholder="Current job title"
            />
          </label>

          <label>
            Industry
            <input
              maxLength={100}
              value={form.industry}
              onChange={(event) =>
                setForm({ ...form, industry: event.target.value })
              }
              placeholder="Technology, Finance, Healthcare…"
            />
          </label>

          <label>
            LinkedIn profile URL
            <input
              type="url"
              maxLength={500}
              value={form.linkedin_url}
              onChange={(event) =>
                setForm({ ...form, linkedin_url: event.target.value })
              }
              placeholder="https://www.linkedin.com/in/your-profile"
            />
            <span className="alumni-muted">
              Optional. Leave blank if you do not want to display a LinkedIn
              profile link.
            </span>
          </label>
        </div>

        <section className="alumni-availability-control">
          <div>
            <strong>Accept student referral requests</strong>
            <p>
              When enabled, eligible Students can find your verified profile
              and send referral requests.
            </p>
          </div>

          <label className="alumni-switch">
            <input
              type="checkbox"
              checked={form.is_open_to_referrals}
              onChange={(event) =>
                setForm({
                  ...form,
                  is_open_to_referrals: event.target.checked,
                })
              }
            />
            <span>
              {form.is_open_to_referrals ? "Available" : "Unavailable"}
            </span>
          </label>
        </section>

        <div className="alumni-form-actions">
          <button
            className="alumni-primary-button"
            type="submit"
            disabled={saving}
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </form>
    </main>
  );
}
