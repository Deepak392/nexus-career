import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../services/auth";
import {
  getStudentProfile,
  isProfileNotFound,
  saveStudentProfile,
  type StudentProfile,
} from "../services/student";
import "./StudentPages.css";

interface ProfileDraft {
  student_id: string;
  department: string;
  degree_programme: string;
  graduation_year: string;
  cgpa: string;
  skills: string;
  areas_of_interest: string;
  experience: string;
  preferred_roles: string;
  preferred_locations: string;
  work_mode: string;
}

const emptyDraft: ProfileDraft = {
  student_id: "", department: "", degree_programme: "", graduation_year: "",
  cgpa: "", skills: "", areas_of_interest: "", experience: "",
  preferred_roles: "", preferred_locations: "", work_mode: "",
};

function toDraft(profile: StudentProfile): ProfileDraft {
  return {
    student_id: profile.student_id ?? "",
    department: profile.department,
    degree_programme: profile.degree_programme,
    graduation_year: String(profile.graduation_year),
    cgpa: profile.cgpa ?? "",
    skills: profile.skills.join(", "),
    areas_of_interest: profile.areas_of_interest.join(", "),
    experience: profile.experience,
    preferred_roles: profile.preferred_roles.join(", "),
    preferred_locations: profile.preferred_locations.join(", "),
    work_mode: profile.work_mode,
  };
}

function appendList(form: FormData, key: string, value: string) {
  const entries = value.split(",").map((item) => item.trim()).filter(Boolean);
  if (entries.length === 0) {
    form.append(key, "");
    return;
  }
  entries.forEach((item) => form.append(key, item));
}

