# Sprint 1–3 delivery summary

This document records the implementation currently present in the repository and the incremental Alumni/referral work proposed for review. It is based on the project SRS and the code merged or included in this branch. It is not a claim that every SRS requirement is complete.

## Sprint 1 — Platform foundation and identity

### Delivered foundation
- React 19 + TypeScript + Vite frontend and Django 5.2 + Django REST Framework backend.
- PostgreSQL-backed application data and Docker Compose development environment.
- Versioned REST API, OpenAPI/Swagger documentation and GitHub Actions quality checks.
- Custom user model with Student, Alumni, Recruiter, IPC Admin and System Admin roles.
- JWT login, refresh, logout and current-user endpoints.
- Role-aware registration and frontend route/navigation guards.
- Student and Alumni profile APIs and profile pages.

### SRS alignment
- Foundation for FR-AUTH-01 through FR-AUTH-05 and FR-AUTH-07.
- Initial student profile and alumni profile support for FR-STU-01 through FR-STU-03 and FR-ALM-02.

### Not claimed as complete
Password recovery, account suspension/reactivation, institutional SSO and a complete university identity-verification integration still require policy and implementation work.

## Sprint 2 — Recruiter, company and opportunity lifecycle

### Delivered workflow
- Recruiters create and maintain a company profile.
- Company verification and rejection are restricted to IPC administrators.
- Recruiters manage company-scoped opportunity drafts and submit them for approval.
- IPC administrators review, approve and reject opportunities.
- Opportunity close and archive actions and workflow audit events.
- Public opportunity discovery uses backend data and supports search, filtering, sorting and pagination.
- Recruiter permissions are scoped to the recruiter's associated company.

### SRS alignment
- Opportunity creation, criteria and publication lifecycle: FR-OPP-01 through FR-OPP-10.
- Company profile and recruiter scoping: FR-REC-01, FR-REC-02 and FR-REC-07.
- IPC company/opportunity review: FR-ADM-06.
- Opportunity search/discovery: FR-SEARCH-01 through FR-SEARCH-07.

### Not claimed as complete
Recruiter invitations/verification automation and advanced administrative reporting remain subject to further work and university policy.

## Sprint 3 — Student applications and Alumni engagement

### Student opportunity workflow already present
- Student PDF resume upload and private storage.
- Rule-based eligibility evaluation for CGPA, graduation year, degree programme, department and skills, including MET / NOT_MET / MISSING explanations.
- Platform application submission with duplicate prevention, resume snapshot, status history and student application tracking.
- External application links are opened directly; the platform does not claim to track external submissions.
- In-app application-submitted notifications and a per-user notification inbox.

### Alumni and referral increment in this branch
- Alumni professional profile maintenance and referral availability.
- Private graduation-proof submission and IPC verification/rejection workflow.
- Student Alumni directory with company, designation and department filters.
- Referral requests containing an opportunity URL, PDF resume and note.
- Alumni accept/decline/request-information actions, student responses and mark-referred action.
- Referral status history, duplicate active-request protection, participant-scoped resume downloads and engagement metrics.
- In-app notifications for referral events.

### SRS alignment
- Student eligibility and applications: FR-ELIG-01 through FR-ELIG-06, FR-APP-01, FR-APP-04 and FR-APP-07.
- Alumni workflows: FR-ALM-01 through FR-ALM-04.
- Referral workflows: FR-REF-01 through FR-REF-04.
- Notification submission/read workflows: FR-NOT-01 and FR-NOT-04, plus referral event notifications.

## Remaining work after these increments

The following SRS areas are not represented as complete by this delivery:
- Recruiter/IPC application review queues and authorized application status transitions.
- Full administrative KPI dashboard, date/company/status filtering and CSV report export.
- Email delivery, deadline reminders and notification preferences.
- Broader reporting/analytics and saved-search/personalized-recommendation features.
- Password reset, account suspension/reactivation and institutional identity/SSO integrations.
- University-approved retention/deletion periods and operational confirmation of production backup/restore targets.
- Further security, accessibility, performance and user-acceptance testing in the target deployment environment.

## Validation

GitHub Actions runs the Django/PostgreSQL system check, migration consistency check, migrations and backend tests, plus frontend ESLint and production build. Python Ruff runs on the backend source. This branch must pass those checks before merge; a successful commit or PR creation alone is not evidence that the checks passed.
