# Sprint 2: Recruiter and Opportunity Approval Workflow

## Scope implemented

This increment adds the backend and frontend foundation for recruiter company management, opportunity submission, IPC company verification, IPC opportunity approval/rejection, workflow audit events and role-specific dashboards.

## Recruiter onboarding decision

SRS assumption A-06 (direct recruiter registration versus IPC invitation) remains a stakeholder decision. This increment does not add public recruiter self-registration or let users assign themselves the RECRUITER role. Recruiter accounts must be provisioned by an authorized Django administrator until the university confirms the onboarding policy.

The custom User model is registered in Django admin with role and verification fields. Do not grant Django admin access to external recruiters.

Company verification is separate from email verification. Creating a company profile sets status to PENDING. A recruiter can save draft opportunities but cannot submit until the company is VERIFIED. Editing company information returns it to PENDING.

## Recruiter endpoints

All recruiter endpoints require an authenticated user with role RECRUITER.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/v1/recruiters/company/ | Retrieve own company profile |
| POST | /api/v1/recruiters/company/ | Create company profile and recruiter association |
| PATCH | /api/v1/recruiters/company/ | Update own company profile; resets verification |
| GET | /api/v1/recruiters/opportunities/ | List own-company opportunities |
| POST | /api/v1/recruiters/opportunities/ | Create a DRAFT opportunity |
| GET | /api/v1/recruiters/opportunities/{id}/ | Retrieve own-company opportunity |
| PATCH | /api/v1/recruiters/opportunities/{id}/ | Edit DRAFT or REJECTED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/submit/ | Submit DRAFT/REJECTED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/close/ | Close a PUBLISHED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/archive/ | Archive DRAFT, REJECTED or CLOSED opportunity |

## IPC endpoints

All IPC endpoints require an authenticated user with role IPC_ADMIN.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/v1/ipc/companies/pending/ | List companies awaiting verification |
| POST | /api/v1/ipc/companies/{id}/verify/ | Verify company |
| POST | /api/v1/ipc/companies/{id}/reject/ | Reject company; reason required |
| GET | /api/v1/ipc/opportunities/pending/ | List opportunities awaiting approval |
| POST | /api/v1/ipc/opportunities/{id}/approve/ | Approve and publish opportunity |
| POST | /api/v1/ipc/opportunities/{id}/reject/ | Reject opportunity; reason required |

## Frontend dashboards

- /recruiter is restricted to RECRUITER users and supports company profile create/read/update, opportunity draft create/edit, submit, close and archive actions.
- /ipc is restricted to IPC_ADMIN users and supports pending company verification and opportunity approval queues.
- Frontend role gates are for navigation and usability; backend role permissions remain authoritative.

## Eligibility criteria payload

eligibility_criteria is a JSON object with supported keys: minimum_cgpa (0 to 10), graduation_years (positive integer years), degree_programmes, departments and required_skills (arrays of non-empty strings). Full comparison against student profiles is separate eligibility-engine work.

## Workflow and audit

Company records store verification status, reviewer, verification timestamp and rejection reason. Opportunity records store creator, approver, approval timestamp, publication timestamp and rejection reason. Workflow transitions create WorkflowAuditEvent records. Public discovery returns published, unexpired opportunities only.

## Not included

- Recruiter self-registration or invitation pending A-06.
- Automated identity checks or email OTP.
- Full eligibility evaluation against student profiles.
- Application submission/review workflow.
- Email notifications.