export default function StudentProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [draft, setDraft] = useState<ProfileDraft>(emptyDraft);
  const [resume, setResume] = useState<File | null>(null);
  const [removeResume, setRemoveResume] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (user?.role !== "STUDENT") {
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    getStudentProfile()
      .then((result) => {
        if (!active) return;
        setProfile(result);
        setDraft(toDraft(result));
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        if (isProfileNotFound(requestError)) {
          setProfile(null);
          setDraft(emptyDraft);
        } else {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [user?.role]);

  function updateField<K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!draft.department.trim() || !draft.degree_programme.trim() || !draft.graduation_year) {
      setError("Department, degree programme and graduation year are required.");
      return;
    }
    const year = Number(draft.graduation_year);
    const cgpa = draft.cgpa.trim();
    if (!Number.isInteger(year) || year < 2000 || year > 2100) {
      setError("Enter a valid graduation year.");
      return;
    }
    if (cgpa && (!Number.isFinite(Number(cgpa)) || Number(cgpa) < 0 || Number(cgpa) > 10)) {
      setError("CGPA must be between 0 and 10.");
      return;
    }

    const form = new FormData();
    form.append("student_id", draft.student_id.trim());
    form.append("department", draft.department.trim());
    form.append("degree_programme", draft.degree_programme.trim());
    form.append("graduation_year", String(year));
    form.append("cgpa", cgpa);
    form.append("experience", draft.experience.trim());
    form.append("work_mode", draft.work_mode);
    appendList(form, "skills", draft.skills);
    appendList(form, "areas_of_interest", draft.areas_of_interest);
    appendList(form, "preferred_roles", draft.preferred_roles);
    appendList(form, "preferred_locations", draft.preferred_locations);
    if (resume) form.append("resume", resume);
    if (removeResume) form.append("remove_resume", "true");

    setSaving(true);
    try {
      const saved = await saveStudentProfile(form, Boolean(profile));
      setProfile(saved);
      setDraft(toDraft(saved));
      setResume(null);
      setRemoveResume(false);
      setSuccess("Your student profile has been saved.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  if (user?.role !== "STUDENT") {
    return (
      <main className="student-page">
        <h1>Student profile</h1>
        <p>Sign in with a student account to create or manage your academic profile.</p>
        <Link to="/login">Sign in</Link>
      </main>
    );
  }

  return (
    <main className="student-page">
      <header className="student-page-header">
        <div>
          <p className="student-eyebrow">STUDENT PORTAL</p>
          <h1>My academic profile</h1>
          <p className="student-muted">Keep your academic details and skills up to date so Nexus Career can check opportunity eligibility.</p>
        </div>
      </header>
      {loading ? (
        <div className="student-panel student-state">Loading your profile…</div>
      ) : (
        <form className="student-panel student-form" onSubmit={handleSubmit}>
          <div className="student-panel-heading">
            <div>
              <h2>Academic information</h2>
              <p>These details are used to evaluate published eligibility criteria.</p>
            </div>
            {profile && <span className="student-status">Profile created</span>}
          </div>
          {error && <div className="student-alert error" role="alert">{error}</div>}
          {success && <div className="student-alert success" role="status">{success}</div>}
          <div className="student-form-grid">
            <label>Student ID (optional)
              <input value={draft.student_id} onChange={(event) => updateField("student_id", event.target.value)} />
            </label>
            <label>Department *
              <input required value={draft.department} onChange={(event) => updateField("department", event.target.value)} placeholder="Computer Science" />
            </label>
            <label>Degree programme *
              <input required value={draft.degree_programme} onChange={(event) => updateField("degree_programme", event.target.value)} placeholder="B.Tech" />
            </label>
            <label>Expected graduation year *
              <input required type="number" min="2000" max="2100" step="1" value={draft.graduation_year} onChange={(event) => updateField("graduation_year", event.target.value)} placeholder="2027" />
            </label>
            <label>Current CGPA (0–10)
              <input type="number" min="0" max="10" step="0.01" value={draft.cgpa} onChange={(event) => updateField("cgpa", event.target.value)} placeholder="8.50" />
            </label>
            <label>Preferred work mode
              <select value={draft.work_mode} onChange={(event) => updateField("work_mode", event.target.value)}>
                <option value="">No preference</option>
                <option value="ONSITE">On-site</option>
                <option value="HYBRID">Hybrid</option>
                <option value="REMOTE">Remote</option>
              </select>
            </label>
          </div>
          <label>Skills (comma-separated)
            <textarea rows={3} value={draft.skills} onChange={(event) => updateField("skills", event.target.value)} placeholder="Python, Django, SQL, React" />
          </label>
          <div className="student-form-grid">
            <label>Areas of interest
              <input value={draft.areas_of_interest} onChange={(event) => updateField("areas_of_interest", event.target.value)} placeholder="Backend development, AI" />
            </label>
            <label>Preferred roles
              <input value={draft.preferred_roles} onChange={(event) => updateField("preferred_roles", event.target.value)} placeholder="Software Engineer, Data Analyst" />
            </label>
            <label>Preferred locations
              <input value={draft.preferred_locations} onChange={(event) => updateField("preferred_locations", event.target.value)} placeholder="Chennai, Bengaluru" />
            </label>
          </div>
          <label>Relevant experience
            <textarea rows={4} value={draft.experience} onChange={(event) => updateField("experience", event.target.value)} placeholder="Projects, internships and relevant experience" />
          </label>
          <section className="student-resume-box">
            <div>
              <h3>Resume (PDF)</h3>
              <p>{profile?.has_resume ? "A resume is currently saved privately in your profile." : "A PDF resume (maximum 5 MB) is required for platform applications."}</p>
            </div>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => {
                setResume(event.target.files?.[0] ?? null);
                setRemoveResume(false);
              }}
            />
            {resume && <span className="student-muted">Selected: {resume.name}</span>}
            {profile?.has_resume && (
              <label className="student-inline-check">
                <input type="checkbox" checked={removeResume} onChange={(event) => setRemoveResume(event.target.checked)} />
                Remove the currently saved resume
              </label>
            )}
          </section>
          <div className="student-actions">
            <button className="student-primary-button" type="submit" disabled={saving}>
              {saving ? "Saving…" : profile ? "Save profile" : "Create profile"}
            </button>
            <Link to="/opportunities">Browse opportunities</Link>
          </div>
        </form>
      )}
    </main>
  );
}
