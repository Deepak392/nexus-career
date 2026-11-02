import type { Opportunity } from "../types";

type Row = {
  title: string;
  company: string;
  location: string;
  type: string;
  mode: Opportunity["mode"];
  compensation: string;
  skills: string[];
  eligibility: string;
  postedBy: Opportunity["postedBy"];
};

const rows: Row[] = [
  { title: "Frontend Developer Intern", company: "TechNova", location: "Chennai", type: "Internship", mode: "Hybrid", compensation: "₹20,000/month", skills: ["React", "TypeScript", "CSS"], eligibility: "B.E/B.Tech CSE/IT, CGPA 7.0+, 2027 batch", postedBy: "Recruiter" },
  { title: "Software Engineer Trainee", company: "Zoho Corp", location: "Chennai", type: "Full-time", mode: "On-site", compensation: "₹6 LPA", skills: ["Java", "DSA", "SQL"], eligibility: "Any branch, CGPA 6.5+, 2026 batch", postedBy: "Placement Cell" },
  { title: "Data Analyst Intern", company: "InsightLabs", location: "Hyderabad", type: "Internship", mode: "Remote", compensation: "₹15,000/month", skills: ["Python", "SQL", "Power BI"], eligibility: "CSE/IT/ECE, CGPA 6.5+, 2027 batch", postedBy: "Recruiter" },
  { title: "Campus Hiring Drive: Infosys", company: "Infosys", location: "Bengaluru", type: "Full-time", mode: "On-site", compensation: "₹3.6 LPA", skills: ["Aptitude", "Programming basics"], eligibility: "All branches, no active backlogs, 2026 batch", postedBy: "Placement Cell" },
  { title: "ML Research Intern", company: "IIT Madras Research Park", location: "Chennai", type: "Research", mode: "On-site", compensation: "₹25,000/month", skills: ["Python", "PyTorch", "Statistics"], eligibility: "CSE/AI&DS, CGPA 8.0+, pre-final year", postedBy: "Alumni" },
  { title: "Smart India Hackathon 2026", company: "Ministry of Education", location: "Remote", type: "Hackathon", mode: "Remote", compensation: "Prize pool ₹1,00,000", skills: ["Problem solving", "Teamwork", "Prototyping"], eligibility: "Teams of 6, all branches", postedBy: "Placement Cell" },
  { title: "UI/UX Design Intern", company: "PixelCraft", location: "Bengaluru", type: "Internship", mode: "Hybrid", compensation: "₹12,000/month", skills: ["Figma", "User research", "Prototyping"], eligibility: "Any branch, portfolio required", postedBy: "Recruiter" },
  { title: "Google Generation Scholarship", company: "Google", location: "Remote", type: "Scholarship", mode: "Remote", compensation: "₹1,00,000 grant", skills: ["Leadership", "Coding"], eligibility: "Women in CS, CGPA 8.0+", postedBy: "Placement Cell" },
  { title: "Backend Developer Intern", company: "CodeWorks", location: "Pune", type: "Internship", mode: "On-site", compensation: "₹18,000/month", skills: ["Node.js", "MongoDB", "REST APIs"], eligibility: "CSE/IT, CGPA 7.0+, 2027 batch", postedBy: "Alumni" },
  { title: "Cyber Security Trainee", company: "SecureNet", location: "Hyderabad", type: "Full-time", mode: "On-site", compensation: "₹5 LPA", skills: ["Networking", "Linux", "Ethical hacking"], eligibility: "CSE/IT/ECE, 2026 batch", postedBy: "Recruiter" },
  { title: "DevOps Intern", company: "InfraHub", location: "Remote", type: "Internship", mode: "Remote", compensation: "₹15,000/month", skills: ["Docker", "Git", "CI/CD"], eligibility: "CSE/IT, CGPA 7.0+, 2027 batch", postedBy: "Alumni" },
  { title: "Associate Consultant", company: "Deloitte", location: "Mumbai", type: "Full-time", mode: "Hybrid", compensation: "₹7.5 LPA", skills: ["Excel", "Communication", "Analytics"], eligibility: "Any branch, CGPA 7.0+, 2026 batch", postedBy: "Placement Cell" },
  { title: "Mobile App Developer Intern", company: "AppForge", location: "Bengaluru", type: "Internship", mode: "Hybrid", compensation: "₹20,000/month", skills: ["Flutter", "Dart", "Firebase"], eligibility: "CSE/IT, 2027 batch", postedBy: "Recruiter" },
  { title: "Resume and Interview Prep Workshop", company: "Alumni Association", location: "Chennai", type: "Workshop", mode: "On-site", compensation: "Free", skills: ["Resume writing", "Mock interviews"], eligibility: "Final-year students", postedBy: "Alumni" },
  { title: "Full Stack Developer", company: "StackLine", location: "Remote", type: "Full-time", mode: "Remote", compensation: "₹8 LPA", skills: ["React", "Node.js", "PostgreSQL"], eligibility: "CSE/IT, CGPA 7.5+, 2026 batch", postedBy: "Recruiter" },
  { title: "Product Management Intern", company: "LaunchPad", location: "Hyderabad", type: "Internship", mode: "Hybrid", compensation: "₹22,000/month", skills: ["Product thinking", "Analytics", "Communication"], eligibility: "Any branch, 2027 batch", postedBy: "Alumni" },
  { title: "Cloud Engineer Associate", company: "SkyOps", location: "Pune", type: "Full-time", mode: "On-site", compensation: "₹6.5 LPA", skills: ["AWS", "Linux", "Networking"], eligibility: "CSE/IT/ECE, 2026 batch", postedBy: "Recruiter" },
  { title: "Open Source Summer Program", company: "FOSS United", location: "Remote", type: "Research", mode: "Remote", compensation: "₹30,000 stipend", skills: ["Git", "Open source", "Any language"], eligibility: "All branches, pre-final and final year", postedBy: "Alumni" },
];

export const opportunities: Opportunity[] = rows.map((r, i): Opportunity => {
  const external = i % 6 === 5;
  return {
    ...r,
    id: String(i + 1),
    status: i === 16 ? "PENDING_APPROVAL" : "PUBLISHED",
    source: external ? "External" : "Internal",
    applicationMethod: external ? "External link" : "Apply on portal",
    eligible: i % 5 !== 3,
    matchScore: 55 + ((i * 7) % 41),
    openings: 2 + (i % 5) * 3,
    deadline: `2026-11-${String(10 + i).padStart(2, "0")}`,
    postedAt: `2026-10-${String(1 + (i % 7)).padStart(2, "0")}`,
    description: `${r.company} is looking for students for the ${r.title} opportunity based in ${r.location} (${r.mode}). You will work on real projects, get mentorship, and build skills in ${r.skills.join(", ")}.`,
    requirements: [
      `Skills: ${r.skills.join(", ")}`,
      `Eligibility: ${r.eligibility}`,
      "Updated profile and resume on the portal",
    ],
  };
});
