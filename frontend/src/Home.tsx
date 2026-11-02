import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Home.css";

export default function Home() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const search = (e: FormEvent) => {
    e.preventDefault();
    navigate(`/opportunities?q=${encodeURIComponent(q)}`);
  };

  return (
    <div className="home">
      <h1>Find your next opportunity</h1>
      <p>Internships, jobs and workshops in one place.</p>
      <form onSubmit={search}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by title, company or skill..."
        />
        <button type="submit">Search</button>
      </form>
      <Link to="/opportunities" className="link">Browse all opportunities →</Link>
    </div>
  );
}